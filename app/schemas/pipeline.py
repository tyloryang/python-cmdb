from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel


class PipelineCreate(BaseModel):
    name: str
    description: Optional[str] = None
    repo_url: str
    branch: str = "main"
    trigger_type: str = "manual"
    cron_expr: Optional[str] = None
    config_yaml: str
    engine: str = "local"
    jenkins_job: Optional[str] = None


class PipelineOut(BaseModel):
    id: int
    name: str
    repo_url: str
    branch: str
    trigger_type: str
    engine: str
    jenkins_job: Optional[str]
    is_active: bool
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class BuildOut(BaseModel):
    id: int
    pipeline_id: int
    build_no: int
    status: str
    trigger_type: str
    commit_sha: str
    commit_msg: str
    branch: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_sec: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}
