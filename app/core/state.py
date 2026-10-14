from pydantic import BaseModel

class ChaosState(BaseModel):
    latency_anomaly: bool = False
    error_anomaly: bool = False
    queue_spike: bool = False

    def reset(self):
        self.latency_anomaly = False
        self.error_anomaly = False
        self.queue_spike = False

# Синглтон состояния хаоса приложения
chaos_state = ChaosState()
