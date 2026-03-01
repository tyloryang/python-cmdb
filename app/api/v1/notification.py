from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.models.notification import NotificationChannel
from app.models.user import User
from app.schemas.notification import NotificationChannelCreate, NotificationChannelOut
from app.schemas.common import PageResult

router = APIRouter(prefix="/notification", tags=["消息通知"])


@router.get("/channels", response_model=PageResult[NotificationChannelOut])
async def list_channels(page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    skip = (page - 1) * page_size
    total = await db.scalar(select(func.count()).select_from(NotificationChannel))
    result = await db.execute(select(NotificationChannel).offset(skip).limit(page_size))
    return PageResult(total=total, page=page, page_size=page_size, items=list(result.scalars().all()))


@router.post("/channels", response_model=NotificationChannelOut, status_code=status.HTTP_201_CREATED)
async def create_channel(body: NotificationChannelCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    ch = NotificationChannel(**body.model_dump())
    db.add(ch)
    await db.commit()
    await db.refresh(ch)
    return ch


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(channel_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(NotificationChannel).where(NotificationChannel.id == channel_id))
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="通知渠道不存在")
    await db.delete(ch)
    await db.commit()


@router.post("/channels/{channel_id}/test")
async def test_channel(channel_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(NotificationChannel).where(NotificationChannel.id == channel_id))
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="通知渠道不存在")
    from app.tasks.notification_tasks import send_notification
    send_notification.delay(channel_id, "测试通知", "这是一条来自 DevOps 平台的测试消息")
    return {"msg": "测试消息已发送"}
