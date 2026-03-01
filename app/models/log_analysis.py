from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Integer, JSON, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class LogWatcher(Base, TimestampMixin):
    """日志监控任务配置"""
    __tablename__ = "log_watchers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    log_path: Mapped[str] = mapped_column(String(512), nullable=False, comment="日志文件路径（支持 glob）")
    source_type: Mapped[str] = mapped_column(
        Enum("local", "remote"), default="local", comment="local=本地文件, remote=SSH远程"
    )
    server_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("servers.id", ondelete="SET NULL"), nullable=True, comment="远程服务器（仅 remote 模式）"
    )
    # drain3 参数
    drain_depth: Mapped[int] = mapped_column(SmallInteger, default=4, comment="drain3 树深度")
    drain_sim_th: Mapped[float] = mapped_column(Float, default=0.4, comment="drain3 相似度阈值")
    drain_max_children: Mapped[int] = mapped_column(SmallInteger, default=100)
    # 日志预处理
    log_format_regex: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="提取 message 字段的正则（含命名组 message）"
    )
    masking_patterns: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, comment="掩码规则列表 [{regex_pattern, mask_with}]"
    )
    # 运行状态
    status: Mapped[str] = mapped_column(
        Enum("active", "paused", "error"), default="paused", index=True
    )
    last_pos: Mapped[int] = mapped_column(BigInteger, default=0, comment="文件已读字节偏移")
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    templates: Mapped[list["LogTemplate"]] = relationship(back_populates="watcher", cascade="all, delete-orphan")


class LogTemplate(Base):
    """drain3 挖掘出的日志模板"""
    __tablename__ = "log_templates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    watcher_id: Mapped[int] = mapped_column(
        ForeignKey("log_watchers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="drain3 cluster_id")
    template_str: Mapped[str] = mapped_column(Text, nullable=False, comment="聚合后的模板字符串")
    hit_count: Mapped[int] = mapped_column(BigInteger, default=1, comment="匹配该模板的日志条数")
    sample_logs: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, comment="最近10条原始日志样本")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    watcher: Mapped[LogWatcher] = relationship(back_populates="templates")
