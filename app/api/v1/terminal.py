import asyncio
import paramiko
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.models.cmdb import Server
from app.models.user import User

router = APIRouter(prefix="/terminal", tags=["WebSSH终端"])


@router.websocket("/{server_id}")
async def terminal(server_id: int, websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    """
    WebSSH 终端：浏览器 <-> WebSocket <-> paramiko SSH
    前端发送 JSON: {"type": "input", "data": "ls\n"} 或 {"type": "resize", "rows": 24, "cols": 80}
    后端推送 JSON: {"type": "output", "data": "..."}
    """
    await websocket.accept()

    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        await websocket.send_json({"type": "error", "data": "服务器不存在"})
        await websocket.close()
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        connect_kwargs = {
            "hostname": server.hostname,
            "port": server.ssh_port,
            "username": server.ssh_user,
            "timeout": 10,
        }
        if server.ssh_auth_type == "password":
            connect_kwargs["password"] = server.ssh_credential
        else:
            import io
            key = paramiko.RSAKey.from_private_key(io.StringIO(server.ssh_credential))
            connect_kwargs["pkey"] = key

        ssh.connect(**connect_kwargs)
        channel = ssh.invoke_shell(term="xterm", width=80, height=24)
        channel.setblocking(False)

        await websocket.send_json({"type": "output", "data": f"已连接到 {server.hostname}\r\n"})

        async def read_from_ssh():
            """从 SSH 读取输出，推送到 WebSocket"""
            loop = asyncio.get_event_loop()
            while True:
                try:
                    data = await loop.run_in_executor(None, _read_channel, channel)
                    if data:
                        await websocket.send_json({"type": "output", "data": data})
                    elif channel.closed or channel.exit_status_ready():
                        break
                    await asyncio.sleep(0.05)
                except Exception:
                    break

        ssh_reader = asyncio.create_task(read_from_ssh())

        try:
            while True:
                msg = await websocket.receive_json()
                if msg.get("type") == "input":
                    channel.send(msg.get("data", ""))
                elif msg.get("type") == "resize":
                    channel.resize_pty(width=msg.get("cols", 80), height=msg.get("rows", 24))
        except WebSocketDisconnect:
            pass
        finally:
            ssh_reader.cancel()

    except Exception as e:
        await websocket.send_json({"type": "error", "data": f"连接失败: {e}"})
    finally:
        ssh.close()


def _read_channel(channel) -> str:
    try:
        if channel.recv_ready():
            return channel.recv(4096).decode("utf-8", errors="replace")
        if channel.recv_stderr_ready():
            return channel.recv_stderr(4096).decode("utf-8", errors="replace")
    except Exception:
        pass
    return ""
