# Incident Prediction Lab — Data-Agnostic Kubernetes Monitoring Stack

Локальный тестовый полигон в Kubernetes для проекта по **раннему прогнозированию инцидентов с помощью ML**.

## Архитектура
* **Mock Service (`app/`)**: FastAPI-микросервис с имитацией бизнес-логики, автономным фоновым генератором трафика, экспортом кастомных метрик в Prometheus-формате и API для инъекции аномалий.
* **Инфраструктурные метрики**: `kube-state-metrics` (состояния подов/реплик/рестартов) и `node-exporter` (CPU/RAM/диск узлов).
* **Сбор метрик**: `vmagent` (VictoriaMetrics Agent) с динамическим Kubernetes Service Discovery.
* **TSDB (Хранилище)**: Single-node `VictoriaMetrics` (Data-Agnostic time-series storage с поддержкой PromQL API).
* **Визуализация**: `Grafana` с автоматическим подключением VictoriaMetrics в качестве источника данных.

---

## Структура репозитория

```text
Project/
├── app/
│   ├── main.py              # Точка входа FastAPI, Lifespan и подключение роутеров
│   ├── pyproject.toml       # Описание проекта и зависимости (PEP 621)
│   ├── uv.lock              # Зафиксированные детерминированные зависимости
│   ├── Dockerfile           # Контейнеризация сервиса через Astral uv
│   ├── core/
│   │   ├── config.py        # Настройки приложения (pydantic-settings)
│   │   └── state.py         # Состояние аномалий (ChaosState)
│   ├── metrics/
│   │   └── prometheus.py    # Экспортируемые Prometheus-метрики
│   ├── services/
│   │   ├── business.py      # Бизнес-логика (заказы, платежи)
│   │   └── background_worker.py # Фоновый воркер трафика и шума
│   └── api/
│       ├── system.py        # Эндпоинты /healthz и /metrics
│       ├── chaos.py         # Эндпоинты управления аномалиями (/chaos/inject)
│       └── v1/
│           └── orders.py    # Бизнес-эндпоинты (/api/v1/orders, /payment)
├── manifests/
│   ├── 00-namespace.yaml    # Namespace 'monitoring'
│   ├── 01-rbac-vmagent.yaml # RBAC для обнаружения подов/сервисов агентом
│   ├── 02-victoriametrics.yaml # TSDB база данных
│   ├── 03-vmagent.yaml      # Scrape-конфигурация и сборщик метрик
│   ├── 04-grafana.yaml      # Grafana с auto-provisioning
│   └── 05-mock-app.yaml     # Деплой тестового приложения
├── deploy.ps1               # Скрипт автоматического запуска (PowerShell)
├── export_dataset.py        # Скрипт потоковой выгрузки датасета в Pandas
├── README.md                # Краткая памятка
└── ProdREADME.md            # Интерактивный учебник: теория, проверки и коммиты
```

---

## Быстрый запуск

### Вариант 1. Автоматический запуск (PowerShell)
```powershell
.\deploy.ps1
```

### Вариант 2. Пошаговый запуск

1. **Сборка Docker-образа:**
   ```powershell
   cd app
   docker build -t mock-service:latest .
   cd ..
   ```
   *(Если используется Minikube, перед сборкой выполните `minikube docker-env | Invoke-Expression`)*

2. **Развертывание K8s-манифестов:**
   ```powershell
   kubectl apply -f manifests/00-namespace.yaml
   
   # Helm-чарты инфраструктурных метрик
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm repo update
   helm upgrade --install ksm prometheus-community/kube-state-metrics -n monitoring
   helm upgrade --install node-exporter prometheus-community/prometheus-node-exporter -n monitoring

   # Мониторинг и Mock-приложение
   kubectl apply -f manifests/01-rbac-vmagent.yaml
   kubectl apply -f manifests/02-victoriametrics.yaml
   kubectl apply -f manifests/03-vmagent.yaml
   kubectl apply -f manifests/04-grafana.yaml
   kubectl apply -f manifests/05-mock-app.yaml
   ```

---

## Доступ к интерфейсам

* **Grafana**:
  ```powershell
  kubectl port-forward svc/grafana 3000:3000 -n monitoring
  ```
  URL: `http://localhost:3000` (Логин: `admin`, Пароль: `admin`).

* **VictoriaMetrics UI (`vmui`)**:
  ```powershell
  kubectl port-forward svc/victoria-metrics 8428:8428 -n monitoring
  ```
  URL: `http://localhost:8428/vmui`

* **Mock Service (API & Управление аномалиями)**:
  ```powershell
  kubectl port-forward svc/mock-service 8000:8000 -n monitoring
  ```
  URL: `http://localhost:8000/metrics`

---

## Управление аномалиями (Chaos Injection)

Сервис непрерывно генерирует нормальный фоновый шум. Для проверки модели раннего прогнозирования вы можете инициировать сбои:

1. **Деградация задержек (Latency Anomaly)**:
   ```bash
   curl -X POST "http://localhost:8000/chaos/inject?anomaly_type=latency&enable=true"
   ```
2. **Всплеск ошибок 5xx (Cascading Failures)**:
   ```bash
   curl -X POST "http://localhost:8000/chaos/inject?anomaly_type=errors&enable=true"
   ```
3. **Раздувание очереди (Queue Overload)**:
   ```bash
   curl -X POST "http://localhost:8000/chaos/inject?anomaly_type=queue&enable=true"
   ```
4. **Возврат в нормальное состояние**:
   ```bash
   curl -X POST "http://localhost:8000/chaos/inject?anomaly_type=latency&enable=false"
   ```

---

## Выгрузка метрик в Python для ML

VictoriaMetrics предоставляет эндпоинт `/api/v1/export`, который отдает данные в потоковом формате JSON Lines:

```python
import requests
import json
import pandas as pd

VM_HOST = "http://localhost:8428"

# Экспорт метрик за последние 30 минут
response = requests.get(
    f"{VM_HOST}/api/v1/export",
    params={
        "match[]": '{__name__=~"mock_app.*|node_cpu.*|kube_pod.*"}',
    },
    stream=True
)

records = []
for line in response.iter_lines():
    if line:
        data = json.loads(line)
        metric_name = data["metric"].get("__name__")
        timestamps = data["values"]
        # Преобразование в удобный DataFrame для обучения
```
