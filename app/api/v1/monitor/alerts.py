from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.models.monitor import AlertRule, AlertEvent
from app.models.user import User
from app.schemas.monitor import AlertRuleCreate, AlertRuleOut, AlertEventOut
from app.schemas.common import PageResult
from app.core.websocket_manager import ws_manager
import asyncio, json

router = APIRouter(prefix="/monitor", tags=["监控告警"])


@router.get("/alert-rules", response_model=PageResult[AlertRuleOut])
async def list_rules(page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    skip = (page - 1) * page_size
    total = await db.scalar(select(func.count()).select_from(AlertRule))
    result = await db.execute(select(AlertRule).offset(skip).limit(page_size))
    return PageResult(total=total, page=page, page_size=page_size, items=list(result.scalars().all()))


@router.post("/alert-rules", response_model=AlertRuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(body: AlertRuleCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rule = AlertRule(**body.model_dump(), created_by=current_user.id)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.put("/alert-rules/{rule_id}", response_model=AlertRuleOut)
async def update_rule(rule_id: int, body: AlertRuleCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="告警规则不存在")
    for k, v in body.model_dump().items():
        setattr(rule, k, v)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/alert-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="告警规则不存在")
    await db.delete(rule)
    await db.commit()


@router.get("/alert-events", response_model=PageResult[AlertEventOut])
async def list_events(
    page: int = 1, page_size: int = 20,
    status: str = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    skip = (page - 1) * page_size
    query = select(AlertEvent)
    if status:
        query = query.where(AlertEvent.status == status)
    total = await db.scalar(select(func.count()).select_from(AlertEvent))
    result = await db.execute(query.order_by(AlertEvent.fired_at.desc()).offset(skip).limit(page_size))
    return PageResult(total=total, page=page, page_size=page_size, items=list(result.scalars().all()))


@router.websocket("/metrics/live")
async def metrics_live(websocket: WebSocket):
    """WebSocket 实时指标推送，Celery 采集后 broadcast 到此频道"""
    channel = "metrics:live"
    await ws_manager.connect(channel, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(channel, websocket)
