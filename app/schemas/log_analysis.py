from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MaskingPattern(BaseModel):
    regex_pattern: str
    mask_with: str = "<*>"


class LogWatcherCreate(BaseModel):
    name: str
    log_path: str = Field(..., description="日志文件绝对路径，支持 glob（如 /var/log/app/*.log）")
    source_type: str = Field("local", description="local | remote")
    server_id: Optional[int] = None
    drain_depth: int = Field(4, ge=2, le=10)
    drain_sim_th: float = Field(0.4, ge=0.1, le=1.0)
    drain_max_children: int = Field(100, ge=10, le=1000)
    log_format_regex: Optional[str] = Field(
        None, description="提取日志正文的正则，须含命名组 (?P<message>...)"
    )
    masking_patterns: Optional[List[MaskingPattern]] = None


class LogWatcherUpdate(BaseModel):
    name: Optional[str] = None
    log_path: Optional[str] = None
    drain_depth: Optional[int] = Field(None, ge=2, le=10)
    drain_sim_th: Optional[float] = Field(None, ge=0.1, le=1.0)
    log_format_regex: Optional[str] = None
    masking_patterns: Optional[List[MaskingPattern]] = None


class LogWatcherOut(BaseModel):
    id: int
    name: str
    log_path: str
    source_type: str
    server_id: Optional[int]
    drain_depth: int
    drain_sim_th: float
    drain_max_children: int
    log_format_regex: Optional[str]
    masking_patterns: Optional[list]
    status: str
    last_pos: int
    last_run_at: Optional[datetime]
    last_error: Optional[str]
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class LogTemplateOut(BaseModel):
    id: int
    watcher_id: int
    cluster_id: int
    template_str: str
    hit_count: int
    sample_logs: Optional[list]
    first_seen_at: datetime
    last_seen_at: datetime

    model_config = {"from_attributes": True}


class LogAskInput(BaseModel):
    question: str = Field(..., description="用户的自然语言问题")
    hours: int = Field(24, description="查询过去几小时内的日志")


class LogAskOutput(BaseModel):
    answer: str
