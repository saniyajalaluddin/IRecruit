"""Requirement database entity."""

from typing import List, TYPE_CHECKING
from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.analysis import Analysis
    from backend.app.models.evidence import Evidence
    from backend.app.models.recommendation import Recommendation


class Requirement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Extracted JD requirement mapped to an analysis."""

    __tablename__ = "requirements"

    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="technical_skill", nullable=False)
    priority: Mapped[str] = mapped_column(String(50), default="required", nullable=False)
    normalized_terms: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="requirements")
    evidence: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="requirement", cascade="all, delete-orphan"
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation", back_populates="requirement", cascade="all, delete-orphan"
    )
