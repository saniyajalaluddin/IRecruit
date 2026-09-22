"""AI Usage and resource consumption database entity."""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.user import User


class UsageRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks token consumption, model utilization, and latency per user or anonymous session."""

    __tablename__ = "usage_records"

    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    analysis_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="usage_records")
