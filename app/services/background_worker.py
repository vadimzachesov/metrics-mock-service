import asyncio
import random

from core.config import settings
from core.state import chaos_state
from metrics.prometheus import QUEUE_DEPTH, REQUESTS_TOTAL, PROCESSING_TIME_SECONDS

async def synthetic_traffic_worker(stop_event: asyncio.Event):
    """
    Фоновый воркер: симулирует постоянную нагрузку и колебания параметров
    для генерации реалистичного датасета в VictoriaMetrics.
    """
    while not stop_event.is_set():
        try:
            # Обновление размера очереди
            if chaos_state.queue_spike:
                QUEUE_DEPTH.set(random.randint(450, 1200))
            else:
                QUEUE_DEPTH.set(random.randint(5, 40))

            # Имитация внутренних обращений к бизнес-функциям
            endpoint = random.choice(["/api/v1/orders", "/api/v1/payment"])
            duration = settings.base_latency + (
                random.uniform(1.0, 2.5) if chaos_state.latency_anomaly else random.uniform(0.01, 0.05)
            )

            err_chance = 0.35 if chaos_state.error_anomaly else 0.02
            st_code = "500" if random.random() < err_chance else "200"

            REQUESTS_TOTAL.labels(method="GET", endpoint=endpoint, status_code=st_code).inc()
            PROCESSING_TIME_SECONDS.labels(endpoint=endpoint).observe(duration)

            await asyncio.sleep(random.uniform(0.3, 1.0))
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(1)
