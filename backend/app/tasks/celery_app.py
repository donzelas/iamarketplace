from celery import Celery
from celery.schedules import crontab

from ..config import settings

celery_app = Celery(
    "ecommerce_ai",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

interval = settings.monitoring_interval_minutes

celery_app.conf.beat_schedule = {
    "monitor-competitors": {
        "task": "app.tasks.monitoring_tasks.collect_competitor_data",
        "schedule": crontab(minute=f"*/{interval}"),
        "options": {"queue": "monitoring"},
    },
    "analyze-and-decide": {
        "task": "app.tasks.monitoring_tasks.analyze_and_decide",
        "schedule": crontab(minute="0"),
        "options": {"queue": "analysis"},
    },
    "collect-ads-performance": {
        "task": "app.tasks.monitoring_tasks.collect_ads_performance",
        "schedule": crontab(hour="*/6", minute="15"),
        "options": {"queue": "ads"},
    },
    "daily-margin-snapshots": {
        "task": "app.tasks.monitoring_tasks.daily_margin_snapshots",
        "schedule": crontab(hour="8", minute="0"),
        "options": {"queue": "analysis"},
    },
}
