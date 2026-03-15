"""Report and email delivery models."""
import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey,
    Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ReportStatus(str, enum.Enum):
    draft = "draft"
    ready = "ready"         # LLM generation done
    approved = "approved"   # operator confirmed
    sent = "sent"


class DeliveryStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    bounced = "bounced"


class DailyReport(Base):
    """One report per date (can have multiple versions)."""
    __tablename__ = "daily_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus), default=ReportStatus.draft, nullable=False
    )
    # Article IDs included in this report
    included_article_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Keyword/category analysis cache
    keyword_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    versions: Mapped[list["ReportVersion"]] = relationship(
        "ReportVersion", back_populates="report", order_by="ReportVersion.version_number.desc()"
    )
    deliveries: Mapped[list["EmailDelivery"]] = relationship(
        "EmailDelivery", back_populates="report"
    )

    @property
    def latest_version(self) -> "ReportVersion | None":
        return self.versions[0] if self.versions else None

    def __repr__(self) -> str:
        return f"<DailyReport date={self.report_date} status={self.status}>"


class ReportVersion(Base):
    """Versioned content of a report (supports re-generation and manual edits)."""
    __tablename__ = "report_versions"
    __table_args__ = (
        UniqueConstraint("report_id", "version_number", name="uq_report_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Generated content
    subject_line: Mapped[str] = mapped_column(String(300), nullable=False)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    plain_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    web_preview_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # LLM metadata
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Manual edits
    edited_by_operator: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    report: Mapped["DailyReport"] = relationship("DailyReport", back_populates="versions")
    sections: Mapped[list["ReportSection"]] = relationship(
        "ReportSection", back_populates="version", order_by="ReportSection.order"
    )


class ReportSection(Base):
    """Individual section within a report version."""
    __tablename__ = "report_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("report_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    section_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # top_issues | tech_changes | new_services
    content_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    html_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    version: Mapped["ReportVersion"] = relationship("ReportVersion", back_populates="sections")


class EmailDelivery(Base):
    """Delivery record per recipient per report."""
    __tablename__ = "email_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("daily_reports.id"), nullable=False, index=True
    )
    version_id: Mapped[int] = mapped_column(
        ForeignKey("report_versions.id"), nullable=False, index=True
    )
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("recipients.id"), nullable=False, index=True
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus), default=DeliveryStatus.pending, nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    report: Mapped["DailyReport"] = relationship("DailyReport", back_populates="deliveries")
    recipient: Mapped["Recipient"] = relationship("Recipient")  # noqa: F821
