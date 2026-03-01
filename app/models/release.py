from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, JSON, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pipeline_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pipelines.id", ondelete="SET NULL"), nullable=True
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    releases: Mapped[list["Release"]] = relationship(back_populates="application")


class Release(Base, TimestampMixin):
    __tablename__ = "releases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    app_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    build_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pipeline_builds.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        Enum("draft", "pending", "deploying", "success", "failed", "rolled_back"),
        default="draft", index=True
    )
    deploy_type: Mapped[str] = mapped_column(
        Enum("full", "blue_green", "canary"), default="full"
    )
    canary_weight: Mapped[int] = mapped_column(default=0)
    target_servers: Mapped[list] = mapped_column(JSON, nullable=False)
    deploy_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    deployed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    application: Mapped[Application] = relationship(back_populates="releases")
    rollbacks: Mapped[list["RollbackRecord"]] = relationship(back_populates="release")


class RollbackRecord(Base):
    __tablename__ = "rollback_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("releases.id"), nullable=False)
    from_version: Mapped[str] = mapped_column(String(64), nullable=False)
    to_version: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    operated_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    operated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    release: Mapped[Release] = relationship(back_populates="rollbacks")
