"""Seed default AI news sources."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal, engine, Base
from app.models.source import Source, SourceType, PollStrategy

DEFAULT_SOURCES = [
    # --- Vendor Blogs (RSS) ---
    {
        "name": "OpenAI Blog",
        "source_type": SourceType.vendor_blog,
        "base_url": "https://openai.com",
        "feed_url": "https://openai.com/blog/rss.xml",
        "poll_strategy": PollStrategy.rss,
        "parser_config": {},
    },
    {
        "name": "Anthropic News",
        "source_type": SourceType.vendor_blog,
        "base_url": "https://www.anthropic.com",
        "feed_url": "https://www.anthropic.com/rss.xml",
        "poll_strategy": PollStrategy.rss,
        "parser_config": {},
    },
    {
        "name": "Google DeepMind Blog",
        "source_type": SourceType.vendor_blog,
        "base_url": "https://deepmind.google",
        "feed_url": "https://deepmind.google/blog/rss.xml",
        "poll_strategy": PollStrategy.rss,
        "parser_config": {},
    },
    {
        "name": "Hugging Face Blog",
        "source_type": SourceType.vendor_blog,
        "base_url": "https://huggingface.co",
        "feed_url": "https://huggingface.co/blog/feed.xml",
        "poll_strategy": PollStrategy.rss,
        "parser_config": {},
    },
    {
        "name": "Meta AI Blog",
        "source_type": SourceType.vendor_blog,
        "base_url": "https://ai.meta.com",
        "feed_url": "https://ai.meta.com/blog/feed/",
        "poll_strategy": PollStrategy.rss,
        "parser_config": {},
    },
    {
        "name": "Microsoft AI Blog",
        "source_type": SourceType.vendor_blog,
        "base_url": "https://blogs.microsoft.com/ai",
        "feed_url": "https://blogs.microsoft.com/ai/feed/",
        "poll_strategy": PollStrategy.rss,
        "parser_config": {},
    },
    {
        "name": "AWS Machine Learning Blog",
        "source_type": SourceType.vendor_blog,
        "base_url": "https://aws.amazon.com/blogs/machine-learning",
        "feed_url": "https://aws.amazon.com/blogs/machine-learning/feed/",
        "poll_strategy": PollStrategy.rss,
        "parser_config": {},
    },
    # --- Research ---
    {
        "name": "arXiv cs.AI",
        "source_type": SourceType.research,
        "base_url": "https://arxiv.org",
        "feed_url": "https://export.arxiv.org/rss/cs.AI",
        "poll_strategy": PollStrategy.rss,
        "parser_config": {"max_items": 30},
    },
    {
        "name": "arXiv cs.LG",
        "source_type": SourceType.research,
        "base_url": "https://arxiv.org",
        "feed_url": "https://export.arxiv.org/rss/cs.LG",
        "poll_strategy": PollStrategy.rss,
        "parser_config": {"max_items": 30},
    },
    {
        "name": "arXiv cs.CL",
        "source_type": SourceType.research,
        "base_url": "https://arxiv.org",
        "feed_url": "https://export.arxiv.org/rss/cs.CL",
        "poll_strategy": PollStrategy.rss,
        "parser_config": {"max_items": 30},
    },
    # --- General AI News (NewsAPI) ---
    {
        "name": "NewsAPI - AI Headlines",
        "source_type": SourceType.news_api,
        "base_url": "https://newsapi.org",
        "feed_url": None,
        "poll_strategy": PollStrategy.api,
        "parser_config": {
            "keywords": "artificial intelligence OR large language model OR GPT OR Claude OR Gemini",
            "language": "en",
            "page_size": 50,
        },
    },
    # --- Open Source ---
    {
        "name": "LangChain Blog",
        "source_type": SourceType.opensource_framework,
        "base_url": "https://blog.langchain.dev",
        "feed_url": "https://blog.langchain.dev/rss/",
        "poll_strategy": PollStrategy.rss,
        "parser_config": {},
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        for src_data in DEFAULT_SOURCES:
            existing = await db.execute(
                select(Source).where(Source.name == src_data["name"])
            )
            if existing.scalar_one_or_none():
                print(f"  SKIP (exists): {src_data['name']}")
                continue
            source = Source(**src_data)
            db.add(source)
            print(f"  ADD: {src_data['name']}")
        await db.commit()
        print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
