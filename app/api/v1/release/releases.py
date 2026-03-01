from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.models.release import Application, Release, RollbackRecord
from app.models.user import User
from app.schemas.release import AppCreate, AppOut, ReleaseCreate, ReleaseOut
from app.schemas.common import PageResult

router = APIRouter(prefix="/release", tags=["发布管理"])


# ---- 应用管理 ----

@router.get("/apps", response_model=PageResult[AppOut])
async def list_apps(page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    skip = (page - 1) * page_size
    total = await db.scalar(select(func.count()).select_from(Application))
    result = await db.execute(select(Application).offset(skip).limit(page_size))
    return PageResult(total=total, page=page, page_size=page_size, items=list(result.scalars().all()))


@router.post("/apps", response_model=AppOut, status_code=status.HTTP_201_CREATED)
async def create_app(body: AppCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    app = Application(**body.model_dump(), owner_id=current_user.id)
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


# ---- 发布单 ----

@router.get("/releases", response_model=PageResult[ReleaseOut])
async def list_releases(page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    skip = (page - 1) * page_size
    total = await db.scalar(select(func.count()).select_from(Release))
    result = await db.execute(select(Release).order_by(Release.created_at.desc()).offset(skip).limit(page_size))
    return PageResult(total=total, page=page, page_size=page_size, items=list(result.scalars().all()))


@router.post("/releases", response_model=ReleaseOut, status_code=status.HTTP_201_CREATED)
async def create_release(body: ReleaseCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    release = Release(**body.model_dump(), created_by=current_user.id, status="draft")
    db.add(release)
    await db.commit()
    await db.refresh(release)
    return release


@router.get("/releases/{release_id}", response_model=ReleaseOut)
async def get_release(release_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(Release).where(Release.id == release_id))
    release = result.scalar_one_or_none()
    if not release:
        raise HTTPException(status_code=404, detail="发布单不存在")
    return release


@router.post("/releases/{release_id}/deploy", response_model=ReleaseOut)
async def deploy_release(release_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Release).where(Release.id == release_id))
    release = result.scalar_one_or_none()
    if not release:
        raise HTTPException(status_code=404, detail="发布单不存在")
    if release.status not in ("draft", "failed"):
        raise HTTPException(status_code=400, detail=f"当前状态 {release.status} 不允许发布")

    release.status = "deploying"
    release.deployed_by = current_user.id
    release.deployed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(release)

    from app.tasks.release_tasks import deploy_release
    deploy_release.delay(release.id)

    return release


@router.post("/releases/{release_id}/rollback")
async def rollback_release(
    release_id: int,
    to_version: str,
    reason: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Release).where(Release.id == release_id))
    release = result.scalar_one_or_none()
    if not release:
        raise HTTPException(status_code=404, detail="发布单不存在")

    record = RollbackRecord(
        release_id=release_id,
        from_version=release.version,
        to_version=to_version,
        reason=reason,
        operated_by=current_user.id,
        operated_at=datetime.now(timezone.utc),
    )
    release.status = "rolled_back"
    db.add(record)
    await db.commit()
    return {"msg": f"已回滚至 {to_version}"}
