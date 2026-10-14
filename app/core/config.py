from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Incident Prediction Mock Service"
    app_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    base_latency: float = 0.05
    enable_background_traffic: bool = True

    class Config:
        env_prefix = "APP_"

settings = Settings()
