"""仪表盘汇总 API"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.cmdb import Server
from app.models.pipeline import Pipeline, PipelineBuild
from app.models.release import Release
from app.models.monitor import AlertEvent
from app.models.log_analysis import LogWatcher

router = APIRouter(prefix="/dashboard", tags=["仪表盘"])


@router.get("/summary")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """返回仪表盘概览数据"""
    server_total = await db.scalar(select(func.count()).select_from(Server)) or 0
    pipeline_total = await db.scalar(select(func.count()).select_from(Pipeline)) or 0
    release_total = await db.scalar(select(func.count()).select_from(Release)) or 0
    alert_firing = await db.scalar(
        select(func.count()).select_from(AlertEvent).where(AlertEvent.status == "firing")
    ) or 0
    watcher_total = await db.scalar(select(func.count()).select_from(LogWatcher)) or 0
    build_total = await db.scalar(select(func.count()).select_from(PipelineBuild)) or 0

    # Server status distribution
    server_status_rows = (await db.execute(
        select(Server.status, func.count()).group_by(Server.status)
    )).all()
    server_status = {row[0]: row[1] for row in server_status_rows}

    # Build status distribution
    build_status_rows = (await db.execute(
        select(PipelineBuild.status, func.count()).group_by(PipelineBuild.status)
    )).all()
    build_status = {row[0]: row[1] for row in build_status_rows}

    # Recent 7 days build trend
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    build_trend_rows = (await db.execute(
        select(
            func.date(PipelineBuild.created_at).label("day"),
            func.count().label("count"),
        )
        .where(PipelineBuild.created_at >= seven_days_ago)
        .group_by(func.date(PipelineBuild.created_at))
        .order_by(func.date(PipelineBuild.created_at))
    )).all()
    build_trend = [{"date": str(row[0]), "count": row[1]} for row in build_trend_rows]

    # Recent alerts (5)
    recent_alerts_rows = (await db.execute(
        select(AlertEvent).order_by(AlertEvent.fired_at.desc()).limit(5)
    )).scalars().all()
    recent_alerts = [
        {
            "id": a.id,
            "rule_id": a.rule_id,
            "status": a.status,
            "metric_value": float(a.metric_value),
            "fired_at": str(a.fired_at),
        }
        for a in recent_alerts_rows
    ]

    # Recent builds (5)
    recent_builds_rows = (await db.execute(
        select(PipelineBuild).order_by(PipelineBuild.created_at.desc()).limit(5)
    )).scalars().all()
    recent_builds = [
        {
            "id": b.id,
            "build_no": b.build_no,
            "status": b.status,
            "pipeline_id": b.pipeline_id,
            "created_at": str(b.created_at),
        }
        for b in recent_builds_rows
    ]

    # OS distribution for servers
    os_rows = (await db.execute(
        select(Server.os_type, func.count()).where(Server.os_type != "").group_by(Server.os_type)
    )).all()
    os_distribution = {row[0]: row[1] for row in os_rows}

    return {
        "counts": {
            "servers": server_total,
            "pipelines": pipeline_total,
            "releases": release_total,
            "alert_firing": alert_firing,
            "watchers": watcher_total,
            "builds": build_total,
        },
        "server_status": server_status,
        "build_status": build_status,
        "build_trend": build_trend,
        "os_distribution": os_distribution,
        "recent_alerts": recent_alerts,
        "recent_builds": recent_builds,
    }
