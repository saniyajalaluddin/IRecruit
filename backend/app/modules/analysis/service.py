"""Service orchestrating anonymous quick analyses, conversion/claiming, and retention lifecycle."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import get_settings
from backend.app.core.errors import ForbiddenError, NotFoundError
from backend.app.models.analysis import Analysis
from backend.app.models.audit import AuditEvent
from backend.app.models.evidence import Evidence
from backend.app.models.job_description import JobDescription
from backend.app.models.recommendation import Recommendation
from backend.app.models.requirement import Requirement
from backend.app.models.resume import Resume, ResumeVersion
from backend.app.models.user import User
from backend.app.modules.analysis.schemas import (
    AnonymousAnalysisRequest,
    AnonymousAnalysisResponse,
    ClaimAnalysisResponse,
)
from backend.app.modules.ats.service import ATSCompatibilityService
from backend.app.modules.evidence.service import EvidenceService
from backend.app.modules.gaps.service import GapAnalysisService
from backend.app.modules.job_descriptions.service import JobDescriptionService
from backend.app.modules.matching.service import MatchingService
from backend.app.modules.privacy.service import PIIService
from backend.app.modules.recommendations.service import RecommendationService
from backend.app.modules.resumes.service import ResumeService
from backend.app.modules.scoring.service import ScoringService


class AnonymousAnalysisService:
    """Manages anonymous resume analyses and conversion pathways."""

    def __init__(
        self,
        resume_service: Optional[ResumeService] = None,
        jd_service: Optional[JobDescriptionService] = None,
        matching_service: Optional[MatchingService] = None,
        evidence_service: Optional[EvidenceService] = None,
        scoring_service: Optional[ScoringService] = None,
        gap_service: Optional[GapAnalysisService] = None,
        rec_service: Optional[RecommendationService] = None,
        ats_service: Optional[ATSCompatibilityService] = None,
    ):
        self.resume_service = resume_service or ResumeService()
        self.jd_service = jd_service or JobDescriptionService()
        self.matching_service = matching_service or MatchingService()
        self.evidence_service = evidence_service or EvidenceService()
        self.scoring_service = scoring_service or ScoringService()
        self.gap_service = gap_service or GapAnalysisService()
        self.rec_service = rec_service or RecommendationService()
        self.ats_service = ats_service or ATSCompatibilityService()

    async def run_anonymous_analysis(
        self,
        db: AsyncSession,
        request: AnonymousAnalysisRequest,
        client_ip: Optional[str] = None,
    ) -> AnonymousAnalysisResponse:
        """Executes full deterministic and explainable pipeline without requiring prior authentication."""
        start_time = time.perf_counter()
        settings = get_settings()

        session_id = request.session_id or f"anon_{uuid.uuid4().hex}"

        # 1. PII Redaction / Minimization
        redaction = PIIService.redact_pii(request.resume_text)
        sanitized_resume_text = redaction.sanitized_text

        # 2. Structural Parsing
        parsed_resume = await self.resume_service.parse(sanitized_resume_text)
        parsed_jd = await self.jd_service.parse(request.job_description_text)

        # 3. Matching & Evidence
        matches = await self.matching_service.match_requirements(
            requirements=parsed_jd.requirements,
            resume=parsed_resume,
        )
        evidence_list = await self.evidence_service.evaluate_evidence(
            requirements=parsed_jd.requirements,
            matches=matches,
            resume=parsed_resume,
        )

        # 4. ATS Parsing Compatibility
        ats_report = self.ats_service.analyze_resume_text(request.resume_text)

        # 5. Explainable Deterministic Scoring
        scoring_result = self.scoring_service.calculate_score(
            requirements=parsed_jd.requirements,
            evidence=evidence_list,
            resume=parsed_resume,
            ats_score=ats_report.overall_score,
        )

        # 6. Gap Analysis & Evidence-grounded Recommendations
        gap_result = self.gap_service.analyze_gaps(
            requirements=parsed_jd.requirements,
            evidence_list=evidence_list,
        )
        recs = await self.rec_service.generate_recommendations(
            requirements=parsed_jd.requirements,
            evidence=evidence_list,
            resume=parsed_resume,
        )

        execution_duration = (time.perf_counter() - start_time) * 1000

        # 7. Persistence: Create Entities
        resume = Resume(
            user_id=None,
            title="Anonymous Uploaded Resume",
            original_filename="anonymous_resume.txt",
            file_path="memory://anonymous",
            file_size_bytes=len(request.resume_text.encode("utf-8")),
            content_type="text/plain",
            is_anonymous=True,
        )
        db.add(resume)
        await db.flush()

        resume_version = ResumeVersion(
            resume_id=resume.id,
            version_number=1,
            raw_text=request.resume_text,
            pii_masked_text=sanitized_resume_text,
            structured_data=parsed_resume.model_dump(),
        )
        db.add(resume_version)
        await db.flush()

        job_desc = JobDescription(
            user_id=None,
            title=request.job_title,
            company_name=request.company_name,
            raw_text=request.job_description_text,
            structured_requirements=[r.model_dump() for r in parsed_jd.requirements],
        )
        db.add(job_desc)
        await db.flush()

        components_dict = scoring_result.components.model_dump()

        analysis = Analysis(
            user_id=None,
            resume_id=resume.id,
            resume_version_id=resume_version.id,
            job_description_id=job_desc.id,
            overall_score=scoring_result.overall_score,
            component_scores=components_dict,
            weights=scoring_result.weights,
            scoring_version=self.scoring_service.version,
            prompt_version="v1.0.0",
            llm_provider="mock",
            llm_model="mock-llm",
            embedding_provider=self.matching_service.metadata.get("provider", "tfidf"),
            embedding_model=self.matching_service.metadata.get("model", "tfidf-v1"),
            embedding_version=self.matching_service.metadata.get("matching_version", "v1.0.0"),
            execution_duration_ms=execution_duration,
            is_anonymous=True,
            session_id=session_id,
        )
        db.add(analysis)
        await db.flush()

        # Insert Requirements and maintain ID map
        req_id_map = {}
        for req in parsed_jd.requirements:
            db_req = Requirement(
                analysis_id=analysis.id,
                requirement_text=req.text,
                category=req.category.value,
                priority=req.priority.value,
                normalized_terms=req.normalized_terms,
            )
            db.add(db_req)
            await db.flush()
            req_id_map[req.id] = db_req.id

        # Insert Evidence Items
        for ev in evidence_list:
            mapped_req_id = req_id_map.get(ev.requirement_id)
            if not mapped_req_id and req_id_map:
                mapped_req_id = next(iter(req_id_map.values()))

            db_ev = Evidence(
                analysis_id=analysis.id,
                requirement_id=mapped_req_id,
                classification=ev.classification.value,
                snippets=[s.model_dump() for s in ev.snippets],
                explanation=ev.explanation or "No supporting evidence was found in the submitted resume.",
                has_evidence=ev.has_evidence,
            )
            db.add(db_ev)

        # Insert Recommendations
        for r in recs:
            db_rec = Recommendation(
                analysis_id=analysis.id,
                requirement_id=req_id_map.get(r.requirement_id),
                recommendation_type=r.type.value,
                title=r.title,
                rationale=r.rationale,
                original_quote=r.current_evidence_quote,
                suggested_revision=r.suggested_revision,
                is_evidence_grounded=r.is_evidence_grounded,
            )
            db.add(db_rec)

        # Audit Event
        audit = AuditEvent(
            user_id=None,
            event_type="anonymous_analysis_created",
            resource_type="analysis",
            resource_id=analysis.id,
            details={"session_id": session_id, "score": str(scoring_result.overall_score)},
            ip_address=client_ip,
        )
        db.add(audit)
        await db.commit()

        # Build Response
        created_at = analysis.created_at or datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=settings.ANONYMOUS_DATA_RETENTION_HOURS)

        matched_count = sum(1 for e in evidence_list if e.classification.value == "MATCHED")
        partial_count = sum(1 for e in evidence_list if e.classification.value == "PARTIAL")
        missing_count = sum(1 for e in evidence_list if e.classification.value == "MISSING")

        top_gaps = [
            {
                "requirement": g.requirement_text,
                "category": g.category.value,
                "priority": g.priority.value,
                "severity": g.severity.value,
            }
            for g in (gap_result.missing + gap_result.partial)[:5]
        ]
        recs_data = [
            {
                "title": r.title,
                "type": r.type.value,
                "rationale": r.rationale,
                "suggested_revision": r.suggested_revision,
            }
            for r in recs[:5]
        ]

        # Calculate Grade
        score_val = scoring_result.overall_score
        grade = "A" if score_val >= 90 else ("B" if score_val >= 80 else ("C" if score_val >= 70 else ("D" if score_val >= 60 else "F")))

        evidence_data = [
            {
                "requirement_text": ev.requirement_text,
                "classification": ev.classification.value,
                "confidence": 1.0 if ev.classification.value == "MATCHED" else (0.5 if ev.classification.value == "PARTIAL" else 0.0),
                "has_evidence": ev.has_evidence,
                "quote": ev.snippets[0].quote if ev.snippets else (ev.explanation if ev.has_evidence else None),
                "match_type": "Direct Semantic Match" if ev.has_evidence else "Absence",
            }
            for ev in evidence_list
        ]

        return AnonymousAnalysisResponse(
            analysis_id=analysis.id,
            session_id=session_id,
            overall_score=scoring_result.overall_score,
            grade=grade,
            component_scores=components_dict,
            requirements_matched=matched_count,
            requirements_partial=partial_count,
            requirements_missing=missing_count,
            top_gaps=top_gaps,
            recommendations=recs_data,
            ats_compatibility={
                "overall_score": ats_report.overall_score,
                "grade": ats_report.grade,
                "issues_count": len(ats_report.critical_issues) + len(ats_report.warnings),
                "summary": ats_report.summary,
            },
            scoring_version=analysis.scoring_version,
            created_at=created_at,
            expires_at=expires_at,
            is_claimed=False,
            evidence=evidence_data,
        )

    async def claim_analysis(
        self,
        db: AsyncSession,
        analysis_id: str,
        session_id: str,
        user: User,
        client_ip: Optional[str] = None,
    ) -> ClaimAnalysisResponse:
        """Transfers ownership of an anonymous analysis to an authenticated candidate."""
        stmt = (
            select(Analysis)
            .where(Analysis.id == analysis_id)
            .options(
                selectinload(Analysis.resume),
                selectinload(Analysis.job_description),
            )
        )
        result = await db.execute(stmt)
        analysis = result.scalar_one_or_none()

        if not analysis:
            raise NotFoundError(f"Analysis with ID '{analysis_id}' was not found.")

        if not analysis.is_anonymous:
            if analysis.user_id == user.id:
                # Already claimed by this user
                return ClaimAnalysisResponse(
                    analysis_id=analysis.id,
                    claimed=True,
                    user_id=user.id,
                    claimed_at=datetime.now(timezone.utc),
                )
            raise ForbiddenError("This analysis has already been claimed by another user.")

        if analysis.session_id != session_id:
            raise ForbiddenError("Session identifier does not match this anonymous analysis.")

        # Update Ownership
        analysis.user_id = user.id
        analysis.is_anonymous = False

        if analysis.resume:
            analysis.resume.user_id = user.id
            analysis.resume.is_anonymous = False

        if analysis.job_description:
            analysis.job_description.user_id = user.id

        audit = AuditEvent(
            user_id=user.id,
            event_type="analysis_claimed",
            resource_type="analysis",
            resource_id=analysis.id,
            details={"session_id": session_id},
            ip_address=client_ip,
        )
        db.add(audit)
        await db.commit()

        return ClaimAnalysisResponse(
            analysis_id=analysis.id,
            claimed=True,
            user_id=user.id,
            claimed_at=datetime.now(timezone.utc),
        )

    async def purge_expired_anonymous_analyses(
        self,
        db: AsyncSession,
        retention_hours: int = 24,
    ) -> int:
        """Purges anonymous analyses older than the retention limit."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)

        stmt = select(Analysis).where(
            Analysis.is_anonymous == True,
            Analysis.created_at < cutoff,
        )
        result = await db.execute(stmt)
        expired = result.scalars().all()

        purged_count = 0
        for analysis in expired:
            await db.delete(analysis)
            audit = AuditEvent(
                user_id=None,
                event_type="retention_purged",
                resource_type="analysis",
                resource_id=analysis.id,
                details={"retention_hours": str(retention_hours)},
            )
            db.add(audit)
            purged_count += 1

        if purged_count > 0:
            await db.commit()

        return purged_count


# Global singleton instance
anonymous_analysis_service = AnonymousAnalysisService()
