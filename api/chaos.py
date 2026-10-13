from fastapi import APIRouter, HTTPException, Query
from core.state import chaos_state
from metrics.prometheus import ANOMALY_ACTIVE

router = APIRouter(prefix="/chaos", tags=["Chaos Engineering"])

@router.post("/inject")
def inject_anomaly(
    anomaly_type: str = Query(..., description="Тип аномалии: latency, errors, queue"),
    enable: bool = Query(True, description="Включить (true) или отключить (false)")
):
    """
    Эндпоинт управления хаосом для ML-экспериментов:
    - latency: провоцирует деградацию времени ответа
    - errors: провоцирует каскадный рост 5xx
    - queue: провоцирует раздувание синтетической очереди
    """
    if anomaly_type == "latency":
        chaos_state.latency_anomaly = enable
        ANOMALY_ACTIVE.labels(anomaly_type="latency").set(1 if enable else 0)
    elif anomaly_type == "errors":
        chaos_state.error_anomaly = enable
        ANOMALY_ACTIVE.labels(anomaly_type="errors").set(1 if enable else 0)
    elif anomaly_type == "queue":
        chaos_state.queue_spike = enable
        ANOMALY_ACTIVE.labels(anomaly_type="queue").set(1 if enable else 0)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Неизвестный тип аномалии: {anomaly_type}. Доступны: latency, errors, queue"
        )

    return {
        "status": "success",
        "message": f"Аномалия '{anomaly_type}' установлена в state={enable}",
        "current_state": chaos_state.model_dump()
    }

@router.get("/status")
def chaos_status():
    """Текущее состояние симулятора аномалий."""
    return {"current_state": chaos_state.model_dump()}
