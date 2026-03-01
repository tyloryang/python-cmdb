from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.models.pipeline import Pipeline, PipelineBuild
from app.models.user import User
from app.schemas.pipeline import PipelineCreate, PipelineOut, BuildOut
from app.schemas.common import PageResult
from app.core.websocket_manager import ws_manager

router = APIRouter(prefix="/cicd", tags=["CI/CD流水线"])


@router.get("/pipelines", response_model=PageResult[PipelineOut])
async def list_pipelines(
    page: int = 1, page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skip = (page - 1) * page_size
    total = await db.scalar(select(func.count()).select_from(Pipeline))
    result = await db.execute(select(Pipeline).offset(skip).limit(page_size))
    return PageResult(total=total, page=page, page_size=page_size, items=list(result.scalars().all()))


@router.post("/pipelines", response_model=PipelineOut, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    body: PipelineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pipeline = Pipeline(**body.model_dump(), created_by=current_user.id)
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)
    return pipeline


@router.get("/pipelines/{pipeline_id}", response_model=PipelineOut)
async def get_pipeline(pipeline_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="流水线不存在")
    return pipeline


@router.delete("/pipelines/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline(pipeline_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="流水线不存在")
    await db.delete(pipeline)
    await db.commit()


@router.post("/pipelines/{pipeline_id}/trigger", response_model=BuildOut)
async def trigger_pipeline(
    pipeline_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline or not pipeline.is_active:
        raise HTTPException(status_code=404, detail="流水线不存在或已禁用")

    # 计算本流水线的下一个 build_no
    max_no = await db.scalar(
        select(func.max(PipelineBuild.build_no)).where(PipelineBuild.pipeline_id == pipeline_id)
    )
    build_no = (max_no or 0) + 1

    build = PipelineBuild(
        pipeline_id=pipeline_id,
        build_no=build_no,
        status="pending",
        trigger_type="manual",
        triggered_by=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(build)
    await db.commit()
    await db.refresh(build)

    # 异步触发 Celery 任务
    from app.tasks.pipeline_tasks import run_pipeline
    run_pipeline.delay(build.id)

    return build


@router.get("/builds/{build_id}", response_model=BuildOut)
async def get_build(build_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(PipelineBuild).where(PipelineBuild.id == build_id))
    build = result.scalar_one_or_none()
    if not build:
        raise HTTPException(status_code=404, detail="构建记录不存在")
    return build


@router.get("/pipelines/{pipeline_id}/builds", response_model=PageResult[BuildOut])
async def list_builds(
    pipeline_id: int, page: int = 1, page_size: int = 20,
    db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user),
):
    skip = (page - 1) * page_size
    total = await db.scalar(
        select(func.count()).select_from(PipelineBuild).where(PipelineBuild.pipeline_id == pipeline_id)
    )
    result = await db.execute(
        select(PipelineBuild)
        .where(PipelineBuild.pipeline_id == pipeline_id)
        .order_by(PipelineBuild.build_no.desc())
        .offset(skip).limit(page_size)
    )
    return PageResult(total=total, page=page, page_size=page_size, items=list(result.scalars().all()))


@router.websocket("/builds/{build_id}/log")
async def build_log_ws(build_id: int, websocket: WebSocket):
    """WebSocket 实时构建日志推送，Celery 任务通过 ws_manager.broadcast 写入"""
    channel = f"build:{build_id}"
    await ws_manager.connect(channel, websocket)
    try:
        while True:
            # 保持连接，等待服务端推送
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(channel, websocket)
