"""
log_analysis/watchers.py
~~~~~~~~~~~~~~~~~~~~~~~~
REST API + WebSocket：
  POST   /log-analysis/watchers            — 创建监控任务
  GET    /log-analysis/watchers            — 列表（分页）
  GET    /log-analysis/watchers/{id}       — 详情
  PATCH  /log-analysis/watchers/{id}       — 更新配置
  DELETE /log-analysis/watchers/{id}       — 删除
  POST   /log-analysis/watchers/{id}/start — 启动
  POST   /log-analysis/watchers/{id}/pause — 暂停
  POST   /log-analysis/watchers/{id}/run   — 立即触发一次解析
  GET    /log-analysis/watchers/{id}/templates     — 模板列表（按命中次数排序）
  WS     /log-analysis/watchers/{id}/live          — 实时推送
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.log_analysis import LogWatcher, LogTemplate
from app.models.user import User
from app.schemas.log_analysis import LogWatcherCreate, LogWatcherUpdate, LogWatcherOut, LogTemplateOut, LogAskInput, LogAskOutput
from app.schemas.common import PageResult
from app.core.websocket_manager import ws_manager

router = APIRouter(prefix="/log-analysis", tags=["日志聚合分析"])


# ─── Watcher CRUD ─────────────────────────────────────────────────────────────

@router.get("/watchers", response_model=PageResult[LogWatcherOut])
async def list_watchers(
    page: int = 1, page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    skip = (page - 1) * page_size
    total = await db.scalar(select(func.count()).select_from(LogWatcher))
    rows = await db.execute(select(LogWatcher).offset(skip).limit(page_size))
    return PageResult(total=total, page=page, page_size=page_size, items=list(rows.scalars().all()))


@router.post("/watchers", response_model=LogWatcherOut, status_code=status.HTTP_201_CREATED)
async def create_watcher(
    body: LogWatcherCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = body.model_dump()
    # masking_patterns 序列化为 dict 列表
    if data.get("masking_patterns"):
        data["masking_patterns"] = [
            p if isinstance(p, dict) else p for p in data["masking_patterns"]
        ]
    watcher = LogWatcher(**data, created_by=current_user.id)
    db.add(watcher)
    await db.commit()
    await db.refresh(watcher)
    return watcher


@router.get("/watchers/{watcher_id}", response_model=LogWatcherOut)
async def get_watcher(
    watcher_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    watcher = await _get_or_404(db, watcher_id)
    return watcher


@router.patch("/watchers/{watcher_id}", response_model=LogWatcherOut)
async def update_watcher(
    watcher_id: int,
    body: LogWatcherUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    watcher = await _get_or_404(db, watcher_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(watcher, k, v)
    await db.commit()
    await db.refresh(watcher)
    return watcher


@router.delete("/watchers/{watcher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watcher(
    watcher_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    watcher = await _get_or_404(db, watcher_id)
    await db.delete(watcher)
    await db.commit()


# ─── 启停控制 ─────────────────────────────────────────────────────────────────

@router.post("/watchers/{watcher_id}/start", response_model=LogWatcherOut)
async def start_watcher(
    watcher_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    watcher = await _get_or_404(db, watcher_id)
    watcher.status = "active"
    watcher.last_error = None
    await db.commit()
    await db.refresh(watcher)
    return watcher


@router.post("/watchers/{watcher_id}/pause", response_model=LogWatcherOut)
async def pause_watcher(
    watcher_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    watcher = await _get_or_404(db, watcher_id)
    watcher.status = "paused"
    await db.commit()
    await db.refresh(watcher)
    return watcher


@router.post("/watchers/{watcher_id}/run")
async def run_watcher_now(
    watcher_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """立即触发一次日志解析（使用 asyncio 后台任务）"""
    await _get_or_404(db, watcher_id)
    import asyncio
    from app.tasks.log_tasks import _process_watcher
    asyncio.create_task(_process_watcher(watcher_id))
    return {"msg": "已触发解析任务"}


# ─── 模板查询 ─────────────────────────────────────────────────────────────────

@router.get("/watchers/{watcher_id}/templates", response_model=PageResult[LogTemplateOut])
async def list_templates(
    watcher_id: int,
    page: int = 1,
    page_size: int = 50,
    order_by: str = "hit_count",   # hit_count | last_seen_at
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_or_404(db, watcher_id)
    skip = (page - 1) * page_size

    sort_col = LogTemplate.last_seen_at if order_by == "last_seen_at" else LogTemplate.hit_count
    total = await db.scalar(
        select(func.count()).select_from(LogTemplate).where(LogTemplate.watcher_id == watcher_id)
    )
    rows = await db.execute(
        select(LogTemplate)
        .where(LogTemplate.watcher_id == watcher_id)
        .order_by(sort_col.desc())
        .offset(skip).limit(page_size)
    )
    return PageResult(total=total, page=page, page_size=page_size, items=list(rows.scalars().all()))


@router.post("/watchers/{watcher_id}/ask", response_model=LogAskOutput)
async def ask_watcher_logs(
    watcher_id: int,
    body: LogAskInput,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    通过 AI 查询日志分析结果
    """
    watcher = await _get_or_404(db, watcher_id)
    from app.services.ai_service import ask_about_logs
    answer = await ask_about_logs(db, watcher, body.question, body.hours)
    return LogAskOutput(answer=answer)


# ─── WebSocket 实时推送 ───────────────────────────────────────────────────────

@router.websocket("/watchers/{watcher_id}/live")
async def live_ws(watcher_id: int, websocket: WebSocket):
    """
    订阅指定 watcher 的实时聚合事件。
    推送消息格式：
      {"type": "scan_done", "watcher_id": N, "new_lines": N, "templates_touched": N}
      {"type": "template_created", "watcher_id": N, "cluster_id": N, "template": "..."}
      {"type": "template_updated", "watcher_id": N, "cluster_id": N, "template": "..."}
    """
    channel = f"log_analysis:{watcher_id}"
    await ws_manager.connect(channel, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(channel, websocket)


# ─── 工具 ─────────────────────────────────────────────────────────────────────

async def _get_or_404(db: AsyncSession, watcher_id: int) -> LogWatcher:
    row = await db.execute(select(LogWatcher).where(LogWatcher.id == watcher_id))
    watcher = row.scalar_one_or_none()
    if not watcher:
        raise HTTPException(status_code=404, detail="日志监控任务不存在")
    return watcher
