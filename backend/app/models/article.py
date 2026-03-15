"""Article models — collected articles and derived data."""
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey,
    Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ArticleCategory(str, enum.Enum):
    model_llm = "model_llm"
    ai_agent = "ai_agent"
    infra_serving = "infra_serving"
    opensource_framework = "opensource_framework"
    product_launch = "product_launch"
    research_paper = "research_paper"
    security_policy = "security_policy"
    dev_tools = "dev_tools"
    other = "other"


class Article(Base):
    """Normalized article metadata."""
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("canonical_url", name="uq_article_canonical_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)

    # Core fields
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Classification
    category: Mapped[ArticleCategory | None] = mapped_column(Enum(ArticleCategory), nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("articles.id"), nullable=True)

    # Collection state
    full_content_fetched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fetch_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="articles")  # noqa: F821
    content: Mapped["ArticleContent | None"] = relationship(
        "ArticleContent", back_populates="article", uselist=False
    )
    fingerprint: Mapped["ArticleFingerprint | None"] = relationship(
        "ArticleFingerprint", back_populates="article", uselist=False
    )
    score: Mapped["ArticleScore | None"] = relationship(
        "ArticleScore", back_populates="article", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Article id={self.id} title={self.title[:50]!r}>"


class ArticleContent(Base):
    """Raw and cleaned article body text."""
    __tablename__ = "article_contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    cleaned_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)  # from RSS/meta
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    article: Mapped["Article"] = relationship("Article", back_populates="content")


class ArticleFingerprint(Base):
    """Deduplication fingerprint (SimHash of title+body)."""
    __tablename__ = "article_fingerprints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    title_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_simhash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    article: Mapped["Article"] = relationship("Article", back_populates="fingerprint")


class ArticleScore(Base):
    """Developer relevance scoring per article."""
    __tablename__ = "article_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    importance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    novelty_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    developer_relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    composite_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    score_details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    article: Mapped["Article"] = relationship("Article", back_populates="score")
