from typing import Optional
from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, JSON, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class IdcRoom(Base, TimestampMixin):
    __tablename__ = "idc_rooms"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    location: Mapped[str] = mapped_column(String(256), default="")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    servers: Mapped[list["Server"]] = relationship(back_populates="idc_room")


class Server(Base, TimestampMixin):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    hostname: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    idc_room_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("idc_rooms.id", ondelete="SET NULL"), nullable=True
    )
    asset_no: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("running", "stopped", "maintenance", "decommissioned"),
        default="running", index=True
    )
    os_type: Mapped[str] = mapped_column(String(32), default="")
    os_version: Mapped[str] = mapped_column(String(64), default="")
    cpu_cores: Mapped[int] = mapped_column(SmallInteger, default=0)
    memory_gb: Mapped[int] = mapped_column(SmallInteger, default=0)
    disk_gb: Mapped[int] = mapped_column(Integer, default=0)
    ssh_port: Mapped[int] = mapped_column(SmallInteger, default=22)
    ssh_user: Mapped[str] = mapped_column(String(64), default="root")
    ssh_auth_type: Mapped[str] = mapped_column(Enum("password", "key"), default="key")
    ssh_credential: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    idc_room: Mapped[Optional[IdcRoom]] = relationship(back_populates="servers")
    ip_addresses: Mapped[list["IpAddress"]] = relationship(back_populates="server")
    config_items: Mapped[list["ConfigItem"]] = relationship(back_populates="server")


class IpAddress(Base, TimestampMixin):
    __tablename__ = "ip_addresses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ip: Mapped[str] = mapped_column(String(45), unique=True, nullable=False, index=True)
    server_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("servers.id", ondelete="SET NULL"), nullable=True
    )
    ip_type: Mapped[str] = mapped_column(Enum("public", "private", "virtual"), default="private")
    is_used: Mapped[bool] = mapped_column(default=False)
    description: Mapped[str] = mapped_column(String(256), default="")

    server: Mapped[Optional[Server]] = relationship(back_populates="ip_addresses")


class ConfigItem(Base, TimestampMixin):
    __tablename__ = "config_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    key_name: Mapped[str] = mapped_column(String(128), nullable=False)
    value_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    server: Mapped[Server] = relationship(back_populates="config_items")
