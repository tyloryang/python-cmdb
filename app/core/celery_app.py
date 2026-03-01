from celery import Celery
from app.config import settings

celery_app = Celery(
    "devops",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.pipeline_tasks",
        "app.tasks.monitor_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.release_tasks",
        "app.tasks.log_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    beat_schedule={
        "collect-metrics-every-60s": {
            "task": "app.tasks.monitor_tasks.collect_metrics",
            "schedule": 60.0,
        },
        "scan-log-watchers-every-30s": {
            "task": "app.tasks.log_tasks.scan_log_watchers",
            "schedule": 30.0,
        },
    },
)
