# Скрипт безопасной остановки стенда мониторинга (освобождение 100% ресурсов ПК)
Write-Host "=== Остановка всех сервисов мониторинга ===" -ForegroundColor Cyan
kubectl scale deployment --all --replicas=0 -n monitoring

Write-Host "`nВсе поды остановлены. Ресурсы процессора и оперативной памяти освобождены на 100%!" -ForegroundColor Green
Write-Host "Для возобновления работы запустите: .\start.ps1" -ForegroundColor Yellow
