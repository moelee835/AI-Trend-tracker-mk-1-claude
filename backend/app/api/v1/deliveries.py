"""Email delivery endpoints — send, test-send, resend."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.report import EmailDelivery
from app.services.email_service import send_report

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


class SendRequest(BaseModel):
    report_id: int
    version_id: Optional[int] = None
    recipient_ids: Optional[list[int]] = None  # None = all subscribed


class TestSendRequest(BaseModel):
    report_id: int
    version_id: Optional[int] = None
    test_email: EmailStr


class DeliveryOut(BaseModel):
    id: int
    report_id: int
    recipient_id: int
    status: str
    sent_at: Optional[datetime]
    error_message: Optional[str]
    is_test: bool
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/send", summary="Send report to all active recipients")
async def send(payload: SendRequest, db: AsyncSession = Depends(get_db)):
    result = await send_report(
        db=db,
        report_id=payload.report_id,
        version_id=payload.version_id,
        recipient_ids=payload.recipient_ids,
        is_test=False,
    )
    return result


@router.post("/test-send", summary="Send test email to a single address")
async def test_send(payload: TestSendRequest, db: AsyncSession = Depends(get_db)):
    from app.models.recipient import Recipient
    from sqlalchemy import select

    # Find or temporarily create recipient record for the test
    result = await db.execute(select(Recipient).where(Recipient.email == payload.test_email))
    recipient = result.scalar_one_or_none()
    if not recipient:
        recipient = Recipient(email=payload.test_email, subscribed=True, tags=["test"])
        db.add(recipient)
        await db.flush()

    res = await send_report(
        db=db,
        report_id=payload.report_id,
        version_id=payload.version_id,
        recipient_ids=[recipient.id],
        is_test=True,
    )
    return res


@router.get("/", response_model=list[DeliveryOut])
async def list_deliveries(
    report_id: Optional[int] = None,
    recipient_id: Optional[int] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    query = select(EmailDelivery).order_by(EmailDelivery.created_at.desc()).limit(limit)
    if report_id:
        query = query.where(EmailDelivery.report_id == report_id)
    if recipient_id:
        query = query.where(EmailDelivery.recipient_id == recipient_id)
    result = await db.execute(query)
    return result.scalars().all()
