"""Email sender — free via Gmail SMTP (App Password) or any SMTP server.

Degrades gracefully: if SMTP isn't configured (or sending fails) it returns False
instead of raising, so password resets and alerts never break the app. In dev with
no SMTP set, callers surface the token/link directly instead.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import settings


def mail_configured() -> bool:
    return settings.mail_configured


def send_email(to: str, subject: str, body: str, html: str | None = None) -> bool:
    """Send a plain-text (optionally HTML) email. Returns True on success, else False."""
    if not settings.mail_configured or not to:
        return False
    msg = EmailMessage()
    msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.mail_from_addr}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception:  # noqa: BLE001 — never let email failure break a request
        return False
