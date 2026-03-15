"""Article listing and detail endpoints."""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.article import Article, ArticleCategory, ArticleContent, ArticleScore

router = APIRouter(prefix="/articles", tags=["articles"])


class ArticleOut(BaseModel):
    id: int
    source_id: int
    title: str
    canonical_url: str
    author: Optional[str]
    published_at: Optional[datetime]
    category: Optional[str]
    is_duplicate: bool
    collected_at: datetime
    composite_score: Optional[float] = None
    summary_excerpt: Optional[str] = None

    model_config = {"from_attributes": True}


class ArticleDetailOut(ArticleOut):
    tags: list[str]
    full_content_fetched: bool
    cleaned_text: Optional[str] = None


@router.get("/", response_model=list[ArticleOut])
async def list_articles(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    category: Optional[ArticleCategory] = None,
    min_score: Optional[float] = None,
    is_duplicate: Optional[bool] = None,
    source_id: Optional[int] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Article, ArticleScore, ArticleContent)
        .join(ArticleScore, Article.id == ArticleScore.article_id, isouter=True)
        .join(ArticleContent, Article.id == ArticleContent.article_id, isouter=True)
        .order_by(desc(ArticleScore.composite_score))
    )

    if date_from:
        query = query.where(Article.collected_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.where(Article.collected_at <= datetime.combine(date_to, datetime.max.time()))
    if category:
        query = query.where(Article.category == category)
    if min_score is not None:
        query = query.where(ArticleScore.composite_score >= min_score)
    if is_duplicate is not None:
        query = query.where(Article.is_duplicate == is_duplicate)
    if source_id:
        query = query.where(Article.source_id == source_id)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)

    out = []
    for article, score, content in result.fetchall():
        row = ArticleOut(
            id=article.id,
            source_id=article.source_id,
            title=article.title,
            canonical_url=article.canonical_url,
            author=article.author,
            published_at=article.published_at,
            category=article.category.value if article.category else None,
            is_duplicate=article.is_duplicate,
            collected_at=article.collected_at,
            composite_score=score.composite_score if score else None,
            summary_excerpt=content.summary_excerpt if content else None,
        )
        out.append(row)
    return out


@router.get("/{article_id}", response_model=ArticleDetailOut)
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Article, ArticleScore, ArticleContent)
        .join(ArticleScore, Article.id == ArticleScore.article_id, isouter=True)
        .join(ArticleContent, Article.id == ArticleContent.article_id, isouter=True)
        .where(Article.id == article_id)
    )
    row = result.first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Article not found")

    article, score, content = row
    return ArticleDetailOut(
        id=article.id,
        source_id=article.source_id,
        title=article.title,
        canonical_url=article.canonical_url,
        author=article.author,
        published_at=article.published_at,
        tags=article.tags or [],
        category=article.category.value if article.category else None,
        is_duplicate=article.is_duplicate,
        full_content_fetched=article.full_content_fetched,
        collected_at=article.collected_at,
        composite_score=score.composite_score if score else None,
        summary_excerpt=content.summary_excerpt if content else None,
        cleaned_text=content.cleaned_text if content else None,
    )
