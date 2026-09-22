"""User database entity."""

from typing import List, TYPE_CHECKING
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.resume import Resume
    from backend.app.models.job_description import JobDescription
    from backend.app.models.analysis import Analysis
    from backend.app.models.audit import AuditEvent
    from backend.app.models.usage import UsageRecord
    from backend.app.models.entitlement import Entitlement


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account entity with strict resource ownership relations."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="candidate", nullable=False)

    # Relationships
    resumes: Mapped[List["Resume"]] = relationship(
        "Resume", back_populates="user", cascade="all, delete-orphan"
    )
    job_descriptions: Mapped[List["JobDescription"]] = relationship(
        "JobDescription", back_populates="user", cascade="all, delete-orphan"
    )
    analyses: Mapped[List["Analysis"]] = relationship(
        "Analysis", back_populates="user", cascade="all, delete-orphan"
    )
    audit_events: Mapped[List["AuditEvent"]] = relationship(
        "AuditEvent", back_populates="user", cascade="all, delete-orphan"
    )
    usage_records: Mapped[List["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="user", cascade="all, delete-orphan"
    )
    entitlements: Mapped[List["Entitlement"]] = relationship(
        "Entitlement", back_populates="user", cascade="all, delete-orphan"
    )
