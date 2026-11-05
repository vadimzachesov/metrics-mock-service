import time
from pydantic import BaseModel, Field


class ChaosState(BaseModel):
    # Флаги активности сбоев
    latency_anomaly: bool = False
    error_anomaly: bool = False
    queue_spike: bool = False

    # Степень тяжести аварии (0.0 = норма, 1.0 = полный отказ)
    # Позволяет моделировать фазу инкубации (ранней деградации)
    severity: float = Field(default=0.0, ge=0.0, le=1.0)

    # Динамическая аккумулирующая очередь (физический бэклог)
    current_queue: float = 15.0
    last_update_ts: float = Field(default_factory=time.time)

    def reset(self):
        self.latency_anomaly = False
        self.error_anomaly = False
        self.queue_spike = False
        self.severity = 0.0
        self.current_queue = 15.0


chaos_state = ChaosState()
