"""Dashboard service for analysis history, entitlements enforcement, and candidate metrics."""

from __future__ import annotations

from collections import Counter
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.analysis import Analysis
from backend.app.models.entitlement import Entitlement
from backend.app.models.evidence import Evidence
from backend.app.models.requirement import Requirement
from backend.app.modules.dashboard.schemas import (
    AnalysisHistoryItem,
    AnalysisHistoryResponse,
    DashboardMetrics,
)


class DashboardService:
    """Manages candidate dashboard analytics, analysis history, and free tier limits."""

    async def get_user_entitlement(
        self, db: AsyncSession, user_id: str
    ) -> Entitlement:
        """Retrieves or provisions the default entitlement tier for a user."""
        stmt = select(Entitlement).where(
            Entitlement.user_id == user_id,
            Entitlement.is_active == True,
        )
        res = await db.execute(stmt)
        entitlement = res.scalar_one_or_none()

        if not entitlement:
            entitlement = Entitlement(
                user_id=user_id,
                tier="free",
                max_saved_analyses=5,
                analyses_count=0,
                is_active=True,
            )
            db.add(entitlement)
            await db.commit()
            await db.refresh(entitlement)

        return entitlement

    async def get_analysis_history(
        self, db: AsyncSession, user_id: str
    ) -> AnalysisHistoryResponse:
        """Fetches up to the latest 5 saved analyses for a free user."""
        entitlement = await self.get_user_entitlement(db, user_id)
        limit = entitlement.max_saved_analyses

        # Count total stored analyses
        count_stmt = select(func.count(Analysis.id)).where(
            Analysis.user_id == user_id,
            Analysis.is_anonymous == False,
        )
        total_count_res = await db.execute(count_stmt)
        total_saved = total_count_res.scalar_one() or 0

        # Fetch capped latest analyses
        stmt = (
            select(Analysis)
            .where(
                Analysis.user_id == user_id,
                Analysis.is_anonymous == False,
            )
            .options(selectinload(Analysis.job_description))
            .order_by(Analysis.created_at.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        analyses = res.scalars().all()

        items: List[AnalysisHistoryItem] = []
        for a in analyses:
            score = a.overall_score
            grade = "A" if score >= 90 else ("B" if score >= 80 else ("C" if score >= 70 else ("D" if score >= 60 else "F")))
            items.append(
                AnalysisHistoryItem(
                    id=a.id,
                    job_title=a.job_description.title if a.job_description else "Target Role",
                    company_name=a.job_description.company_name if a.job_description else None,
                    overall_score=a.overall_score,
                    grade=grade,
                    component_scores=a.component_scores or {},
                    scoring_version=a.scoring_version,
                    created_at=a.created_at,
                )
            )

        return AnalysisHistoryResponse(
            items=items,
            total_saved=total_saved,
            max_allowed=limit,
            tier=entitlement.tier,
        )

    async def get_dashboard_metrics(
        self, db: AsyncSession, user_id: str
    ) -> DashboardMetrics:
        """Computes summary statistics and recurring skill gaps across candidate analyses."""
        entitlement = await self.get_user_entitlement(db, user_id)

        stmt = (
            select(Analysis)
            .where(
                Analysis.user_id == user_id,
                Analysis.is_anonymous == False,
            )
            .options(
                selectinload(Analysis.job_description),
                selectinload(Analysis.evidence),
                selectinload(Analysis.requirements),
            )
            .order_by(Analysis.created_at.desc())
        )
        res = await db.execute(stmt)
        analyses = res.scalars().all()

        if not analyses:
            return DashboardMetrics(
                total_analyses_run=0,
                average_score=0.0,
                top_missing_skills=[],
                tier=entitlement.tier,
                saved_analyses_count=0,
                max_saved_analyses=entitlement.max_saved_analyses,
                latest_analysis=None,
            )

        total_runs = len(analyses)
        avg_score = round(sum(a.overall_score for a in analyses) / total_runs, 1)

        # Extract missing skills from requirements
        missing_skill_counter: Counter = Counter()
        for a in analyses:
            req_by_id = {r.id: r for r in a.requirements}
            for ev in a.evidence:
                if ev.classification == "MISSING":
                    req = req_by_id.get(ev.requirement_id)
                    if req and req.normalized_terms:
                        for term in req.normalized_terms:
                            missing_skill_counter[term] += 1
                    elif req:
                        # Fallback to snippet of text
                        missing_skill_counter[req.requirement_text[:30]] += 1

        top_missing = [term for term, _ in missing_skill_counter.most_common(5)]

        latest = analyses[0]
        l_score = latest.overall_score
        l_grade = "A" if l_score >= 90 else ("B" if l_score >= 80 else ("C" if l_score >= 70 else ("D" if l_score >= 60 else "F")))
        latest_item = AnalysisHistoryItem(
            id=latest.id,
            job_title=latest.job_description.title if latest.job_description else "Target Role",
            company_name=latest.job_description.company_name if latest.job_description else None,
            overall_score=latest.overall_score,
            grade=l_grade,
            component_scores=latest.component_scores or {},
            scoring_version=latest.scoring_version,
            created_at=latest.created_at,
        )

        return DashboardMetrics(
            total_analyses_run=total_runs,
            average_score=avg_score,
            top_missing_skills=top_missing,
            tier=entitlement.tier,
            saved_analyses_count=min(total_runs, entitlement.max_saved_analyses),
            max_saved_analyses=entitlement.max_saved_analyses,
            latest_analysis=latest_item,
        )


# Global singleton instance
dashboard_service = DashboardService()
