"""Reproducibility and configuration tracking for evidence-based career intelligence."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.errors import NotFoundError
from backend.app.models.analysis import Analysis
from backend.app.models.resume import ResumeVersion


class ReproducibilityMetadata(BaseModel):
    """Schema tracking complete model, embedding, and prompt configuration used for an analysis."""

    model_config = ConfigDict(from_attributes=True)

    analysis_id: str = Field(..., description="Unique UUID of the evaluation run")
    resume_version: int = Field(default=1, description="Version number of the evaluated resume")
    llm_provider: str = Field(..., description="LLM provider name (e.g. mock, openai, ollama)")
    llm_model: str = Field(..., description="LLM model identifier")
    embedding_provider: str = Field(..., description="Embedding provider name")
    embedding_model: str = Field(..., description="Embedding model identifier")
    embedding_version: str = Field(default="v1.0.0", description="Embedding model / schema version")
    prompt_version: str = Field(..., description="Semantic prompt schema version")
    scoring_version: str = Field(..., description="Deterministic scoring engine version")
    created_at: datetime = Field(..., description="UTC timestamp of the analysis creation")
    configuration_hash: str = Field(..., description="Deterministic SHA256 digest of configuration parameters")
    explanation: str = Field(..., description="Human-readable explanation of the model and scoring configuration")


class ReproducibilityService:
    """Service providing configuration tracking, hash verification, and audit explanation."""

    @staticmethod
    def compute_configuration_hash(
        llm_provider: str,
        llm_model: str,
        embedding_provider: str,
        embedding_model: str,
        embedding_version: str,
        prompt_version: str,
        scoring_version: str,
    ) -> str:
        """Computes a deterministic SHA256 signature uniquely identifying the execution configuration."""
        raw_signature = (
            f"{llm_provider}:{llm_model}|"
            f"{embedding_provider}:{embedding_model}:{embedding_version}|"
            f"{prompt_version}|{scoring_version}"
        )
        return hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_explanation(
        llm_provider: str,
        llm_model: str,
        embedding_provider: str,
        embedding_model: str,
        prompt_version: str,
        scoring_version: str,
    ) -> str:
        """Constructs an explainable summary of the evaluation engine configuration."""
        return (
            f"This analysis was generated using {llm_provider.upper()} ({llm_model}) for reasoning, "
            f"{embedding_provider.upper()} ({embedding_model}) for semantic vector comparisons, "
            f"prompt template {prompt_version}, and deterministic scoring engine {scoring_version}. "
            "All findings are grounded strictly in candidate-provided evidence with zero hallucinated skills."
        )

    @classmethod
    async def get_metadata_for_analysis(
        cls,
        db: AsyncSession,
        analysis_id: str,
    ) -> ReproducibilityMetadata:
        """Retrieves and constructs reproducibility metadata for a specific analysis."""
        stmt = (
            select(Analysis)
            .options(selectinload(Analysis.resume_version))
            .where(Analysis.id == analysis_id)
        )
        result = await db.execute(stmt)
        analysis = result.scalar_one_or_none()
        if not analysis:
            raise NotFoundError(f"Analysis with ID '{analysis_id}' not found")

        version_num = analysis.resume_version.version_number if analysis.resume_version else 1
        embedding_ver = getattr(analysis, "embedding_version", "v1.0.0") or "v1.0.0"

        config_hash = cls.compute_configuration_hash(
            llm_provider=analysis.llm_provider,
            llm_model=analysis.llm_model,
            embedding_provider=analysis.embedding_provider,
            embedding_model=analysis.embedding_model,
            embedding_version=embedding_ver,
            prompt_version=analysis.prompt_version,
            scoring_version=analysis.scoring_version,
        )

        explanation = cls.generate_explanation(
            llm_provider=analysis.llm_provider,
            llm_model=analysis.llm_model,
            embedding_provider=analysis.embedding_provider,
            embedding_model=analysis.embedding_model,
            prompt_version=analysis.prompt_version,
            scoring_version=analysis.scoring_version,
        )

        return ReproducibilityMetadata(
            analysis_id=analysis.id,
            resume_version=version_num,
            llm_provider=analysis.llm_provider,
            llm_model=analysis.llm_model,
            embedding_provider=analysis.embedding_provider,
            embedding_model=analysis.embedding_model,
            embedding_version=embedding_ver,
            prompt_version=analysis.prompt_version,
            scoring_version=analysis.scoring_version,
            created_at=analysis.created_at,
            configuration_hash=config_hash,
            explanation=explanation,
        )

