import asyncio
import io
import json
from datetime import datetime, timezone

import paramiko

from app.core.celery_app import celery_app
from app.core.websocket_manager import ws_manager


@celery_app.task(bind=True, name="app.tasks.release_tasks.deploy_release")
def deploy_release(self, release_id: int):
    """SSH 部署任务：逐台目标服务器执行部署脚本 / Docker 镜像更新，推送实时日志"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_deploy_release(release_id))
    finally:
        loop.close()


async def _deploy_release(release_id: int):
    from app.db.session import AsyncSessionLocal
    from app.models.release import Release
    from app.models.cmdb import Server
    from sqlalchemy import select

    channel = f"release:{release_id}"

    async with AsyncSessionLocal() as db:
        rel_row = await db.execute(select(Release).where(Release.id == release_id))
        release = rel_row.scalar_one_or_none()
        if not release:
            return

        await ws_manager.broadcast(channel, json.dumps({
            "type": "deploy_start", "release_id": release_id, "version": release.version
        }))

        overall_success = True
        try:
            server_ids = release.target_servers or []
            srv_rows = await db.execute(select(Server).where(Server.id.in_(server_ids)))
            servers = srv_rows.scalars().all()

            deploy_config = release.deploy_config or {}
            deploy_script = deploy_config.get("deploy_script", "")
            docker_image = deploy_config.get("docker_image", "")
            container_name = deploy_config.get("container_name", "app")

            for server in servers:
                ok = await asyncio.get_event_loop().run_in_executor(
                    None,
                    _deploy_to_server,
                    server, release.version, deploy_script, docker_image, container_name, channel,
                )
                if not ok:
                    overall_success = False

        except Exception as exc:
            overall_success = False
            await ws_manager.broadcast(channel, json.dumps({"type": "error", "message": str(exc)}))

        finally:
            release.status = "success" if overall_success else "failed"
            await db.commit()

        await ws_manager.broadcast(channel, json.dumps({
            "type": "deploy_done", "release_id": release_id, "status": release.status
        }))


def _deploy_to_server(
    server,
    version: str,
    deploy_script: str,
    docker_image: str,
    container_name: str,
    ws_channel: str,
) -> bool:
    """同步 SSH 部署到单台服务器，推送日志到 WebSocket 频道"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict = {
        "hostname": server.hostname,
        "port": server.ssh_port,
        "username": server.ssh_user,
        "timeout": 15,
    }
    if server.ssh_auth_type == "password":
        connect_kwargs["password"] = server.ssh_credential
    else:
        connect_kwargs["pkey"] = paramiko.RSAKey.from_private_key(
            io.StringIO(server.ssh_credential)
        )

    def _broadcast(msg: dict):
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(ws_manager.broadcast(ws_channel, json.dumps(msg)))
            loop.close()
        except Exception:
            pass

    try:
        ssh.connect(**connect_kwargs)
        _broadcast({"type": "log", "server": server.hostname, "line": f"=== 连接成功: {server.hostname} ==="})

        # 决定执行的命令
        if deploy_script:
            commands = deploy_script.strip().splitlines()
        elif docker_image:
            commands = [
                f"docker pull {docker_image}:{version}",
                f"docker stop {container_name} || true",
                f"docker rm {container_name} || true",
                f"docker run -d --name {container_name} {docker_image}:{version}",
            ]
        else:
            _broadcast({"type": "log", "server": server.hostname,
                        "line": "未配置 deploy_script 或 docker_image，跳过"})
            return True

        for cmd in commands:
            _broadcast({"type": "log", "server": server.hostname, "line": f"$ {cmd}"})
            _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
            exit_code = stdout.channel.recv_exit_status()
            for line in stdout.read().decode("utf-8", errors="replace").splitlines():
                _broadcast({"type": "log", "server": server.hostname, "line": line})
            err_text = stderr.read().decode("utf-8", errors="replace").strip()
            if err_text:
                _broadcast({"type": "log", "server": server.hostname, "line": f"[stderr] {err_text}"})
            if exit_code != 0:
                _broadcast({"type": "log", "server": server.hostname,
                            "line": f"命令失败 (exit {exit_code}): {cmd}"})
                return False

        _broadcast({"type": "log", "server": server.hostname, "line": "=== 部署成功 ==="})
        return True

    except Exception as exc:
        _broadcast({"type": "log", "server": server.hostname, "line": f"部署异常: {exc}"})
        return False
    finally:
        ssh.close()
