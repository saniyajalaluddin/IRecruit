"""Recommendation database entity."""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.analysis import Analysis
    from backend.app.models.requirement import Requirement


class Recommendation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Evidence-grounded recommendation entity without fabrication."""

    __tablename__ = "recommendations"

    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=True, index=True
    )
    recommendation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    original_quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_revision: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_evidence_grounded: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="recommendations")
    requirement: Mapped[Optional["Requirement"]] = relationship("Requirement", back_populates="recommendations")
