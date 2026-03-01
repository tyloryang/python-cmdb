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
