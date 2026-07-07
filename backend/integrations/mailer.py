"""Email delivery. Every message is logged to the `emails` collection (the
Outbox in the UI). In dry-run mode (default) nothing leaves the building —
flip EMAIL_DRY_RUN=false with SMTP credentials set to send for real."""
import smtplib
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

import config
from database import db


def smtp_configured() -> bool:
    return bool(config.SMTP_HOST and config.SMTP_USER and config.SMTP_PASSWORD)


def send_email(to_email: str, subject: str, html_body: str,
               attachment_paths: list | None = None,
               agent_key: str | None = None, run_id: str | None = None,
               patient_id: str | None = None) -> dict:
    attachment_paths = attachment_paths or []
    email_id = str(uuid.uuid4())
    record = {
        "id": email_id,
        "to": to_email,
        "subject": subject,
        "html_body": html_body,
        "attachments": [Path(p).name for p in attachment_paths],
        "agent_key": agent_key,
        "run_id": run_id,
        "patient_id": patient_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if config.EMAIL_DRY_RUN or not smtp_configured():
        record["status"] = "dry_run"
        record["detail"] = ("Captured in Outbox — dry-run mode. Configure SMTP and set "
                            "EMAIL_DRY_RUN=false to deliver for real.")
        db.emails.insert_one(record)
        record.pop("_id", None)
        return {"status": "dry_run", "email_id": email_id, "to": to_email,
                "note": record["detail"]}

    msg = EmailMessage()
    msg["From"] = config.SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content("This email requires an HTML-capable client.")
    msg.add_alternative(html_body, subtype="html")
    for p in attachment_paths:
        path = Path(p)
        msg.add_attachment(path.read_bytes(), maintype="application",
                           subtype="pdf", filename=path.name)

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
        record["status"] = "sent"
        db.emails.insert_one(record)
        return {"status": "sent", "email_id": email_id, "to": to_email}
    except Exception as exc:
        record["status"] = "failed"
        record["detail"] = str(exc)
        db.emails.insert_one(record)
        return {"status": "failed", "email_id": email_id, "to": to_email, "error": str(exc)}
