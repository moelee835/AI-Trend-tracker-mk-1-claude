"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension (optional — comment out if not available)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # sources
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("vendor_blog", "research", "opensource", "news_api", "rss", "html_scrape", name="sourcetype"),
            nullable=False,
        ),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("feed_url", sa.String(500), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "poll_strategy",
            sa.Enum("rss", "api", "html", "playwright", name="pollstrategy"),
            nullable=False,
        ),
        sa.Column("parser_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("last_collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sources_id", "sources", ["id"])

    # articles
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("canonical_url", sa.String(1000), nullable=False),
        sa.Column("author", sa.String(200), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "category",
            sa.Enum(
                "model_llm", "ai_agent", "infra_serving", "opensource_framework",
                "product_launch", "research_paper", "security_policy", "dev_tools", "other",
                name="articlecategory",
            ),
            nullable=True,
        ),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("duplicate_of_id", sa.Integer(), sa.ForeignKey("articles.id"), nullable=True),
        sa.Column("full_content_fetched", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("fetch_error", sa.Text(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_url", name="uq_article_canonical_url"),
    )
    op.create_index("ix_articles_id", "articles", ["id"])
    op.create_index("ix_articles_source_id", "articles", ["source_id"])

    # article_contents
    op.create_table(
        "article_contents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("cleaned_text", sa.Text(), nullable=True),
        sa.Column("summary_excerpt", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id"),
    )
    op.create_index("ix_article_contents_article_id", "article_contents", ["article_id"])

    # article_fingerprints
    op.create_table(
        "article_fingerprints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title_hash", sa.String(64), nullable=False),
        sa.Column("content_simhash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id"),
    )
    op.create_index("ix_article_fingerprints_title_hash", "article_fingerprints", ["title_hash"])

    # article_scores
    op.create_table(
        "article_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("importance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("novelty_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("developer_relevance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("composite_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("score_details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("scored_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id"),
    )
    op.create_index("ix_article_scores_composite_score", "article_scores", ["composite_score"])

    # recipients
    op.create_table(
        "recipients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("subscribed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_recipients_email"),
    )
    op.create_index("ix_recipients_id", "recipients", ["id"])
    op.create_index("ix_recipients_email", "recipients", ["email"])

    # daily_reports
    op.create_table(
        "daily_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "ready", "approved", "sent", name="reportstatus"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("included_article_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("keyword_summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_daily_reports_id", "daily_reports", ["id"])
    op.create_index("ix_daily_reports_report_date", "daily_reports", ["report_date"])

    # report_versions
    op.create_table(
        "report_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("subject_line", sa.String(300), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("plain_content", sa.Text(), nullable=True),
        sa.Column("web_preview_content", sa.Text(), nullable=True),
        sa.Column("llm_model", sa.String(100), nullable=True),
        sa.Column("generation_prompt", sa.Text(), nullable=True),
        sa.Column("generation_tokens", sa.Integer(), nullable=True),
        sa.Column("edited_by_operator", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "version_number", name="uq_report_version"),
    )
    op.create_index("ix_report_versions_id", "report_versions", ["id"])
    op.create_index("ix_report_versions_report_id", "report_versions", ["report_id"])

    # report_sections
    op.create_table(
        "report_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version_id", sa.Integer(), sa.ForeignKey("report_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("section_type", sa.String(50), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("html_content", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_sections_version_id", "report_sections", ["version_id"])

    # email_deliveries
    op.create_table(
        "email_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("daily_reports.id"), nullable=False),
        sa.Column("version_id", sa.Integer(), sa.ForeignKey("report_versions.id"), nullable=False),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("recipients.id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "sent", "failed", "bounced", name="deliverystatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("is_test", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_deliveries_id", "email_deliveries", ["id"])
    op.create_index("ix_email_deliveries_report_id", "email_deliveries", ["report_id"])
    op.create_index("ix_email_deliveries_recipient_id", "email_deliveries", ["recipient_id"])

    # job_execution_logs
    op.create_table(
        "job_execution_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "job_type",
            sa.Enum("collect", "analyze", "generate_report", "send_email", "manual_resend", name="jobtype"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("running", "success", "failed", "partial", name="jobstatus"),
            nullable=False,
        ),
        sa.Column("celery_task_id", sa.String(200), nullable=True),
        sa.Column("triggered_by", sa.String(50), nullable=False, server_default="scheduler"),
        sa.Column("result_summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_execution_logs_id", "job_execution_logs", ["id"])
    op.create_index("ix_job_execution_logs_started_at", "job_execution_logs", ["started_at"])


def downgrade() -> None:
    op.drop_table("job_execution_logs")
    op.drop_table("email_deliveries")
    op.drop_table("report_sections")
    op.drop_table("report_versions")
    op.drop_table("daily_reports")
    op.drop_table("recipients")
    op.drop_table("article_scores")
    op.drop_table("article_fingerprints")
    op.drop_table("article_contents")
    op.drop_table("articles")
    op.drop_table("sources")
    # Drop enums
    for enum_name in [
        "sourcetype", "pollstrategy", "articlecategory",
        "reportstatus", "deliverystatus", "jobtype", "jobstatus",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
