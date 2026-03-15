"""Abstract base class for all article collectors."""
import abc
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawArticle:
    """Intermediate DTO produced by collectors before DB persistence."""
    title: str
    url: str
    source_id: int
    published_at: datetime | None = None
    author: str | None = None
    summary: str | None = None
    raw_html: str | None = None
    cleaned_text: str | None = None
    tags: list[str] = field(default_factory=list)


class BaseCollector(abc.ABC):
    """All collectors implement this interface."""

    def __init__(self, source_id: int, config: dict) -> None:
        self.source_id = source_id
        self.config = config

    @abc.abstractmethod
    async def collect(self) -> list[RawArticle]:
        """Fetch and return raw articles from the source."""

    def _normalize_url(self, url: str) -> str:
        """Strip tracking params and normalize to canonical form."""
        from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
        parsed = urlparse(url)
        # Remove common tracking query params
        skip = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "ref"}
        qs = {k: v for k, v in parse_qs(parsed.query).items() if k not in skip}
        clean = parsed._replace(query=urlencode(qs, doseq=True), fragment="")
        return urlunparse(clean)
