"""News API-based collector (NewsAPI.org, GNews, etc.)."""
import logging
from datetime import datetime, timezone

import httpx

from app.collectors.base import BaseCollector, RawArticle
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class NewsApiCollector(BaseCollector):
    """Collects articles from NewsAPI.org."""

    BASE_URL = "https://newsapi.org/v2/everything"

    async def collect(self) -> list[RawArticle]:
        api_key = settings.NEWS_API_KEY
        if not api_key:
            logger.warning("NEWS_API_KEY not configured, skipping NewsAPI collector")
            return []

        keywords = self.config.get("keywords", "artificial intelligence OR LLM OR machine learning")
        language = self.config.get("language", "en")
        page_size = self.config.get("page_size", 50)

        params = {
            "q": keywords,
            "language": language,
            "pageSize": page_size,
            "sortBy": "publishedAt",
            "apiKey": api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.error("NewsAPI fetch failed source_id=%s: %s", self.source_id, exc)
            raise

        articles: list[RawArticle] = []
        for item in data.get("articles", []):
            url = item.get("url", "")
            title = (item.get("title") or "").strip()
            if not url or not title or title == "[Removed]":
                continue

            published_at = None
            if pa := item.get("publishedAt"):
                try:
                    published_at = datetime.fromisoformat(pa.replace("Z", "+00:00"))
                except Exception:
                    pass

            articles.append(
                RawArticle(
                    title=title,
                    url=self._normalize_url(url),
                    source_id=self.source_id,
                    published_at=published_at,
                    author=item.get("author"),
                    summary=item.get("description"),
                )
            )

        logger.info("NewsAPI collected %d articles source_id=%s", len(articles), self.source_id)
        return articles
