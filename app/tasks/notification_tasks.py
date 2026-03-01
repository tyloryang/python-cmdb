import smtplib
import httpx
from email.mime.text import MIMEText
from app.core.celery_app import celery_app
from app.config import settings


@celery_app.task(name="app.tasks.notification_tasks.send_notification")
def send_notification(channel_id: int, title: str, content: str):
    """根据渠道配置发送通知（钉钉 / 邮件 / Webhook）"""
    from app.db.session import AsyncSessionLocal
    from app.models.notification import NotificationChannel
    import asyncio
    from sqlalchemy import select

    async def _get_channel():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(NotificationChannel).where(NotificationChannel.id == channel_id))
            return result.scalar_one_or_none()

    channel = asyncio.get_event_loop().run_until_complete(_get_channel())
    if not channel or not channel.is_active:
        return

    cfg = channel.config
    if channel.channel_type == "dingtalk":
        _send_dingtalk(cfg.get("webhook", ""), title, content)
    elif channel.channel_type == "email":
        _send_email(cfg, title, content)
    elif channel.channel_type == "webhook":
        _send_webhook(cfg.get("url", ""), title, content)


def _send_dingtalk(webhook: str, title: str, content: str):
    if not webhook:
        return
    payload = {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": f"### {title}\n{content}"},
    }
    with httpx.Client(timeout=10) as client:
        client.post(webhook, json=payload)


def _send_email(cfg: dict, title: str, content: str):
    host = cfg.get("smtp_host") or settings.SMTP_HOST
    port = cfg.get("smtp_port") or settings.SMTP_PORT
    user = cfg.get("smtp_user") or settings.SMTP_USER
    password = cfg.get("smtp_password") or settings.SMTP_PASSWORD
    recipients = cfg.get("to", [])
    if not host or not recipients:
        return
    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = title
    msg["From"] = user
    msg["To"] = ", ".join(recipients)
    with smtplib.SMTP_SSL(host, port) as smtp:
        smtp.login(user, password)
        smtp.sendmail(user, recipients, msg.as_string())


def _send_webhook(url: str, title: str, content: str):
    if not url:
        return
    with httpx.Client(timeout=10) as client:
        client.post(url, json={"title": title, "content": content})
