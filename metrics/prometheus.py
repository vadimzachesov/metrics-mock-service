from prometheus_client import Counter, Histogram, Gauge

# ---------------------------------------------------------
# Обобщенные Data-Agnostic Prometheus Метрики
# ---------------------------------------------------------
REQUESTS_TOTAL = Counter(
    "mock_app_requests_total",
    "Общее количество HTTP-запросов",
    ["method", "endpoint", "status_code"],
)

PROCESSING_TIME_SECONDS = Histogram(
    "mock_app_processing_time_seconds",
    "Время обработки запроса в секундах",
    ["endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

QUEUE_DEPTH = Gauge(
    "mock_app_queue_depth",
    "Текущая глубина внутренней очереди задач (синтетический бэклог)",
)

ANOMALY_ACTIVE = Gauge(
    "mock_app_anomaly_mode_active",
    "Флаг активности режима аномалии (1 = аномалия, 0 = норма)",
    ["anomaly_type"],
)

def init_metrics():
    """Инициализация начальных значений метрик."""
    ANOMALY_ACTIVE.labels(anomaly_type="latency").set(0)
    ANOMALY_ACTIVE.labels(anomaly_type="errors").set(0)
    ANOMALY_ACTIVE.labels(anomaly_type="queue").set(0)
    QUEUE_DEPTH.set(10)
