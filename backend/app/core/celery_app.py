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
        "app.tasks.drip_runner",
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
    # Route tasks to per-module queues so the worker processes
    # them in order. Without this, tasks default to the celery
    # default queue and our -Q scraping,analysis,outreach worker
    # never picks them up.
    task_routes={
        "app.tasks.scraping.*": {"queue": "scraping"},
        "app.tasks.analysis.*": {"queue": "analysis"},
        "app.tasks.outreach.*": {"queue": "outreach"},
        "app.tasks.drip_runner.*": {"queue": "outreach"},
    },
    # Periodic beat schedule — T6.2 / Sprint 3A multi-channel outreach.
    # The drip runner walks enrollments whose next_action_at <= now
    # and creates Message rows for the next step.
    beat_schedule={
        "drip-runner-every-15-min": {
            "task": "app.tasks.outreach.drip_runner",
            "schedule": 15 * 60.0,  # every 15 minutes
        },
        "send-approved-messages-every-5-min": {
            "task": "app.tasks.outreach.send_scheduled",
            "schedule": 5 * 60.0,
        },
    },
)
