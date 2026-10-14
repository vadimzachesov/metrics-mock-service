# PowerShell скрипт для быстрого развертывания тестового стенда в Kubernetes (Minikube / Docker Desktop)

Write-Host "=== 1. Проверка и сборка Docker-образа Mock-сервиса ===" -ForegroundColor Cyan
Push-Location "$PSScriptRoot\app"
try {
    docker build -t mock-service:latest .
} finally {
    Pop-Location
}

Write-Host "`n=== 2. Создание Namespace 'monitoring' ===" -ForegroundColor Cyan
kubectl apply -f "$PSScriptRoot\manifests\00-namespace.yaml"

Write-Host "`n=== 3. Установка Kube-State-Metrics и Node-Exporter через Helm ===" -ForegroundColor Cyan
if (Get-Command helm -ErrorAction SilentlyContinue) {
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update

    # Установка Kube-State-Metrics
    helm upgrade --install ksm prometheus-community/kube-state-metrics `
      --namespace monitoring

    # Установка Node-Exporter
    helm upgrade --install node-exporter prometheus-community/prometheus-node-exporter `
      --namespace monitoring
} else {
    Write-Warning "Утилита 'helm' не найдена в PATH. Шаг установки ksm и node-exporter пропущен."
    Write-Host "Для их установки выполните: winget install Helm.Helm (или scoop install helm), затем перезапустите скрипт." -ForegroundColor Yellow
}

Write-Host "`n=== 4. Применение манифестов мониторинга и сервисов ===" -ForegroundColor Cyan
kubectl apply -f "$PSScriptRoot\manifests\01-rbac-vmagent.yaml"
kubectl apply -f "$PSScriptRoot\manifests\02-victoriametrics.yaml"
kubectl apply -f "$PSScriptRoot\manifests\03-vmagent.yaml"
if (Test-Path "$PSScriptRoot\manifests\04-grafana-secret.yaml") {
    kubectl apply -f "$PSScriptRoot\manifests\04-grafana-secret.yaml"
} else {
    kubectl apply -f "$PSScriptRoot\manifests\04-grafana-secret.example.yaml"
}
kubectl apply -f "$PSScriptRoot\manifests\04-grafana.yaml"
kubectl apply -f "$PSScriptRoot\manifests\05-mock-app.yaml"

Write-Host "`n=== 5. Проверка статуса подов ===" -ForegroundColor Green
kubectl get pods -n monitoring
Write-Host "`nГотово! Grafana доступна в браузере: http://localhost:30080" -ForegroundColor Yellow
