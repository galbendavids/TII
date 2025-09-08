"""
Simple email sender for notifications.

Env vars used:
- SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
- EMAIL_FROM, EMAIL_TO (comma-separated allowed)

Sends plain-text emails; easy to swap to HTML if needed.
"""

import os
import smtplib
from email.message import EmailMessage


def send_email(subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    email_from = os.getenv("EMAIL_FROM")
    email_to_raw = os.getenv("EMAIL_TO")

    if not all([host, port, user, password, email_from, email_to_raw]):
        raise RuntimeError("Missing required SMTP/EMAIL_* environment variables")

    recipients = [addr.strip() for addr in email_to_raw.split(",") if addr.strip()]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


