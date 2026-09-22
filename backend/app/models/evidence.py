"""Evidence database entity."""

from typing import TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.analysis import Analysis
    from backend.app.models.requirement import Requirement


class Evidence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Grounded candidate evidence supporting or missing for a requirement."""

    __tablename__ = "evidence"

    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    classification: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # MATCHED, PARTIAL, MISSING, AMBIGUOUS
    snippets: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    has_evidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="evidence")
    requirement: Mapped["Requirement"] = relationship("Requirement", back_populates="evidence")
