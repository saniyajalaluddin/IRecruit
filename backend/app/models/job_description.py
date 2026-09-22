"""Job Description database entity."""

from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.analysis import Analysis


class JobDescription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Target job description pasted or provided by user."""

    __tablename__ = "job_descriptions"

    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_requirements: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="job_descriptions")
    analyses: Mapped[List["Analysis"]] = relationship(
        "Analysis", back_populates="job_description", cascade="all, delete-orphan"
    )
