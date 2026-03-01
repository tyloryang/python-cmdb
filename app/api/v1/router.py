from fastapi import APIRouter
from app.api.v1 import auth, users, roles, audit, notification, terminal
from app.api.v1.cmdb import servers
from app.api.v1.cicd import pipelines
from app.api.v1.monitor import alerts
from app.api.v1.release import releases
from app.api.v1.log_analysis import watchers as log_watchers

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(roles.router)
router.include_router(servers.router)
router.include_router(audit.router)
router.include_router(pipelines.router)
router.include_router(alerts.router)
router.include_router(releases.router)
router.include_router(notification.router)
router.include_router(terminal.router)
router.include_router(log_watchers.router)
