from fastapi import APIRouter

from app.api.v1 import analytics, articles, dashboard, deliveries, jobs, recipients, reports, sources

router = APIRouter(prefix="/api/v1")
router.include_router(dashboard.router)
router.include_router(sources.router)
router.include_router(articles.router)
router.include_router(reports.router)
router.include_router(recipients.router)
router.include_router(deliveries.router)
router.include_router(analytics.router)
router.include_router(jobs.router)
