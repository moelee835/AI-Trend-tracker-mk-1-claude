"""Tests for email service with mocked SMTP."""
from __future__ import annotations

import pytest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

from app.models.source import Source, SourceType, PollStrategy
from app.models.recipient import Recipient
from app.models.report import DailyReport, ReportStatus, ReportVersion, EmailDelivery, DeliveryStatus
from app.services.email_service import send_report


@pytest.fixture
async def report_with_version(db):
    r = DailyReport(
        report_date=date(2026, 3, 17),
        status=ReportStatus.approved,
        included_article_ids=[],
        keyword_summary={},
    )
    db.add(r)
    await db.flush()
    v = ReportVersion(
        report_id=r.id,
        version_number=1,
        is_active=True,
        subject_line="AI Trend | 2026-03-17",
        html_content="<html><body>Newsletter</body></html>",
        plain_content="Newsletter text",
        llm_model="gpt-4o",
        generation_tokens=500,
        edited_by_operator=False,
    )
    db.add(v)
    await db.commit()
    await db.refresh(r)
    return r, v


@pytest.fixture
async def subscribed_recipient(db):
    r = Recipient(email="sub@example.com", name="Subscriber", subscribed=True, tags=[])
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


@pytest.fixture
async def unsubscribed_recipient(db):
    r = Recipient(email="unsub@example.com", name="Unsubscribed", subscribed=False, tags=[])
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


class TestSendReport:
    async def test_send_to_subscribed_recipients(self, db, report_with_version, subscribed_recipient):
        report, version = report_with_version

        with patch("app.services.email_service._send_single", new_callable=AsyncMock) as mock_send:
            result = await send_report(db=db, report_id=report.id, is_test=False)

        assert result["sent"] == 1
        assert result["failed"] == 0
        assert result["total"] == 1
        mock_send.assert_called_once()

    async def test_skip_unsubscribed_recipients(self, db, report_with_version, unsubscribed_recipient):
        report, _ = report_with_version

        with patch("app.services.email_service._send_single", new_callable=AsyncMock) as mock_send:
            result = await send_report(db=db, report_id=report.id, is_test=False)

        assert result["sent"] == 0
        assert result["total"] == 0
        mock_send.assert_not_called()

    async def test_send_to_specific_recipient_ids(self, db, report_with_version, subscribed_recipient):
        report, _ = report_with_version

        with patch("app.services.email_service._send_single", new_callable=AsyncMock) as mock_send:
            result = await send_report(
                db=db,
                report_id=report.id,
                recipient_ids=[subscribed_recipient.id],
                is_test=True,
            )

        assert result["sent"] == 1
        mock_send.assert_called_once()

    async def test_smtp_failure_marks_delivery_failed(self, db, report_with_version, subscribed_recipient):
        report, _ = report_with_version

        with patch("app.services.email_service._send_single", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("SMTP connection refused")
            result = await send_report(db=db, report_id=report.id, is_test=False)

        assert result["sent"] == 0
        assert result["failed"] == 1

        # Verify delivery record shows failed status
        from sqlalchemy import select
        deliveries = await db.execute(select(EmailDelivery))
        delivery = deliveries.scalar_one()
        assert delivery.status == DeliveryStatus.failed
        assert "SMTP connection refused" in delivery.error_message

    async def test_report_status_set_to_sent_after_success(self, db, report_with_version, subscribed_recipient):
        report, _ = report_with_version

        with patch("app.services.email_service._send_single", new_callable=AsyncMock):
            await send_report(db=db, report_id=report.id, is_test=False)

        await db.refresh(report)
        assert report.status == ReportStatus.sent

    async def test_test_send_does_not_change_report_status(self, db, report_with_version, subscribed_recipient):
        report, _ = report_with_version

        with patch("app.services.email_service._send_single", new_callable=AsyncMock):
            await send_report(db=db, report_id=report.id, is_test=True)

        await db.refresh(report)
        # Test send should not change status to sent
        assert report.status == ReportStatus.approved

    async def test_report_not_found_raises_value_error(self, db):
        with pytest.raises(ValueError, match="Report 9999 not found"):
            await send_report(db=db, report_id=9999)

    async def test_no_active_version_raises_value_error(self, db):
        r = DailyReport(
            report_date=date(2026, 3, 17),
            status=ReportStatus.draft,
            included_article_ids=[],
            keyword_summary={},
        )
        db.add(r)
        await db.commit()

        with pytest.raises(ValueError, match="No active version"):
            await send_report(db=db, report_id=r.id)

    async def test_send_with_explicit_version_id(self, db, report_with_version, subscribed_recipient):
        report, version = report_with_version

        with patch("app.services.email_service._send_single", new_callable=AsyncMock) as mock_send:
            result = await send_report(
                db=db,
                report_id=report.id,
                version_id=version.id,
                is_test=False,
            )

        assert result["sent"] == 1
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["subject"] == "AI Trend | 2026-03-17"

    async def test_no_recipients_returns_zero_counts(self, db, report_with_version):
        report, _ = report_with_version

        with patch("app.services.email_service._send_single", new_callable=AsyncMock) as mock_send:
            result = await send_report(db=db, report_id=report.id, is_test=False)

        assert result["sent"] == 0
        assert result["total"] == 0
        mock_send.assert_not_called()


class TestSendSingle:
    async def test_send_single_calls_aiosmtplib(self):
        from app.services.email_service import _send_single

        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_smtp:
            await _send_single(
                to_email="user@example.com",
                to_name="User Name",
                subject="Test Subject",
                html_body="<html>body</html>",
                plain_body="plain body",
            )

        mock_smtp.assert_called_once()
        call_kwargs = mock_smtp.call_args
        # aiosmtplib.send called with message and SMTP params
        assert call_kwargs is not None
