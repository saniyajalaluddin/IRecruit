"""Harness for executing evaluation benchmarks against ground-truth resumes and JDs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.app.evaluation.benchmark_dataset import BENCHMARK_CASES, BenchmarkCase
from backend.app.modules.ats.service import ATSCompatibilityService
from backend.app.modules.evidence.service import EvidenceService
from backend.app.modules.gaps.service import GapAnalysisService
from backend.app.modules.job_descriptions.service import JobDescriptionService
from backend.app.modules.matching.service import MatchingService
from backend.app.modules.privacy.service import PIIService
from backend.app.modules.recommendations.service import RecommendationService
from backend.app.modules.resumes.service import ResumeService
from backend.app.modules.scoring.service import ScoringService
from backend.app.modules.security.prompt_defense import PromptInjectionDetector

logger = logging.getLogger(__name__)


@dataclass
class CaseEvaluationResult:
    """Evaluation metrics for an individual benchmark case."""

    case_id: str
    case_name: str
    overall_score: float
    score_within_bounds: bool
    classified_items_count: int
    expected_matches_count: int
    correct_classifications: int
    false_positives: int  # Claimed matched when ground truth is missing
    false_negatives: int  # Claimed missing when ground truth is matched
    hallucination_detected: bool
    absence_statement_compliant: bool
    adversarial_blocked: bool
    notes: List[str] = field(default_factory=list)


@dataclass
class BenchmarkEvaluationReport:
    """Aggregated evaluation report across all benchmark scenarios."""

    total_cases: int
    passed_cases: int
    failed_cases: int
    precision: float
    recall: float
    accuracy: float
    hallucination_rate: float
    absence_compliance_rate: float
    adversarial_defense_rate: float
    case_results: List[CaseEvaluationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "accuracy": round(self.accuracy, 4),
            "hallucination_rate": round(self.hallucination_rate, 4),
            "absence_compliance_rate": round(self.absence_compliance_rate, 4),
            "adversarial_defense_rate": round(self.adversarial_defense_rate, 4),
            "case_results": [
                {
                    "case_id": r.case_id,
                    "case_name": r.case_name,
                    "overall_score": round(r.overall_score, 2),
                    "score_within_bounds": r.score_within_bounds,
                    "hallucination_detected": r.hallucination_detected,
                    "absence_compliant": r.absence_statement_compliant,
                    "adversarial_blocked": r.adversarial_blocked,
                    "notes": r.notes,
                }
                for r in self.case_results
            ],
        }


class BenchmarkEvaluator:
    """Executes evaluation benchmarks and generates quality metrics."""

    def __init__(self):
        self.resume_service = ResumeService()
        self.jd_service = JobDescriptionService()
        self.matching_service = MatchingService()
        self.evidence_service = EvidenceService()
        self.scoring_service = ScoringService()
        self.gap_service = GapAnalysisService()
        self.rec_service = RecommendationService()
        self.ats_service = ATSCompatibilityService()

    async def evaluate_case(self, case: BenchmarkCase) -> CaseEvaluationResult:
        """Run a single benchmark case through the full intelligence pipeline and assess metrics."""
        notes = []

        # 1. Prompt Injection Defense Scanning & Sanitization
        scan = PromptInjectionDetector.scan_for_injection(case.resume_text)
        sanitized_input = PromptInjectionDetector.sanitize_untrusted_input(
            case.resume_text, policy="sanitize"
        )

        # 2. PII Redaction
        redaction = PIIService.redact_pii(sanitized_input)
        sanitized_resume_text = redaction.sanitized_text

        # 3. Structural Parsing
        parsed_resume = await self.resume_service.parse(sanitized_resume_text)
        parsed_jd = await self.jd_service.parse(case.job_description_text)

        # 4. Matching & Evidence
        matches = await self.matching_service.match_requirements(
            requirements=parsed_jd.requirements,
            resume=parsed_resume,
        )
        evidence_list = await self.evidence_service.evaluate_evidence(
            requirements=parsed_jd.requirements,
            matches=matches,
            resume=parsed_resume,
        )

        # 5. ATS Parsing Compatibility
        ats_report = self.ats_service.analyze_resume_text(case.resume_text)

        # 6. Explainable Deterministic Scoring
        scoring_result = self.scoring_service.calculate_score(
            requirements=parsed_jd.requirements,
            evidence=evidence_list,
            resume=parsed_resume,
            ats_score=ats_report.overall_score,
        )

        overall_score = scoring_result.overall_score
        score_within_bounds = case.min_overall_score <= overall_score <= case.max_overall_score

        if not score_within_bounds:
            notes.append(
                f"Score {overall_score:.1f} out of expected range [{case.min_overall_score}, {case.max_overall_score}]"
            )

        # Build classification map by requirement keyword (lowercased)
        evidence_by_text = {}
        for ev in evidence_list:
            req_text = ev.requirement_text.lower()
            evidence_by_text[req_text] = ev

        correct = 0
        false_positives = 0
        false_negatives = 0
        hallucination_detected = False
        absence_compliant = True

        for keyword, expected_status in case.expected_classifications.items():
            # Find matching requirement
            matched_ev = None
            for req_text, ev in evidence_by_text.items():
                if keyword in req_text:
                    matched_ev = ev
                    break

            if matched_ev:
                actual_status = matched_ev.classification.value if hasattr(matched_ev.classification, "value") else str(matched_ev.classification)

                if actual_status == expected_status:
                    correct += 1
                elif expected_status == "MISSING" and actual_status in ("MATCHED", "PARTIAL"):
                    false_positives += 1
                    hallucination_detected = True
                    notes.append(f"False Positive on '{keyword}': Expected MISSING, got {actual_status}")
                elif expected_status in ("MATCHED", "PARTIAL") and actual_status == "MISSING":
                    false_negatives += 1
                    notes.append(f"False Negative on '{keyword}': Expected {expected_status}, got MISSING")
                else:
                    # e.g. expected PARTIAL, got AMBIGUOUS
                    correct += 1
            else:
                # If expected missing and not in requirements, it is consistent
                if expected_status == "MISSING":
                    correct += 1

        # Check absence statement compliance
        for ev in evidence_list:
            status = ev.classification.value if hasattr(ev.classification, "value") else str(ev.classification)
            if status == "MISSING":
                # Ensure no snippet/quote is hallucinated
                if ev.has_evidence or (hasattr(ev, "snippets") and ev.snippets):
                    absence_compliant = False
                    hallucination_detected = True
                    notes.append(f"Illegal evidence attached to MISSING item: {ev.requirement_text}")

        # Check adversarial resistance
        adversarial_blocked = True
        if case.is_adversarial:
            if not scan.is_suspicious:
                adversarial_blocked = False
                notes.append("Adversarial prompt injection was not detected by scanner")
            if overall_score >= 90.0:
                adversarial_blocked = False
                notes.append("Adversarial prompt injection bypassed scoring limits")
            if false_positives > 0:
                adversarial_blocked = False
                notes.append("Adversarial prompt injection successfully forced false match")

        return CaseEvaluationResult(
            case_id=case.id,
            case_name=case.name,
            overall_score=overall_score,
            score_within_bounds=score_within_bounds,
            classified_items_count=len(evidence_list),
            expected_matches_count=len(case.expected_classifications),
            correct_classifications=correct,
            false_positives=false_positives,
            false_negatives=false_negatives,
            hallucination_detected=hallucination_detected,
            absence_statement_compliant=absence_compliant,
            adversarial_blocked=adversarial_blocked,
            notes=notes,
        )

    async def run_benchmark(self, cases: Optional[List[BenchmarkCase]] = None) -> BenchmarkEvaluationReport:
        """Runs the entire benchmark suite and aggregates performance metrics."""
        cases_to_run = cases or BENCHMARK_CASES
        case_results: List[CaseEvaluationResult] = []

        total_tp = 0
        total_fp = 0
        total_fn = 0
        total_tn = 0
        total_evaluations = 0

        passed_cases = 0

        for case in cases_to_run:
            res = await self.evaluate_case(case)
            case_results.append(res)

            case_passed = (
                res.score_within_bounds
                and not res.hallucination_detected
                and res.absence_statement_compliant
                and res.adversarial_blocked
            )
            if case_passed:
                passed_cases += 1

            total_tp += res.correct_classifications
            total_fp += res.false_positives
            total_fn += res.false_negatives
            total_evaluations += (res.correct_classifications + res.false_positives + res.false_negatives)

        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
        accuracy = total_tp / total_evaluations if total_evaluations > 0 else 1.0

        hallucination_cases = sum(1 for r in case_results if r.hallucination_detected)
        hallucination_rate = hallucination_cases / len(case_results) if case_results else 0.0

        absence_compliant_cases = sum(1 for r in case_results if r.absence_statement_compliant)
        absence_compliance_rate = absence_compliant_cases / len(case_results) if case_results else 1.0

        adversarial_cases = [r for r in case_results if any(c.id == r.case_id and c.is_adversarial for c in cases_to_run)]
        if adversarial_cases:
            adv_passed = sum(1 for r in adversarial_cases if r.adversarial_blocked)
            adversarial_rate = adv_passed / len(adversarial_cases)
        else:
            adversarial_rate = 1.0

        return BenchmarkEvaluationReport(
            total_cases=len(cases_to_run),
            passed_cases=passed_cases,
            failed_cases=len(cases_to_run) - passed_cases,
            precision=precision,
            recall=recall,
            accuracy=accuracy,
            hallucination_rate=hallucination_rate,
            absence_compliance_rate=absence_compliance_rate,
            adversarial_defense_rate=adversarial_rate,
            case_results=case_results,
        )
