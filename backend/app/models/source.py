"""Source model — defines where articles are collected from."""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class SourceType(str, enum.Enum):
    vendor_blog = "vendor_blog"
    research = "research"
    opensource = "opensource"
    news_api = "news_api"
    rss = "rss"
    html_scrape = "html_scrape"


class PollStrategy(str, enum.Enum):
    rss = "rss"
    api = "api"
    html = "html"
    playwright = "playwright"


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    feed_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    poll_strategy: Mapped[PollStrategy] = mapped_column(Enum(PollStrategy), nullable=False)
    # Flexible config: headers, selectors, auth, etc.
    parser_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # Stats
    last_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    articles: Mapped[list["Article"]] = relationship("Article", back_populates="source")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Source id={self.id} name={self.name!r} enabled={self.enabled}>"
