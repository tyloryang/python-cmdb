from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, JSON, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class Pipeline(Base, TimestampMixin):
    __tablename__ = "pipelines"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repo_url: Mapped[str] = mapped_column(String(512), nullable=False)
    branch: Mapped[str] = mapped_column(String(128), default="main")
    trigger_type: Mapped[str] = mapped_column(
        Enum("manual", "webhook", "schedule"), default="manual"
    )
    cron_expr: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    config_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    engine: Mapped[str] = mapped_column(Enum("local", "jenkins"), default="local")
    jenkins_job: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    builds: Mapped[list["PipelineBuild"]] = relationship(back_populates="pipeline")


class PipelineBuild(Base):
    __tablename__ = "pipeline_builds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False
    )
    build_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "success", "failed", "cancelled"),
        default="pending", index=True
    )
    trigger_type: Mapped[str] = mapped_column(Enum("manual", "webhook", "schedule"), nullable=False)
    triggered_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    commit_sha: Mapped[str] = mapped_column(String(40), default="")
    commit_msg: Mapped[str] = mapped_column(String(256), default="")
    branch: Mapped[str] = mapped_column(String(128), default="")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    pipeline: Mapped[Pipeline] = relationship(back_populates="builds")
    stage_logs: Mapped[list["BuildStageLog"]] = relationship(back_populates="build")


class BuildStageLog(Base):
    __tablename__ = "build_stage_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    build_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_builds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_name: Mapped[str] = mapped_column(String(128), nullable=False)
    stage_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "success", "failed", "skipped"), default="pending"
    )
    log_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    build: Mapped[PipelineBuild] = relationship(back_populates="stage_logs")
