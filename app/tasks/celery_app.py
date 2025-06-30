from celery import Celery
from app.config import settings
import structlog

logger = structlog.get_logger()

# Configuração do Celery
celery_app = Celery(
    "neuroflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.memory_tasks"]
)

# Configurações do Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutos
    task_soft_time_limit=25 * 60,  # 25 minutos
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Configuração das filas
celery_app.conf.task_routes = {
    "app.tasks.memory_tasks.update_memory_task": {"queue": "memory"},
    "app.tasks.memory_tasks.cleanup_old_sessions": {"queue": "maintenance"},
}

# Configuração de retry
celery_app.conf.task_annotations = {
    "app.tasks.memory_tasks.update_memory_task": {
        "rate_limit": "10/s",
        "max_retries": 3,
        "default_retry_delay": 60,
    }
}

logger.info("Celery app configured")
