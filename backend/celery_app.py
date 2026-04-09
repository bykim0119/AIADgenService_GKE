from celery import Celery

celery_app = Celery(
    "ad_tasks",
    broker="redis://redis-service:6379/0",
    backend="redis://redis-service:6379/0",
    include=["tasks"],
)

celery_app.conf.update(
    result_expires=3600,          # 결과 1시간 보관
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,      # STARTED 상태 추적
    worker_prefetch_multiplier=1, # GPU 순차 처리
)
