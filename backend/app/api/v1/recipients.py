"""Recipient (subscriber) management endpoints."""
import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.recipient import Recipient

router = APIRouter(prefix="/recipients", tags=["recipients"])


class RecipientCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    subscribed: bool = True
    tags: list[str] = []


class RecipientUpdate(BaseModel):
    name: Optional[str] = None
    subscribed: Optional[bool] = None
    tags: Optional[list[str]] = None


class RecipientOut(BaseModel):
    id: int
    email: str
    name: Optional[str]
    subscribed: bool
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[RecipientOut])
async def list_recipients(
    subscribed: Optional[bool] = None,
    tag: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Recipient).order_by(Recipient.created_at.desc())
    if subscribed is not None:
        query = query.where(Recipient.subscribed == subscribed)
    result = await db.execute(query)
    recipients = result.scalars().all()
    if tag:
        recipients = [r for r in recipients if tag in (r.tags or [])]
    return recipients


@router.post("/", response_model=RecipientOut, status_code=status.HTTP_201_CREATED)
async def create_recipient(payload: RecipientCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Recipient).where(Recipient.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    r = Recipient(**payload.model_dump())
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


@router.get("/{recipient_id}", response_model=RecipientOut)
async def get_recipient(recipient_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.get(Recipient, recipient_id)
    if not r:
        raise HTTPException(status_code=404, detail="Recipient not found")
    return r


@router.patch("/{recipient_id}", response_model=RecipientOut)
async def update_recipient(
    recipient_id: int, payload: RecipientUpdate, db: AsyncSession = Depends(get_db)
):
    r = await db.get(Recipient, recipient_id)
    if not r:
        raise HTTPException(status_code=404, detail="Recipient not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(r, field, value)
    await db.commit()
    await db.refresh(r)
    return r


@router.delete("/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipient(recipient_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.get(Recipient, recipient_id)
    if not r:
        raise HTTPException(status_code=404, detail="Recipient not found")
    await db.delete(r)
    await db.commit()


@router.post("/import/csv", status_code=status.HTTP_201_CREATED)
async def import_csv(file: UploadFile, db: AsyncSession = Depends(get_db)):
    """
    CSV format: email,name,tags
    tags column is comma-separated inside the field, e.g. "internal;vip"
    """
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    created, skipped = 0, 0

    for row in reader:
        email = (row.get("email") or "").strip().lower()
        if not email:
            continue
        existing = await db.execute(select(Recipient).where(Recipient.email == email))
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        tags_raw = row.get("tags", "")
        tags = [t.strip() for t in tags_raw.split(";") if t.strip()]
        r = Recipient(
            email=email,
            name=(row.get("name") or "").strip() or None,
            tags=tags,
        )
        db.add(r)
        created += 1

    await db.commit()
    return {"created": created, "skipped": skipped}
