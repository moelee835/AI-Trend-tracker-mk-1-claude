"""Orchestrates article collection for all enabled sources."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.deduplicator import is_duplicate_title, title_simhash, url_fingerprint
from app.analyzers.scorer import score_article
from app.collectors import get_collector
from app.models.article import Article, ArticleContent, ArticleFingerprint, ArticleScore
from app.models.source import Source

logger = logging.getLogger(__name__)


async def run_collection(db: AsyncSession, source_ids: list[int] | None = None) -> dict:
    """
    Collect articles from all enabled sources (or a subset).
    Returns summary stats.
    """
    query = select(Source).where(Source.enabled == True)  # noqa: E712
    if source_ids:
        query = query.where(Source.id.in_(source_ids))
    result = await db.execute(query)
    sources = result.scalars().all()

    total_new = 0
    total_dupes = 0
    errors: list[str] = []

    # Load existing fingerprints for dedup
    fp_result = await db.execute(select(ArticleFingerprint.title_hash))
    existing_hashes = [row[0] for row in fp_result.fetchall()]

    url_result = await db.execute(select(Article.canonical_url))
    existing_urls = {row[0] for row in url_result.fetchall()}

    for source in sources:
        try:
            collector = get_collector(
                poll_strategy=source.poll_strategy.value,
                source_id=source.id,
                config={**source.parser_config, "feed_url": source.feed_url},
            )
            raw_articles = await collector.collect()
        except Exception as exc:
            err_msg = f"Source {source.id} ({source.name}): {exc}"
            logger.error(err_msg)
            errors.append(err_msg)
            source.failure_count += 1
            source.last_error = str(exc)
            await db.flush()
            continue

        new_count = 0
        for raw in raw_articles:
            canonical = raw.url
            if canonical in existing_urls:
                total_dupes += 1
                continue

            t_hash = title_simhash(raw.title)
            if is_duplicate_title(t_hash, existing_hashes):
                total_dupes += 1
                continue

            # Score article
            scores = score_article(raw.title, raw.cleaned_text or raw.summary)

            # Persist article
            article = Article(
                source_id=source.id,
                title=raw.title,
                canonical_url=canonical,
                author=raw.author,
                published_at=raw.published_at,
                tags=raw.tags,
                category=scores.get("category"),
                full_content_fetched=bool(raw.cleaned_text),
            )
            db.add(article)
            await db.flush()  # get article.id

            db.add(ArticleContent(
                article_id=article.id,
                cleaned_text=raw.cleaned_text,
                summary_excerpt=raw.summary,
            ))

            db.add(ArticleFingerprint(
                article_id=article.id,
                title_hash=t_hash,
            ))

            db.add(ArticleScore(
                article_id=article.id,
                importance_score=scores["importance_score"],
                novelty_score=scores["novelty_score"],
                developer_relevance_score=scores["developer_relevance_score"],
                composite_score=scores["composite_score"],
                score_details=scores.get("details", {}),
            ))

            existing_urls.add(canonical)
            existing_hashes.append(t_hash)
            new_count += 1

        total_new += new_count
        source.last_collected_at = datetime.now(timezone.utc)
        source.failure_count = 0
        source.last_error = None
        logger.info("Source %s (%s): +%d new articles", source.id, source.name, new_count)

    await db.commit()
    return {"new_articles": total_new, "duplicates_skipped": total_dupes, "errors": errors}
