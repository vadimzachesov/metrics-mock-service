import asyncio
import random
import time
from typing import Any

from core.config import settings
from core.state import chaos_state
from metrics.prometheus import REQUESTS_TOTAL, PROCESSING_TIME_SECONDS


class BusinessService:
    @staticmethod
    async def process_orders() -> tuple[int, dict[str, Any]]:
        start_time = time.time()
        endpoint = "/api/v1/orders"

        # 1. Базовая задержка нормального запроса (30-60 мс)
        delay = settings.base_latency + random.uniform(0.005, 0.025)

        # 2. Штатный выброс (Benign Jitter / GC-пауза) - НЕ аномалия!
        # Раз в ~120 запросов один случайный запрос подвисает на 150-250 мс
        if random.random() < 0.008:
            delay += random.uniform(0.15, 0.25)

        # 3. Деградация при аномалии (масштабируется от severity)
        if chaos_state.latency_anomaly:
            # Часть запросов успевает проскочить, часть залипает в таймаут (bimodal tail)
            if random.random() < 0.75:
                delay += random.uniform(0.4, 2.0) * chaos_state.severity

        await asyncio.sleep(delay)

        # 4. Вероятность сбоя: плавный рост вместо жесткой константы
        error_threshold = 0.015 + (0.35 * chaos_state.severity if chaos_state.error_anomaly else 0.0)
        if random.random() < error_threshold:
            status_code = 500
            payload = {"error": "Internal Server Error"}
        else:
            status_code = 200
            payload = {
                "orders": [
                    {"id": i, "price": random.randint(10, 500)} for i in range(5)
                ]
            }

        duration = time.time() - start_time
        REQUESTS_TOTAL.labels(method="GET", endpoint=endpoint, status_code=str(status_code)).inc()
        PROCESSING_TIME_SECONDS.labels(endpoint=endpoint).observe(duration)

        return status_code, payload

    @staticmethod
    async def process_payment() -> tuple[int, dict[str, Any]]:
        start_time = time.time()
        endpoint = "/api/v1/payment"

        delay = settings.base_latency + random.uniform(0.01, 0.03)

        # GC-пауза
        if random.random() < 0.008:
            delay += random.uniform(0.15, 0.25)

        if chaos_state.latency_anomaly:
            if random.random() < 0.75:
                delay += random.uniform(0.5, 2.5) * chaos_state.severity

        await asyncio.sleep(delay)

        error_threshold = 0.01 + (0.45 * chaos_state.severity if chaos_state.error_anomaly else 0.0)
        if random.random() < error_threshold:
            status_code = 503
            payload = {"error": "Payment Gateway Timeout"}
        else:
            status_code = 201
            payload = {"status": "paid", "transaction_id": random.randint(10000, 99999)}

        duration = time.time() - start_time
        REQUESTS_TOTAL.labels(method="POST", endpoint=endpoint, status_code=str(status_code)).inc()
        PROCESSING_TIME_SECONDS.labels(endpoint=endpoint).observe(duration)

        return status_code, payload
