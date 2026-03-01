"""
log_tasks.py
~~~~~~~~~~~~
Celery 任务：
  - scan_log_watchers  — Beat 每 30 秒触发，为所有 active watcher 分发子任务
  - process_log_watcher — 单个 watcher 的 tail + drain3 解析 + DB 写入 + WebSocket 推送
"""
import asyncio
import json
from datetime import datetime, timezone

from app.core.celery_app import celery_app
from app.core.websocket_manager import ws_manager


# ─── Beat 调度入口 ────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.log_tasks.scan_log_watchers")
def scan_log_watchers():
    """遍历所有 active LogWatcher，为每个发起 process_log_watcher 子任务"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_dispatch_watchers())
    finally:
        loop.close()


async def _dispatch_watchers():
    from app.db.session import AsyncSessionLocal
    from app.models.log_analysis import LogWatcher
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        rows = await db.execute(select(LogWatcher).where(LogWatcher.status == "active"))
        watchers = rows.scalars().all()

    for w in watchers:
        process_log_watcher.delay(w.id)


# ─── 单 Watcher 处理任务 ──────────────────────────────────────────────────────

@celery_app.task(bind=True, name="app.tasks.log_tasks.process_log_watcher")
def process_log_watcher(self, watcher_id: int):
    """
    1. 读取 LogWatcher 配置
    2. Tail 日志文件（本地 or SSH）
    3. 送入 drain3 解析
    4. Upsert LogTemplate 记录
    5. 推送 WebSocket 实时事件
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_process_watcher(watcher_id))
    finally:
        loop.close()


async def _process_watcher(watcher_id: int):
    from app.db.session import AsyncSessionLocal
    from app.models.log_analysis import LogWatcher, LogTemplate
    from app.models.cmdb import Server
    from app.services.log_drain_service import tail_local, tail_remote, parse_lines
    from sqlalchemy import select

    channel = f"log_analysis:{watcher_id}"

    async with AsyncSessionLocal() as db:
        row = await db.execute(select(LogWatcher).where(LogWatcher.id == watcher_id))
        watcher = row.scalar_one_or_none()
        if not watcher or watcher.status != "active":
            return

        # ── 1. Tail ──────────────────────────────────────────────────────────
        try:
            if watcher.source_type == "remote" and watcher.server_id:
                srv_row = await db.execute(select(Server).where(Server.id == watcher.server_id))
                server = srv_row.scalar_one_or_none()
                lines, new_pos = await asyncio.get_event_loop().run_in_executor(
                    None, tail_remote, server, watcher.log_path, watcher.last_pos
                )
            else:
                lines, new_pos = await asyncio.get_event_loop().run_in_executor(
                    None, tail_local, watcher.log_path, watcher.last_pos
                )
        except Exception as exc:
            watcher.status = "error"
            watcher.last_error = str(exc)
            await db.commit()
            return

        if not lines:
            watcher.last_run_at = datetime.now(timezone.utc)
            await db.commit()
            return

        # ── 2. drain3 解析 ────────────────────────────────────────────────────
        parse_results = await asyncio.get_event_loop().run_in_executor(
            None, parse_lines, watcher, lines
        )

        # ── 3. Upsert LogTemplate ─────────────────────────────────────────────
        now = datetime.now(timezone.utc)
        ws_events: list[dict] = []

        for item in parse_results:
            cluster_id = item["cluster_id"]
            template_str = item["template_str"]
            raw_line = item["raw_line"]
            change_type = item["change_type"]

            tpl_row = await db.execute(
                select(LogTemplate).where(
                    LogTemplate.watcher_id == watcher_id,
                    LogTemplate.cluster_id == cluster_id,
                )
            )
            tpl = tpl_row.scalar_one_or_none()

            if tpl is None:
                # 新模板
                tpl = LogTemplate(
                    watcher_id=watcher_id,
                    cluster_id=cluster_id,
                    template_str=template_str,
                    hit_count=1,
                    sample_logs=[raw_line],
                    first_seen_at=now,
                    last_seen_at=now,
                )
                db.add(tpl)
                ws_events.append({"type": "template_created", "cluster_id": cluster_id, "template": template_str})
            else:
                tpl.hit_count += 1
                tpl.last_seen_at = now
                # 模板字符串可能随 drain3 学习而更新
                if tpl.template_str != template_str:
                    tpl.template_str = template_str
                    ws_events.append({"type": "template_updated", "cluster_id": cluster_id, "template": template_str})
                # 追加样本（最多 10 条）
                samples: list = list(tpl.sample_logs or [])
                if len(samples) < 10:
                    samples.append(raw_line)
                    tpl.sample_logs = samples

        watcher.last_pos = new_pos
        watcher.last_run_at = now
        watcher.last_error = None
        await db.commit()

        # ── 4. WebSocket 推送 ─────────────────────────────────────────────────
        summary = {
            "type": "scan_done",
            "watcher_id": watcher_id,
            "new_lines": len(lines),
            "templates_touched": len({r["cluster_id"] for r in parse_results}),
        }
        await ws_manager.broadcast(channel, json.dumps(summary))

        for evt in ws_events:
            evt["watcher_id"] = watcher_id
            await ws_manager.broadcast(channel, json.dumps(evt))
