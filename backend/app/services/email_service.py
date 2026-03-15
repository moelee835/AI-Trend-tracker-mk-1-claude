"""Email sending via SMTP (aiosmtplib)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.recipient import Recipient
from app.models.report import DailyReport, DeliveryStatus, EmailDelivery, ReportStatus, ReportVersion

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_report(
    db: AsyncSession,
    report_id: int,
    version_id: int | None = None,
    recipient_ids: list[int] | None = None,
    is_test: bool = False,
) -> dict:
    """Send a report version to all active recipients (or a subset)."""
    # Load report
    report_result = await db.execute(select(DailyReport).where(DailyReport.id == report_id))
    report = report_result.scalar_one_or_none()
    if not report:
        raise ValueError(f"Report {report_id} not found")

    # Load version
    if version_id:
        ver_result = await db.execute(select(ReportVersion).where(ReportVersion.id == version_id))
    else:
        ver_result = await db.execute(
            select(ReportVersion)
            .where(ReportVersion.report_id == report_id, ReportVersion.is_active == True)  # noqa: E712
        )
    version = ver_result.scalar_one_or_none()
    if not version:
        raise ValueError(f"No active version found for report {report_id}")

    # Load recipients
    rcpt_query = select(Recipient).where(Recipient.subscribed == True)  # noqa: E712
    if recipient_ids:
        rcpt_query = rcpt_query.where(Recipient.id.in_(recipient_ids))
    rcpt_result = await db.execute(rcpt_query)
    recipients = rcpt_result.scalars().all()

    sent_count = 0
    failed_count = 0

    for recipient in recipients:
        delivery = EmailDelivery(
            report_id=report_id,
            version_id=version.id,
            recipient_id=recipient.id,
            status=DeliveryStatus.pending,
            is_test=is_test,
        )
        db.add(delivery)
        await db.flush()

        try:
            await _send_single(
                to_email=recipient.email,
                to_name=recipient.name or recipient.email,
                subject=version.subject_line,
                html_body=version.html_content,
                plain_body=version.plain_content or "",
            )
            delivery.status = DeliveryStatus.sent
            delivery.sent_at = datetime.now(timezone.utc)
            sent_count += 1
        except Exception as exc:
            logger.error("Email send failed to %s: %s", recipient.email, exc)
            delivery.status = DeliveryStatus.failed
            delivery.error_message = str(exc)
            failed_count += 1

    if not is_test and sent_count > 0:
        report.status = ReportStatus.sent

    await db.commit()
    return {"sent": sent_count, "failed": failed_count, "total": len(recipients)}


async def _send_single(
    to_email: str,
    to_name: str,
    subject: str,
    html_body: str,
    plain_body: str,
) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = f"{to_name} <{to_email}>"

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    await aiosmtplib.send(
        msg,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=True,
    )
