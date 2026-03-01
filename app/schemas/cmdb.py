from typing import Optional
from pydantic import BaseModel


class ServerCreate(BaseModel):
    hostname: str
    idc_room_id: Optional[int] = None
    asset_no: Optional[str] = None
    status: str = "running"
    os_type: str = ""
    os_version: str = ""
    cpu_cores: int = 0
    memory_gb: int = 0
    disk_gb: int = 0
    ssh_port: int = 22
    ssh_user: str = "root"
    ssh_auth_type: str = "key"
    ssh_credential: Optional[str] = None
    tags: Optional[dict] = None


class ServerUpdate(BaseModel):
    status: Optional[str] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    memory_gb: Optional[int] = None
    disk_gb: Optional[int] = None
    tags: Optional[dict] = None


class ServerOut(BaseModel):
    id: int
    hostname: str
    idc_room_id: Optional[int]
    asset_no: Optional[str]
    status: str
    os_type: str
    os_version: str
    cpu_cores: int
    memory_gb: int
    disk_gb: int
    ssh_port: int
    ssh_user: str
    tags: Optional[dict]

    model_config = {"from_attributes": True}


class IpCreate(BaseModel):
    ip: str
    server_id: Optional[int] = None
    ip_type: str = "private"
    description: str = ""


class IpOut(BaseModel):
    id: int
    ip: str
    server_id: Optional[int]
    ip_type: str
    is_used: bool
    description: str

    model_config = {"from_attributes": True}
