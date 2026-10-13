import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from core.config import settings
from metrics.prometheus import init_metrics
from services.background_worker import synthetic_traffic_worker
from api.system import router as system_router
from api.chaos import router as chaos_router
from api.v1.orders import router as orders_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: инициализация метрик и запуск фонового генератора трафика
    init_metrics()
    stop_event = asyncio.Event()
    worker_task = None

    if settings.enable_background_traffic:
        worker_task = asyncio.create_task(synthetic_traffic_worker(stop_event))

    yield

    # Shutdown: корректное завершение фоновых задач
    if worker_task:
        stop_event.set()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Регистрация модульных роутеров
    app.include_router(system_router)
    app.include_router(chaos_router)
    app.include_router(orders_router)

    return app

app = create_app()
