# ====================================================
# СТАДИЯ 1: Сборщик зависимостей и окружения (Builder)
# ====================================================
FROM python:3.11-slim AS builder

# Копируем uv из официального бинарного образа Astral
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Оптимизация сборки uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# 1. Кэширование слоев: сначала только манифесты зависимостей
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 2. Копируем исходный код микросервиса и завершаем установку
COPY . .
RUN uv sync --frozen --no-dev

# ====================================================
# СТАДИЯ 2: Финальный легковесный рантайм (Runner)
# ====================================================
FROM python:3.11-slim AS runner

WORKDIR /app

# Настройки рантайма Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH"

# Создаем непривилегированного пользователя appuser (UID 1000)
RUN useradd -u 1000 appuser

# Копируем из стадии builder готовое окружение .venv и код с нужными правами
COPY --from=builder --chown=appuser:appuser /app /app

USER appuser

EXPOSE 8000

# Команда запуска веб-сервера Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
