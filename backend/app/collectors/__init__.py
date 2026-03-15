"""Collector factory — returns the right collector for a source's poll_strategy."""
from app.collectors.api_collector import NewsApiCollector
from app.collectors.base import BaseCollector, RawArticle
from app.collectors.rss_collector import RssCollector

__all__ = ["BaseCollector", "RawArticle", "RssCollector", "NewsApiCollector", "get_collector"]


def get_collector(poll_strategy: str, source_id: int, config: dict) -> BaseCollector:
    collectors = {
        "rss": RssCollector,
        "api": NewsApiCollector,
    }
    cls = collectors.get(poll_strategy)
    if cls is None:
        raise ValueError(f"Unknown poll_strategy: {poll_strategy!r}")
    return cls(source_id=source_id, config=config)
