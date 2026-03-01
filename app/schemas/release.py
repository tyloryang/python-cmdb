from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class ReleaseCreate(BaseModel):
    app_id: int
    version: str
    build_id: Optional[int] = None
    deploy_type: str = "full"
    canary_weight: int = 0
    target_servers: List[int]
    deploy_config: Optional[dict] = None
    description: Optional[str] = None


class ReleaseOut(BaseModel):
    id: int
    app_id: int
    version: str
    status: str
    deploy_type: str
    canary_weight: int
    target_servers: List[int]
    created_by: int
    deployed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class AppCreate(BaseModel):
    name: str
    description: Optional[str] = None
    pipeline_id: Optional[int] = None


class AppOut(BaseModel):
    id: int
    name: str
    pipeline_id: Optional[int]
    owner_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
