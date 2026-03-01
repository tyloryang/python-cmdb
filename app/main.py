import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router as v1_router
from app.core.audit import AuditMiddleware
from app.db.session import engine
from app.db.base import Base

# 导入所有模型，确保 Alembic 能扫描到
import app.models.user      # noqa
import app.models.cmdb      # noqa
import app.models.pipeline  # noqa
import app.models.release   # noqa
import app.models.monitor   # noqa
import app.models.audit     # noqa
import app.models.notification  # noqa
import app.models.log_analysis  # noqa


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动建表（开发模式）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="DevOps 管理平台",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

app.include_router(v1_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
