from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class NotificationChannelCreate(BaseModel):
    name: str
    channel_type: str  # dingtalk / email / webhook
    config: dict       # {"webhook": "https://..."} or {"smtp": ..., "to": [...]}


class NotificationChannelOut(BaseModel):
    id: int
    name: str
    channel_type: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
