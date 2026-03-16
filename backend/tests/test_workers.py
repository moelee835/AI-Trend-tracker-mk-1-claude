"""Tests for workers/tasks helpers and celery configuration."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
import asyncio


class TestRunAsync:
    def test_run_async_executes_coroutine(self):
        from app.workers.tasks import _run_async

        async def sample_coro():
            return 42

        result = _run_async(sample_coro())
        assert result == 42

    def test_run_async_with_exception(self):
        from app.workers.tasks import _run_async

        async def failing_coro():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            _run_async(failing_coro())


class TestLoggedTask:
    def test_on_failure_logs_error(self):
        from app.workers.tasks import LoggedTask
        import logging

        task = LoggedTask()
        task.name = "test.task"

        # Should not raise
        with patch.object(logging.getLogger("app.workers.tasks"), "error") as mock_log:
            task.on_failure(
                exc=Exception("test failure"),
                task_id="abc123",
                args=[],
                kwargs={},
                einfo=None,
            )
            mock_log.assert_called_once()


class TestCeleryConfig:
    def test_celery_app_beat_schedule_has_three_tasks(self):
        from app.workers.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert len(schedule) == 3
        assert "daily-collect" in schedule
        assert "daily-report" in schedule
        assert "daily-send" in schedule

    def test_celery_app_collect_task_name(self):
        from app.workers.celery_app import celery_app

        collect = celery_app.conf.beat_schedule["daily-collect"]
        assert collect["task"] == "app.workers.tasks.collect_articles_task"

    def test_celery_app_report_task_name(self):
        from app.workers.celery_app import celery_app

        report = celery_app.conf.beat_schedule["daily-report"]
        assert report["task"] == "app.workers.tasks.generate_report_task"

    def test_celery_app_send_task_name(self):
        from app.workers.celery_app import celery_app

        send = celery_app.conf.beat_schedule["daily-send"]
        assert send["task"] == "app.workers.tasks.send_daily_email_task"

    def test_celery_app_timezone_is_utc(self):
        from app.workers.celery_app import celery_app

        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_celery_app_serialization_config(self):
        from app.workers.celery_app import celery_app

        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content
