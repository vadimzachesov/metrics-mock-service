from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter(tags=["System"])

@router.get("/metrics")
def metrics():
    """Эндпоинт для скрейпинга метрик агентом vmagent / Prometheus."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/healthz")
def healthz():
    """Liveness / Readiness probe."""
    return {"status": "ok"}
