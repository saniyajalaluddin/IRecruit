"""Analysis database entity representing an evaluation run."""

from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.resume import Resume, ResumeVersion
    from backend.app.models.job_description import JobDescription
    from backend.app.models.requirement import Requirement
    from backend.app.models.evidence import Evidence
    from backend.app.models.recommendation import Recommendation


class Analysis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Core analysis report entity linking candidate resume, JD, scores, and evidence."""

    __tablename__ = "analyses"

    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_description_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Deterministic Scoring & Breakdown
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    component_scores: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    weights: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Reproducibility Metadata
    scoring_version: Mapped[str] = mapped_column(String(50), default="v1.0.0", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), default="v1.0.0", nullable=False)
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    execution_duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="analyses")
    resume: Mapped["Resume"] = relationship("Resume", back_populates="analyses")
    resume_version: Mapped["ResumeVersion"] = relationship("ResumeVersion", back_populates="analyses")
    job_description: Mapped["JobDescription"] = relationship("JobDescription", back_populates="analyses")

    requirements: Mapped[List["Requirement"]] = relationship(
        "Requirement", back_populates="analysis", cascade="all, delete-orphan"
    )
    evidence: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="analysis", cascade="all, delete-orphan"
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation", back_populates="analysis", cascade="all, delete-orphan"
    )
