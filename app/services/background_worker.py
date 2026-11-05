import asyncio
import math
import random
import time

from core.config import settings
from core.state import chaos_state
from metrics.prometheus import QUEUE_DEPTH, REQUESTS_TOTAL, PROCESSING_TIME_SECONDS


async def synthetic_traffic_worker(stop_event: asyncio.Event):
    """
    Фоновый воркер с реалистичной физикой очередей (M/M/1), суточной волной
    трафика и непрерывной динамикой накопления/дренажа задержек.
    """
    start_time = time.time()

    while not stop_event.is_set():
        try:
            now = time.time()
            elapsed_m = (now - start_time) / 60.0

            # 1. Суточная синусоида нагрузки (diurnal wave): RPS плавно «дышит»
            diurnal_factor = 1.0 + 0.35 * math.sin(elapsed_m * 2 * math.pi / 15.0)

            # 2. Физическая модель очереди (M/M/1 Queuing Dynamics):
            # Приток задач (Inflow) зависит от суточной волны
            inflow = random.uniform(8.0, 16.0) * diurnal_factor

            # Пропускная способность (Outflow) падает при авариях
            if chaos_state.queue_spike or chaos_state.latency_anomaly:
                capacity = max(2.0, 14.0 * (1.0 - 0.85 * chaos_state.severity))
            else:
                capacity = random.uniform(13.0, 18.0)

            # Очередь накапливается и рассасывается плавно, а не прыгает мгновенно
            chaos_state.current_queue = max(
                2.0,
                chaos_state.current_queue + (inflow - capacity) * 0.4
            )
            QUEUE_DEPTH.set(round(chaos_state.current_queue, 1))

            # 3. Обработка запросов с тяжелыми хвостами распределения
            endpoint = random.choice(["/api/v1/orders", "/api/v1/payment"])
            base = settings.base_latency

            # Логнормальное распределение задержки (как в реальных веб-сервисах)
            duration = base + random.lognormvariate(-3.2, 0.25)
            if chaos_state.latency_anomaly:
                # Плавное нарастание задержки по severity
                duration += random.uniform(0.3, 1.8) * chaos_state.severity

            # Ошибки зависят от силы аварии
            err_chance = 0.01 + (0.45 * chaos_state.severity if chaos_state.error_anomaly else 0.0)
            st_code = "500" if random.random() < err_chance else "200"

            REQUESTS_TOTAL.labels(method="GET", endpoint=endpoint, status_code=st_code).inc()
            PROCESSING_TIME_SECONDS.labels(endpoint=endpoint).observe(duration)

            # Интервал между запросами модулируется нагрузкой
            interval = max(0.05, (0.5 / diurnal_factor) + random.uniform(-0.08, 0.08))
            await asyncio.sleep(interval)

        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(1)
