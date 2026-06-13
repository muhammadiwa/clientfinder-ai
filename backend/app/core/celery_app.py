"""
Celery Application — T1 placeholder
Full configuration in T2.
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "clientfinder",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.scraping_tasks",
        "app.tasks.analysis_tasks",
        "app.tasks.outreach_tasks",
        "app.tasks.scheduled_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    broker_connection_retry_on_startup=True,
)
