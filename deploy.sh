#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "\033[36m=== 1. Проверка и сборка Docker-образа Mock-сервиса ===\033[0m"
cd "$SCRIPT_DIR/app"
docker build -t mock-service:latest .
cd "$SCRIPT_DIR"

# Если используется kind, загружаем локальный образ в ноду кластера
if command -v kind &> /dev/null; then
    if kind get clusters 2>/dev/null | grep -q "telemetry-lab"; then
        echo -e "\033[33mЗагрузка образа mock-service:latest в кластер kind (telemetry-lab)...\033[0m"
        kind load docker-image mock-service:latest --name telemetry-lab
    fi
fi

echo -e "\n\033[36m=== 2. Создание Namespace 'monitoring' ===\033[0m"
kubectl apply -f "$SCRIPT_DIR/manifests/00-namespace.yaml"

echo -e "\n\033[36m=== 3. Установка Kube-State-Metrics и Node-Exporter через Helm ===\033[0m"
if command -v helm &> /dev/null; then
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
    helm repo update

    helm upgrade --install ksm prometheus-community/kube-state-metrics \
      --namespace monitoring

    helm upgrade --install node-exporter prometheus-community/prometheus-node-exporter \
      --namespace monitoring \
      --set hostRootFsMount.enabled=false
else
    echo -e "\033[33mУтилита 'helm' не найдена. Шаг установки ksm и node-exporter пропущен.\033[0m"
fi

echo -e "\n\033[36m=== 4. Применение манифестов мониторинга и сервисов ===\033[0m"
kubectl apply -f "$SCRIPT_DIR/manifests/01-rbac-vmagent.yaml"
kubectl apply -f "$SCRIPT_DIR/manifests/02-victoriametrics.yaml"
kubectl apply -f "$SCRIPT_DIR/manifests/03-vmagent.yaml"

if [ -f "$SCRIPT_DIR/manifests/04-grafana-secret.yaml" ]; then
    kubectl apply -f "$SCRIPT_DIR/manifests/04-grafana-secret.yaml"
else
    kubectl apply -f "$SCRIPT_DIR/manifests/04-grafana-secret.example.yaml"
fi

kubectl apply -f "$SCRIPT_DIR/manifests/04-grafana.yaml"
kubectl apply -f "$SCRIPT_DIR/manifests/05-mock-app.yaml"

echo -e "\n\033[32m=== 5. Проверка статуса подов ===\033[0m"
kubectl get pods -n monitoring

echo -e "\n\033[32mГотово! Все сервисы мониторинга запущены.\033[0m"
echo -e "\033[33mGrafana доступна по адресу: http://localhost:30080\033[0m"
