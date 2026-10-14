# Скрипт быстрого возобновления работы стенда мониторинга
Write-Host "=== Возобновление работы сервисов мониторинга ===" -ForegroundColor Cyan
kubectl scale deployment --all --replicas=1 -n monitoring

Write-Host "`nОжидаем запуск подов..." -ForegroundColor Cyan
kubectl get pods -n monitoring
Write-Host "`nГотово! Grafana доступна по адресу: http://localhost:30080" -ForegroundColor Green
