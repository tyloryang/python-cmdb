import asyncio
import json
import yaml
from datetime import datetime, timezone

from app.core.celery_app import celery_app
from app.core.websocket_manager import ws_manager


@celery_app.task(bind=True, name="app.tasks.pipeline_tasks.run_pipeline")
def run_pipeline(self, build_id: int):
    """执行流水线构建任务：解析 config_yaml -> 按阶段执行命令 -> 实时推送日志"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_pipeline(build_id))
    finally:
        loop.close()


async def _run_pipeline(build_id: int):
    from app.db.session import AsyncSessionLocal
    from app.models.pipeline import Pipeline, PipelineBuild, BuildStageLog
    from sqlalchemy import select

    channel = f"build:{build_id}"

    async with AsyncSessionLocal() as db:
        build_row = await db.execute(select(PipelineBuild).where(PipelineBuild.id == build_id))
        build = build_row.scalar_one_or_none()
        if not build:
            return

        pipeline_row = await db.execute(select(Pipeline).where(Pipeline.id == build.pipeline_id))
        pipeline = pipeline_row.scalar_one_or_none()
        if not pipeline:
            return

        build.status = "running"
        build.started_at = datetime.now(timezone.utc)
        await db.commit()

        await ws_manager.broadcast(channel, json.dumps({"type": "build_start", "build_id": build_id}))

        overall_success = True
        try:
            if pipeline.engine == "jenkins":
                overall_success = await _run_jenkins_pipeline(pipeline, build, channel, db)
            else:
                overall_success = await _run_local_pipeline(pipeline, build, channel, db)

        except Exception as exc:
            overall_success = False
            await ws_manager.broadcast(channel, json.dumps({"type": "error", "message": str(exc)}))

        finally:
            build.status = "success" if overall_success else "failed"
            build.finished_at = datetime.now(timezone.utc)
            if build.started_at:
                delta = build.finished_at - build.started_at.replace(tzinfo=None) \
                    if build.started_at.tzinfo is None \
                    else build.finished_at - build.started_at
                build.duration_sec = int(delta.total_seconds())
            await db.commit()

        await ws_manager.broadcast(channel, json.dumps({
            "type": "build_done", "build_id": build_id, "status": build.status
        }))


async def _run_local_pipeline(pipeline, build, channel, db):
    """本地轻量级流水线执行逻辑"""
    from app.models.pipeline import BuildStageLog
    config = yaml.safe_load(pipeline.config_yaml) or {}
    stages = config.get("stages", [])

    overall_success = True
    for order, stage_def in enumerate(stages):
        stage_name = stage_def.get("name", f"stage_{order}")
        commands = stage_def.get("commands", [])

        stage_log = BuildStageLog(
            build_id=build.id,
            stage_name=stage_name,
            stage_order=order,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(stage_log)
        await db.commit()
        await db.refresh(stage_log)

        await ws_manager.broadcast(channel, json.dumps({
            "type": "stage_start", "stage": stage_name, "order": order
        }))

        output_lines: list[str] = []
        stage_success = True
        for cmd in commands:
            lines, ok = await _run_command(cmd, channel)
            output_lines.extend(lines)
            if not ok:
                stage_success = False
                break

        stage_log.log_content = "\n".join(output_lines)
        stage_log.finished_at = datetime.now(timezone.utc)
        stage_log.status = "success" if stage_success else "failed"
        await db.commit()

        await ws_manager.broadcast(channel, json.dumps({
            "type": "stage_done", "stage": stage_name, "status": stage_log.status
        }))

        if not stage_success:
            overall_success = False
            break
    
    return overall_success


async def _run_jenkins_pipeline(pipeline, build, channel, db):
    """Jenkins 流水线执行逻辑"""
    from app.services.jenkins_service import jenkins_service
    if not pipeline.jenkins_job:
        await ws_manager.broadcast(channel, json.dumps({"type": "error", "message": "未配置 Jenkins Job 名称"}))
        return False

    try:
        # 1. 触发构建
        # 注意：这里简化处理，不处理参数化构建。实际可从 config_yaml 或构建请求中提取参数。
        jenkins_service.trigger_job(pipeline.jenkins_job)
        await ws_manager.broadcast(channel, json.dumps({"type": "log", "line": f"已在 Jenkins 触发 Job: {pipeline.jenkins_job}"}))

        # 2. 等待并获取构建编号
        # Jenkins 触发后可能在队列中，需要等待它变成真正的 build
        time_waited = 0
        jenkins_build_no = None
        while time_waited < 30: # 最多等30秒
            last_no = jenkins_service.get_last_build_number(pipeline.jenkins_job)
            if last_no:
                info = jenkins_service.get_build_info(pipeline.jenkins_job, last_no)
                # 简单判断这个 build 可能是我们触发的（通过触发时间或排队信息更准，这里简化）
                jenkins_build_no = last_no
                break
            await asyncio.sleep(2)
            time_waited += 2
        
        if not jenkins_build_no:
            await ws_manager.broadcast(channel, json.dumps({"type": "error", "message": "获取 Jenkins 构建编号超时"}))
            return False

        await ws_manager.broadcast(channel, json.dumps({"type": "log", "line": f"Jenkins 构建编号: #{jenkins_build_no}"}))

        # 3. 轮询状态和日志
        last_log_pos = 0
        while True:
            info = jenkins_service.get_build_info(pipeline.jenkins_job, jenkins_build_no)
            status = info.get("result") # SUCCESS, FAILURE, ABORTED, or None if running
            
            # 获取增量日志
            full_log = jenkins_service.get_build_console_output(pipeline.jenkins_job, jenkins_build_no)
            if len(full_log) > last_log_pos:
                new_logs = full_log[last_log_pos:]
                for line in new_logs.splitlines():
                    if line.strip():
                        await ws_manager.broadcast(channel, json.dumps({"type": "log", "line": line}))
                last_log_pos = len(full_log)

            if status:
                return status == "SUCCESS"
            
            await asyncio.sleep(3)

    except Exception as e:
        await ws_manager.broadcast(channel, json.dumps({"type": "error", "message": f"Jenkins 执行异常: {str(e)}"}))
        return False


async def _run_command(cmd: str, ws_channel: str) -> tuple[list[str], bool]:
    """在子进程中执行 shell 命令，逐行推送输出，返回 (输出行列表, 是否成功)"""
    import asyncio
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    lines: list[str] = []
    if proc.stdout:
        async for raw in proc.stdout:
            text = raw.decode("utf-8", errors="replace").rstrip()
            lines.append(text)
            await ws_manager.broadcast(ws_channel, json.dumps({"type": "log", "line": text}))

    await proc.wait()
    return lines, proc.returncode == 0
