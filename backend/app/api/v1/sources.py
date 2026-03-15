"""Source management endpoints."""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.source import PollStrategy, Source, SourceType

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceCreate(BaseModel):
    name: str
    source_type: SourceType
    base_url: str
    feed_url: str | None = None
    enabled: bool = True
    poll_strategy: PollStrategy
    parser_config: dict = {}


class SourceUpdate(BaseModel):
    name: str | None = None
    feed_url: str | None = None
    enabled: bool | None = None
    poll_strategy: PollStrategy | None = None
    parser_config: dict | None = None


class SourceOut(BaseModel):
    id: int
    name: str
    source_type: str
    base_url: str
    feed_url: str | None
    enabled: bool
    poll_strategy: str
    parser_config: dict
    last_collected_at: datetime | None
    failure_count: int
    last_error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[SourceOut])
async def list_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).order_by(Source.name))
    return result.scalars().all()


@router.post("/", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
async def create_source(payload: SourceCreate, db: AsyncSession = Depends(get_db)):
    source = Source(**payload.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.get("/{source_id}", response_model=SourceOut)
async def get_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.patch("/{source_id}", response_model=SourceOut)
async def update_source(source_id: int, payload: SourceUpdate, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(source, field, value)
    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    await db.delete(source)
    await db.commit()


@router.post("/{source_id}/toggle", response_model=SourceOut)
async def toggle_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    source.enabled = not source.enabled
    await db.commit()
    await db.refresh(source)
    return source
