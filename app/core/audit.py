import time
from datetime import datetime, timezone
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.db.session import AsyncSessionLocal
from app.models.audit import AuditLog


class AuditMiddleware(BaseHTTPMiddleware):
    """记录写操作（POST/PUT/PATCH/DELETE）的审计日志"""

    SKIP_METHODS = {"GET", "HEAD", "OPTIONS"}
    SKIP_PATHS = {"/api/v1/auth/login"}  # 登录单独处理

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in self.SKIP_METHODS or request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        response = await call_next(request)

        # 异步写入审计日志，不阻塞响应
        user = getattr(request.state, "current_user", None)
        log = AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else "",
            action=request.method,
            resource=request.url.path,
            client_ip=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", "")[:256],
            status_code=response.status_code,
            created_at=datetime.now(timezone.utc),
        )
        async with AsyncSessionLocal() as session:
            session.add(log)
            await session.commit()

        return response
