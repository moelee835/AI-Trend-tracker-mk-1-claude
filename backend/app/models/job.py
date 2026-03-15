"""Job execution log model."""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class JobType(str, enum.Enum):
    collect = "collect"
    analyze = "analyze"
    generate_report = "generate_report"
    send_email = "send_email"
    manual_resend = "manual_resend"


class JobStatus(str, enum.Enum):
    running = "running"
    success = "success"
    failed = "failed"
    partial = "partial"


class JobExecutionLog(Base):
    __tablename__ = "job_execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False, index=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(50), default="scheduler", nullable=False)
    # summary counts
    result_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def duration_seconds(self) -> float | None:
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
