"""Resume and ResumeVersion database entities."""

from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.analysis import Analysis


class Resume(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Candidate resume entity holding file references and versions."""

    __tablename__ = "resumes"

    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="Resume", nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="resumes")
    versions: Mapped[List["ResumeVersion"]] = relationship(
        "ResumeVersion", back_populates="resume", cascade="all, delete-orphan", order_by="ResumeVersion.version_number"
    )
    analyses: Mapped[List["Analysis"]] = relationship(
        "Analysis", back_populates="resume", cascade="all, delete-orphan"
    )


class ResumeVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Implements version tracking for resume iterations and text revisions."""

    __tablename__ = "resume_versions"

    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    pii_masked_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    resume: Mapped["Resume"] = relationship("Resume", back_populates="versions")
    analyses: Mapped[List["Analysis"]] = relationship(
        "Analysis", back_populates="resume_version", cascade="all, delete-orphan"
    )
