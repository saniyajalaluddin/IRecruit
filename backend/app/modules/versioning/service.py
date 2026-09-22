"""Resume versioning, iteration tracking, and comparative diff service."""

from __future__ import annotations

import difflib
from typing import List, Optional, Set

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.errors import NotFoundError, ValidationError
from backend.app.models.analysis import Analysis
from backend.app.models.audit import AuditEvent
from backend.app.models.resume import Resume, ResumeVersion
from backend.app.models.user import User
from backend.app.modules.privacy.service import PIIService
from backend.app.modules.resumes.service import ResumeService
from backend.app.modules.security.authorization import verify_resume_ownership
from backend.app.modules.versioning.schemas import (
    ResumeVersionItem,
    ResumeVersionListResponse,
    ScoreProgression,
    VersionComparisonResponse,
    VersionDiffItem,
)


class ResumeVersioningService:
    """Manages sequential resume revisions, diffs, and score progression."""

    def __init__(self, resume_service: Optional[ResumeService] = None):
        self._resume_service = resume_service or ResumeService()

    async def create_version(
        self,
        db: AsyncSession,
        resume_id: str,
        user: User,
        raw_text: str,
        notes: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> ResumeVersionItem:
        """Appends a new sequential version to an existing candidate resume."""
        resume = await verify_resume_ownership(resume_id, user, db)

        # Get latest version number
        stmt = select(func.max(ResumeVersion.version_number)).where(
            ResumeVersion.resume_id == resume_id
        )
        res = await db.execute(stmt)
        max_ver = res.scalar_one_or_none() or 0
        new_ver_num = max_ver + 1

        # PII Minimization and Parsing
        redaction = PIIService.redact_pii(raw_text)
        structured_resume = await self._resume_service.parse(raw_text)

        new_version = ResumeVersion(
            resume_id=resume.id,
            version_number=new_ver_num,
            raw_text=raw_text,
            pii_masked_text=redaction.sanitized_text,
            structured_data=structured_resume.model_dump(),
        )
        db.add(new_version)
        await db.flush()

        audit = AuditEvent(
            user_id=user.id,
            event_type="resume_version_created",
            resource_type="resume_version",
            resource_id=new_version.id,
            details={"version_number": str(new_ver_num), "notes": notes or ""},
            ip_address=client_ip,
        )
        db.add(audit)
        await db.commit()

        words = len(raw_text.split())
        return ResumeVersionItem(
            id=new_version.id,
            version_number=new_ver_num,
            character_count=len(raw_text),
            word_count=words,
            created_at=new_version.created_at,
        )

    async def list_versions(
        self,
        db: AsyncSession,
        resume_id: str,
        user: User,
    ) -> ResumeVersionListResponse:
        """Lists all sequential revisions for a candidate resume."""
        await verify_resume_ownership(resume_id, user, db)

        stmt = (
            select(ResumeVersion)
            .where(ResumeVersion.resume_id == resume_id)
            .order_by(ResumeVersion.version_number.asc())
        )
        res = await db.execute(stmt)
        versions = res.scalars().all()

        items: List[ResumeVersionItem] = []
        for v in versions:
            words = len(v.raw_text.split())
            items.append(
                ResumeVersionItem(
                    id=v.id,
                    version_number=v.version_number,
                    character_count=len(v.raw_text),
                    word_count=words,
                    created_at=v.created_at,
                )
            )

        return ResumeVersionListResponse(
            resume_id=resume_id,
            total_versions=len(items),
            versions=items,
        )

    async def compare_versions(
        self,
        db: AsyncSession,
        resume_id: str,
        user: User,
        base_version_number: int,
        target_version_number: int,
    ) -> VersionComparisonResponse:
        """Computes structural text diffs, skill changes, and alignment score progression."""
        await verify_resume_ownership(resume_id, user, db)

        if base_version_number == target_version_number:
            raise ValidationError("Base and target version numbers must be distinct.")

        # Query both versions
        stmt = select(ResumeVersion).where(
            ResumeVersion.resume_id == resume_id,
            ResumeVersion.version_number.in_([base_version_number, target_version_number]),
        )
        res = await db.execute(stmt)
        found = {v.version_number: v for v in res.scalars().all()}

        base_ver = found.get(base_version_number)
        target_ver = found.get(target_version_number)

        if not base_ver:
            raise NotFoundError(f"Base resume version {base_version_number} does not exist.")
        if not target_ver:
            raise NotFoundError(f"Target resume version {target_version_number} does not exist.")

        # 1. Compute Text Diffs
        base_lines = base_ver.raw_text.splitlines()
        target_lines = target_ver.raw_text.splitlines()

        diffs: List[VersionDiffItem] = []
        matcher = difflib.unified_diff(base_lines, target_lines, lineterm="")
        for line in matcher:
            if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
                continue
            if line.startswith("+"):
                diffs.append(VersionDiffItem(change_type="added", text=line[1:].strip()))
            elif line.startswith("-"):
                diffs.append(VersionDiffItem(change_type="removed", text=line[1:].strip()))

        # 2. Compute Skill Delta
        base_skills: Set[str] = set(
            s.lower() for s in (base_ver.structured_data.get("skills") or [])
        )
        target_skills: Set[str] = set(
            s.lower() for s in (target_ver.structured_data.get("skills") or [])
        )

        skills_added = sorted(list(target_skills - base_skills))
        skills_removed = sorted(list(base_skills - target_skills))

        # 3. Check for Comparative Score Progression
        # Find latest analyses for both versions
        base_analysis_stmt = (
            select(Analysis)
            .where(Analysis.resume_version_id == base_ver.id)
            .order_by(Analysis.created_at.desc())
            .limit(1)
        )
        target_analysis_stmt = (
            select(Analysis)
            .where(Analysis.resume_version_id == target_ver.id)
            .order_by(Analysis.created_at.desc())
            .limit(1)
        )

        base_a_res = await db.execute(base_analysis_stmt)
        target_a_res = await db.execute(target_analysis_stmt)
        base_a = base_a_res.scalar_one_or_none()
        target_a = target_a_res.scalar_one_or_none()

        score_prog: Optional[ScoreProgression] = None
        if base_a and target_a:
            delta = round(target_a.overall_score - base_a.overall_score, 1)
            b_score = base_a.overall_score
            t_score = target_a.overall_score
            b_grade = "A" if b_score >= 90 else ("B" if b_score >= 80 else ("C" if b_score >= 70 else ("D" if b_score >= 60 else "F")))
            t_grade = "A" if t_score >= 90 else ("B" if t_score >= 80 else ("C" if t_score >= 70 else ("D" if t_score >= 60 else "F")))

            score_prog = ScoreProgression(
                base_score=b_score,
                target_score=t_score,
                delta=delta,
                base_grade=b_grade,
                target_grade=t_grade,
            )

        return VersionComparisonResponse(
            resume_id=resume_id,
            base_version_number=base_version_number,
            target_version_number=target_version_number,
            text_diffs=diffs,
            skills_added=skills_added,
            skills_removed=skills_removed,
            score_progression=score_prog,
        )


# Global singleton instance
resume_versioning_service = ResumeVersioningService()

