from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.common import PageResult
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int]
    username: str
    action: str
    resource: str
    client_ip: str
    status_code: int
    created_at: datetime

    model_config = {"from_attributes": True}


router = APIRouter(prefix="/audit", tags=["审计日志"])


@router.get("/logs", response_model=PageResult[AuditLogOut])
async def list_audit_logs(
    page: int = 1, page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    skip = (page - 1) * page_size
    total = await db.scalar(select(func.count()).select_from(AuditLog))
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(page_size)
    )
    return PageResult(total=total, page=page, page_size=page_size, items=list(result.scalars().all()))
