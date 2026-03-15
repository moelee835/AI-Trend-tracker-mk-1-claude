"""RSS feed collector."""
import logging
from datetime import datetime, timezone

import feedparser
import httpx

from app.collectors.base import BaseCollector, RawArticle

logger = logging.getLogger(__name__)


class RssCollector(BaseCollector):
    """Collects articles from RSS/Atom feeds."""

    async def collect(self) -> list[RawArticle]:
        feed_url: str = self.config.get("feed_url", "")
        if not feed_url:
            logger.warning("source_id=%s has no feed_url configured", self.source_id)
            return []

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(feed_url, headers={"User-Agent": "AINewsletterBot/1.0"})
                resp.raise_for_status()
                feed_text = resp.text
        except Exception as exc:
            logger.error("RSS fetch failed source_id=%s url=%s: %s", self.source_id, feed_url, exc)
            raise

        feed = feedparser.parse(feed_text)
        articles: list[RawArticle] = []

        for entry in feed.entries:
            url = entry.get("link", "")
            if not url:
                continue

            published_at = self._parse_date(entry)
            title = entry.get("title", "").strip()
            if not title:
                continue

            summary = entry.get("summary", "") or entry.get("description", "")
            summary = self._clean_html(summary)

            articles.append(
                RawArticle(
                    title=title,
                    url=self._normalize_url(url),
                    source_id=self.source_id,
                    published_at=published_at,
                    author=entry.get("author"),
                    summary=summary[:2000] if summary else None,
                    tags=[t.get("term", "") for t in entry.get("tags", []) if t.get("term")],
                )
            )

        logger.info("RSS collected %d articles from source_id=%s", len(articles), self.source_id)
        return articles

    def _parse_date(self, entry: dict) -> datetime | None:
        import time
        for field in ("published_parsed", "updated_parsed"):
            t = entry.get(field)
            if t:
                try:
                    return datetime(*t[:6], tzinfo=timezone.utc)
                except Exception:
                    pass
        return None

    def _clean_html(self, text: str) -> str:
        from bs4 import BeautifulSoup
        return BeautifulSoup(text, "lxml").get_text(separator=" ", strip=True)
