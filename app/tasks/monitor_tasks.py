import asyncio
from datetime import datetime, timezone
from app.core.celery_app import celery_app
from app.core.websocket_manager import ws_manager
import json


@celery_app.task(name="app.tasks.monitor_tasks.collect_metrics")
def collect_metrics():
    """
    Celery Beat 每60秒触发一次：
    1. 遍历状态为 running 的服务器
    2. 通过 SSH 采集 CPU/内存/磁盘 指标
    3. 推送到 WebSocket 实时频道
    4. 检查告警规则，触发告警事件
    """
    from app.db.session import AsyncSessionLocal
    from app.models.cmdb import Server
    from app.models.monitor import AlertRule, AlertEvent
    from sqlalchemy import select

    async def _run():
        async with AsyncSessionLocal() as db:
            servers = (await db.execute(
                select(Server).where(Server.status == "running")
            )).scalars().all()

            for server in servers:
                metrics = await _collect_server_metrics(server)
                if metrics:
                    # 推送到实时 WebSocket
                    await ws_manager.broadcast(
                        "metrics:live",
                        json.dumps({"server_id": server.id, "hostname": server.hostname, **metrics})
                    )
                    # 检查告警规则
                    await _check_alert_rules(db, server.id, metrics)

    asyncio.get_event_loop().run_until_complete(_run())


async def _collect_server_metrics(server) -> dict | None:
    """通过 SSH 采集主机指标，返回 {cpu, mem, disk}"""
    import paramiko, io
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = {"hostname": server.hostname, "port": server.ssh_port,
                  "username": server.ssh_user, "timeout": 5}
        if server.ssh_auth_type == "password":
            kwargs["password"] = server.ssh_credential
        else:
            kwargs["pkey"] = paramiko.RSAKey.from_private_key(io.StringIO(server.ssh_credential))
        ssh.connect(**kwargs)

        # CPU 使用率
        _, out, _ = ssh.exec_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'")
        cpu = float(out.read().decode().strip() or 0)

        # 内存使用率
        _, out, _ = ssh.exec_command("free | awk 'NR==2{printf \"%.1f\", $3/$2*100}'")
        mem = float(out.read().decode().strip() or 0)

        # 磁盘使用率（根分区）
        _, out, _ = ssh.exec_command("df / | awk 'NR==2{print $5}' | tr -d '%'")
        disk = float(out.read().decode().strip() or 0)

        ssh.close()
        return {"cpu_usage": cpu, "mem_usage": mem, "disk_usage": disk,
                "collected_at": datetime.now(timezone.utc).isoformat()}
    except Exception:
        return None


async def _check_alert_rules(db, server_id: int, metrics: dict):
    """对比告警规则阈值，写入告警事件"""
    from app.models.monitor import AlertRule, AlertEvent
    from sqlalchemy import select

    rules = (await db.execute(
        select(AlertRule).where(
            AlertRule.target_id == server_id,
            AlertRule.target_type == "host",
            AlertRule.is_active == True,
        )
    )).scalars().all()

    ops = {"gt": lambda a, b: a > b, "lt": lambda a, b: a < b,
           "gte": lambda a, b: a >= b, "lte": lambda a, b: a <= b,
           "eq": lambda a, b: a == b}

    for rule in rules:
        value = metrics.get(rule.metric)
        if value is None:
            continue
        if ops.get(rule.condition, lambda a, b: False)(value, float(rule.threshold)):
            event = AlertEvent(
                rule_id=rule.id,
                status="firing",
                metric_value=value,
                fired_at=datetime.now(timezone.utc),
            )
            db.add(event)
            # 异步发送通知
            if rule.notify_channels:
                from app.tasks.notification_tasks import send_notification
                for ch_id in rule.notify_channels:
                    send_notification.delay(
                        ch_id,
                        f"[{rule.severity.upper()}] {rule.name} 告警",
                        f"服务器 ID {server_id} 指标 {rule.metric}={value}，触发阈值 {rule.condition} {rule.threshold}"
                    )
    await db.commit()
