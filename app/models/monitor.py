from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class AlertRule(Base, TimestampMixin):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(Enum("host", "service", "url"), default="host")
    target_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    condition: Mapped[str] = mapped_column(Enum("gt", "lt", "gte", "lte", "eq"), nullable=False)
    threshold: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    duration_sec: Mapped[int] = mapped_column(default=60)
    severity: Mapped[str] = mapped_column(Enum("info", "warning", "critical"), default="warning")
    notify_channels: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(Enum("firing", "resolved"), default="firing")
    metric_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    fired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notified: Mapped[bool] = mapped_column(default=False)
