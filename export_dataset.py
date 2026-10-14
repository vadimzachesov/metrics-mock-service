import requests
import json
import pandas as pd

# 1. Адрес эндпоинта экспорта сырых временных рядов VictoriaMetrics
VM_URL = "http://localhost:8428/api/v1/export"

# 2. Фильтр метрик: берем все метрики нашего приложения и CPU ноды
params = {
    "match[]": '{__name__=~"mock_app.*|node_cpu_seconds_total"}'
}

print("Запрашиваем данные из VictoriaMetrics...")
try:
    response = requests.get(VM_URL, params=params, stream=True, timeout=10)
    response.raise_for_status()

    # 3. Разбираем потоковый формат JSON Lines
    records = []
    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            metric_name = data["metric"].get("__name__")

            timestamps = data["timestamps"]
            values = data["values"]
            labels = {k: v for k, v in data["metric"].items() if k != "__name__"}

            for ts, val in zip(timestamps, values):
                records.append({
                    "timestamp": pd.to_datetime(ts, unit="ms"),
                    "metric": metric_name,
                    "value": val,
                    "labels": str(labels)
                })

    # 4. Формируем DataFrame
    df = pd.DataFrame(records)
    print(f"Успешно выгружено {len(df)} измерений!")
    print("\nПервые 5 строк датасета:")
    print(df.head())

    # 5. Пример преобразования в широкую матрицу фичей (Pivot Table) для ML:
    if not df.empty:
        feature_matrix = df.pivot_table(
            index="timestamp",
            columns="metric",
            values="value",
            aggfunc="mean"
        ).ffill()

        print("\nМатрица признаков (Features Matrix) для модели:")
        print(feature_matrix.head())

except requests.exceptions.RequestException as e:
    print(f"Ошибка подключения к VictoriaMetrics ({VM_URL}): {e}")
    print("Убедитесь, что проброшен порт: kubectl port-forward svc/victoria-metrics 8428:8428 -n monitoring")
