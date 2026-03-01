from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class AlertRuleCreate(BaseModel):
    name: str
    target_type: str = "host"
    target_id: Optional[int] = None
    metric: str
    condition: str
    threshold: float
    duration_sec: int = 60
    severity: str = "warning"
    notify_channels: Optional[List[int]] = None


class AlertRuleOut(BaseModel):
    id: int
    name: str
    target_type: str
    metric: str
    condition: str
    threshold: float
    severity: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertEventOut(BaseModel):
    id: int
    rule_id: int
    status: str
    metric_value: float
    fired_at: datetime
    resolved_at: Optional[datetime]
    notified: bool

    model_config = {"from_attributes": True}
