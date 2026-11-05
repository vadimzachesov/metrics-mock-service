#!/bin/bash
# Скрипт быстрого возобновления работы стенда мониторинга
echo -e "\033[36m=== Возобновление работы сервисов мониторинга ===\033[0m"
kubectl scale deployment --all --replicas=1 -n monitoring

echo -e "\n\033[36mОжидаем запуск подов...\033[0m"
kubectl get pods -n monitoring
echo -e "\n\033[32mГотово! Grafana доступна по адресу: http://localhost:30080\033[0m"
