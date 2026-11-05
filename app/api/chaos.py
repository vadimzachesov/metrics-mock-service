import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from core.state import chaos_state
from metrics.prometheus import ANOMALY_ACTIVE

router = APIRouter(prefix="/chaos", tags=["Chaos Engineering"])


async def ramp_severity(target: float, duration_seconds: float = 20.0):
    """
    Плавно разгоняет или гасит аномалию, моделируя реальную фазу
    ранней инкубации сбоя (Early Warning transition).
    """
    steps = 15
    sleep_per_step = max(0.2, duration_seconds / steps)
    start_val = chaos_state.severity
    diff = target - start_val

    for i in range(1, steps + 1):
        await asyncio.sleep(sleep_per_step)
        chaos_state.severity = round(start_val + diff * (i / steps), 3)


@router.post("/inject")
async def inject_anomaly(
    background_tasks: BackgroundTasks,
    anomaly_type: str = Query(..., description="Тип аномалии: latency, errors, queue"),
    enable: bool = Query(True, description="Включить (true) или отключить (false)"),
    ramp_seconds: float = Query(20.0, description="Время плавного разгона/угасания сбоя в секундах"),
):
    """
    Эндпоинт управления хаосом для ML-экспериментов:
    - latency: плавная деградация времени ответа
    - errors: нарастающий рост 5xx
    - queue: физическое наполнение очереди из-за падения пропускной способности
    """
    valid_types = ["latency", "errors", "queue"]
    if anomaly_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Неизвестный тип аномалии: {anomaly_type}. Доступны: {valid_types}",
        )

    attr_name = f"{anomaly_type}_anomaly" if anomaly_type != "queue" else "queue_spike"
    setattr(chaos_state, attr_name, enable)
    ANOMALY_ACTIVE.labels(anomaly_type=anomaly_type).set(1 if enable else 0)

    target_severity = 1.0 if enable else 0.0
    background_tasks.add_task(ramp_severity, target_severity, ramp_seconds)

    return {
        "status": "success",
        "message": f"Аномалия '{anomaly_type}' установлена (enable={enable}, ramp_seconds={ramp_seconds})",
        "current_state": chaos_state.model_dump(),
    }


@router.get("/status")
def chaos_status():
    """Текущее состояние симулятора аномалий."""
    return {"current_state": chaos_state.model_dump()}
