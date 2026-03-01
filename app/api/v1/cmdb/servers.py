from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.models.cmdb import Server, IpAddress
from app.models.user import User
from app.schemas.cmdb import ServerCreate, ServerUpdate, ServerOut, IpCreate, IpOut
from app.schemas.common import PageResult

router = APIRouter(prefix="/cmdb", tags=["CMDB资产"])


# ---- 服务器 ----

@router.get("/servers", response_model=PageResult[ServerOut])
async def list_servers(
    page: int = 1, page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    skip = (page - 1) * page_size
    total = await db.scalar(select(func.count()).select_from(Server))
    result = await db.execute(select(Server).offset(skip).limit(page_size))
    return PageResult(total=total, page=page, page_size=page_size, items=list(result.scalars().all()))


@router.post("/servers", response_model=ServerOut, status_code=status.HTTP_201_CREATED)
async def create_server(body: ServerCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    existing = await db.execute(select(Server).where(Server.hostname == body.hostname))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="主机名已存在")
    server = Server(**body.model_dump())
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server


@router.get("/servers/{server_id}", response_model=ServerOut)
async def get_server(server_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    return server


@router.put("/servers/{server_id}", response_model=ServerOut)
async def update_server(
    server_id: int, body: ServerUpdate,
    db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user),
):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(server, k, v)
    await db.commit()
    await db.refresh(server)
    return server


@router.post("/servers/{server_id}/ping")
async def ping_server(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """测试 SSH 连接"""
    import asyncio
    import paramiko
    import io
    
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
        
    def _test_ssh():
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = {
            "hostname": server.hostname,
            "port": server.ssh_port,
            "username": server.ssh_user,
            "timeout": 5,
        }
        if server.ssh_auth_type == "password":
            kwargs["password"] = server.ssh_credential
        elif server.ssh_credential:
            kwargs["pkey"] = paramiko.RSAKey.from_private_key(io.StringIO(server.ssh_credential))
            
        try:
            ssh.connect(**kwargs)
            # Test executing a simple command
            _, stdout, _ = ssh.exec_command("echo hello")
            out = stdout.read().decode().strip()
            return True, "连接成功" if out == "hello" else "连接成功但命令返回异常"
        except Exception as e:
            return False, str(e)
        finally:
            ssh.close()
            
    success, msg = await asyncio.get_event_loop().run_in_executor(None, _test_ssh)
    if not success:
        raise HTTPException(status_code=400, detail=f"SSH 连接失败: {msg}")
    
    return {"msg": "连接成功", "success": True}


@router.post("/servers/{server_id}/collect")
async def collect_server_info(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """SSH 远程采集服务器硬件与系统信息"""
    import asyncio
    import paramiko
    import io

    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    def _collect():
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = {
            "hostname": server.hostname,
            "port": server.ssh_port,
            "username": server.ssh_user,
            "timeout": 10,
        }
        if server.ssh_auth_type == "password":
            kwargs["password"] = server.ssh_credential
        elif server.ssh_credential:
            kwargs["pkey"] = paramiko.RSAKey.from_private_key(io.StringIO(server.ssh_credential))

        info = {}
        try:
            ssh.connect(**kwargs)

            def _exec(cmd):
                _, stdout, _ = ssh.exec_command(cmd)
                return stdout.read().decode().strip()

            # CPU cores
            cpu_str = _exec("nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo")
            info["cpu_cores"] = int(cpu_str) if cpu_str.isdigit() else 0

            # Memory (GB)
            mem_str = _exec("grep MemTotal /proc/meminfo | awk '{print $2}'")
            info["memory_gb"] = round(int(mem_str) / 1024 / 1024) if mem_str.isdigit() else 0

            # Disk (GB) – root partition
            disk_str = _exec("df -BG / | tail -1 | awk '{gsub(/G/,\"\",$2); print $2}'")
            try:
                info["disk_gb"] = int(float(disk_str))
            except (ValueError, TypeError):
                info["disk_gb"] = 0

            # OS info
            os_release = _exec("cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null")
            os_type = ""
            os_version = ""
            for line in os_release.splitlines():
                if line.startswith("ID="):
                    os_type = line.split("=", 1)[1].strip('"').strip()
                elif line.startswith("VERSION_ID="):
                    os_version = line.split("=", 1)[1].strip('"').strip()
            if not os_type:
                os_type = _exec("uname -s").lower()
            if not os_version:
                os_version = _exec("uname -r")
            info["os_type"] = os_type
            info["os_version"] = os_version

            # Uptime
            info["uptime"] = _exec("uptime -p 2>/dev/null || uptime")

            # Kernel
            info["kernel"] = _exec("uname -r")

            # Hostname (real)
            info["real_hostname"] = _exec("hostname")

            # IP addresses
            info["ip_list"] = _exec("hostname -I 2>/dev/null || echo ''").split()

            return True, info
        except Exception as e:
            return False, str(e)
        finally:
            ssh.close()

    success, data = await asyncio.get_event_loop().run_in_executor(None, _collect)
    if not success:
        raise HTTPException(status_code=400, detail=f"采集失败: {data}")

    # Update server record
    server.cpu_cores = data.get("cpu_cores", server.cpu_cores)
    server.memory_gb = data.get("memory_gb", server.memory_gb)
    server.disk_gb = data.get("disk_gb", server.disk_gb)
    server.os_type = data.get("os_type", server.os_type)
    server.os_version = data.get("os_version", server.os_version)
    await db.commit()
    await db.refresh(server)

    return {
        "msg": "采集成功",
        "success": True,
        "collected": data,
        "server": {
            "id": server.id,
            "hostname": server.hostname,
            "cpu_cores": server.cpu_cores,
            "memory_gb": server.memory_gb,
            "disk_gb": server.disk_gb,
            "os_type": server.os_type,
            "os_version": server.os_version,
        },
    }


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(server_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    await db.delete(server)
    await db.commit()


# ---- IP 地址 ----

@router.get("/ips", response_model=PageResult[IpOut])
async def list_ips(page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    skip = (page - 1) * page_size
    total = await db.scalar(select(func.count()).select_from(IpAddress))
    result = await db.execute(select(IpAddress).offset(skip).limit(page_size))
    return PageResult(total=total, page=page, page_size=page_size, items=list(result.scalars().all()))


@router.post("/ips", response_model=IpOut, status_code=status.HTTP_201_CREATED)
async def create_ip(body: IpCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    ip = IpAddress(**body.model_dump(), is_used=body.server_id is not None)
    db.add(ip)
    await db.commit()
    await db.refresh(ip)
    return ip
