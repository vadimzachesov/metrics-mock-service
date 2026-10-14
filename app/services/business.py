import asyncio
import random
import time
from typing import Tuple, Dict, Any

from core.config import settings
from core.state import chaos_state
from metrics.prometheus import REQUESTS_TOTAL, PROCESSING_TIME_SECONDS

class BusinessService:
    @staticmethod
    async def process_orders() -> Tuple[int, Dict[str, Any]]:
        start_time = time.time()
        endpoint = "/api/v1/orders"

        # Расчет задержки
        delay = settings.base_latency + random.uniform(0.01, 0.04)
        if chaos_state.latency_anomaly:
            delay += random.uniform(1.2, 2.8)
        await asyncio.sleep(delay)

        # Моделирование сбоев
        error_threshold = 0.40 if chaos_state.error_anomaly else 0.02
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

        # Фиксация метрик
        duration = time.time() - start_time
        REQUESTS_TOTAL.labels(method="GET", endpoint=endpoint, status_code=str(status_code)).inc()
        PROCESSING_TIME_SECONDS.labels(endpoint=endpoint).observe(duration)

        return status_code, payload

    @staticmethod
    async def process_payment() -> Tuple[int, Dict[str, Any]]:
        start_time = time.time()
        endpoint = "/api/v1/payment"

        delay = settings.base_latency + random.uniform(0.02, 0.05)
        if chaos_state.latency_anomaly:
            delay += random.uniform(1.5, 3.5)
        await asyncio.sleep(delay)

        error_threshold = 0.50 if chaos_state.error_anomaly else 0.01
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
