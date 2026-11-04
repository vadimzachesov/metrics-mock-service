#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

echo -e "\033[36m=== Настройка Kubernetes окружения в GitHub Codespaces ===\033[0m"

# 1. Установка kind, если его ещё нет
if ! command -v kind &> /dev/null; then
    echo "Установка утилиты kind (Kubernetes in Docker)..."
    ARCH=$(dpkg --print-architecture 2>/dev/null || echo "amd64")
    curl -Lo ./kind "https://kind.sigs.k8s.io/dl/v0.24.0/kind-linux-${ARCH}"
    chmod +x ./kind
    sudo mv ./kind /usr/local/bin/kind
fi

# 2. Создание кластера kind с маппингом портов
if ! kind get clusters 2>/dev/null | grep -q "telemetry-lab"; then
    echo "Создание кластера kind (telemetry-lab)..."
    kind create cluster --name telemetry-lab --config .devcontainer/kind-config.yaml
else
    echo "Кластер telemetry-lab уже существует."
fi

# 3. Выдача прав на исполнение скриптам
chmod +x deploy.sh start.sh stop.sh 2>/dev/null || true

# 4. Установка ML зависимостей
echo "Установка Python библиотек для анализа данных и ML..."
pip install --no-cache-dir requests pandas catboost scikit-learn matplotlib

# 5. Развёртывание стенда мониторинга
echo "Развертывание сервисов стенда..."
./deploy.sh

echo -e "\n\033[32m=== ВСЕ ГОТОВО! ===\033[0m"
echo -e "\033[33mПерейдите во вкладку 'PORTS' внизу экрана VS Code, чтобы открыть Grafana или Swagger!\033[0m"
