#!/usr/bin/env python3
"""
Automated Kubernetes Chaos Experiment & Telemetry Collector.

Lifecycle:
  1. Verifies/Starts cluster monitoring and mock app.
  2. Runs baseline healthy traffic (10 min).
  3. Sequentially executes progressive chaos scenarios:
     - Incident 1: Database Latency Spike & Worker Stalling (ramp-up 20s).
     - Incident 2: Cascading 5xx Error Storm (ramp-up 20s).
     - Incident 3: Synthetic Backlog & Queue Saturation.
  4. Exports aligned feature matrix from VictoriaMetrics TSDB into CSV format.
  5. Scales all deployments to 0 replicas (stop.sh) to immediately idle the cluster.
  6. Exits cleanly -> GitHub Codespaces auto-shuts down after 5 minutes of inactivity.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import requests
import pandas as pd
import numpy as np

MOCK_API_URL = "http://localhost:8000"
VM_EXPORT_URL = "http://localhost:8428/api/v1/export"
VM_QUERY_URL = "http://localhost:8428/api/v1/query"

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_CSV = SCRIPT_DIR / "telemetry_codespaces.csv"


def log(msg: str):
    print(f"\033[36m[{datetime.now().strftime('%H:%M:%S')}]\033[0m {msg}", flush=True)


def is_port_open(port: int) -> bool:
    """Checks whether a local port is open and accepting TCP connections."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_port_forward(service: str, port: int) -> subprocess.Popen | None:
    """Launches kubectl port-forward in background if the port is not already bound."""
    if is_port_open(port):
        log(f"Port {port} is already open and responding.")
        return None
    log(f"Starting auto port-forward: kubectl port-forward svc/{service} {port}:{port} -n monitoring...")
    proc = subprocess.Popen(
        ["kubectl", "port-forward", f"svc/{service}", f"{port}:{port}", "-n", "monitoring"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def check_health(retries: int = 15, delay: float = 1.5) -> bool:
    """Verifies that mock-service and VictoriaMetrics are up and responding."""
    for i in range(retries):
        try:
            r1 = requests.get(f"{MOCK_API_URL}/healthz", timeout=2)
            r2 = requests.get(f"{VM_QUERY_URL}?query=up", timeout=2)
            if r1.status_code == 200 and r2.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(delay)
    return False


def inject_chaos(anomaly_type: str, enable: bool, ramp_seconds: float = 20.0):
    """Triggers progressive chaos mode on mock-service."""
    url = f"{MOCK_API_URL}/chaos/inject"
    params = {
        "anomaly_type": anomaly_type,
        "enable": "true" if enable else "false",
        "ramp_seconds": ramp_seconds,
    }
    try:
        r = requests.post(url, params=params, timeout=5)
        log(f"Chaos API: type={anomaly_type}, enable={enable} -> Status {r.status_code}")
    except Exception as e:
        log(f"\033[31mError calling chaos API: {e}\033[0m")


def stop_cluster():
    """Scales down all deployments to 0 to save 100% CPU and RAM in Codespaces."""
    log("Scaling down deployments to 0 (saving GitHub Codespaces credits)...")
    stop_script = SCRIPT_DIR / "stop.sh"
    if stop_script.exists():
        subprocess.run(["bash", str(stop_script)], check=False)
    else:
        subprocess.run(["kubectl", "scale", "deployment", "--all", "--replicas=0", "-n", "monitoring"], check=False)


def collect_metrics_from_vm(start_time_s: float, end_time_s: float) -> pd.DataFrame:
    """
    Queries VictoriaMetrics for the experiment interval and reconstructs
    the required ML feature columns:
      - queue_depth (Gauge)
      - rps (Rate of requests)
      - processing_time (Mean duration from histogram)
      - cpu_usage (Container or node CPU)
      - is_anomaly (Ground truth target)
    """
    log("Querying VictoriaMetrics Prometheus API for aligned feature timeseries...")
    step_s = 5
    timestamps = np.arange(start_time_s, end_time_s, step_s)
    
    # QueryPromQL helper:
    def query_promql(query: str) -> dict[int, float]:
        url = f"http://localhost:8428/api/v1/query_range"
        params = {
            "query": query,
            "start": int(start_time_s),
            "end": int(end_time_s),
            "step": f"{step_s}s",
        }
        res = {}
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for series in data.get("data", {}).get("result", []):
                    for ts, val in series.get("values", []):
                        ts_key = int(ts)
                        res[ts_key] = max(res.get(ts_key, 0.0), float(val))
        except Exception as e:
            log(f"Query error for '{query}': {e}")
        return res

    log("Fetching queue_depth...")
    q_map = query_promql("max(mock_app_queue_depth)")

    log("Fetching rps...")
    rps_map = query_promql("sum(rate(mock_app_requests_total[30s]))")

    log("Fetching processing_time...")
    lat_map = query_promql(
        "sum(rate(mock_app_processing_time_seconds_sum[30s])) / sum(rate(mock_app_processing_time_seconds_count[30s]))"
    )

    log("Fetching cpu_usage...")
    cpu_map = query_promql(
        "sum(rate(container_cpu_usage_seconds_total{container='mock-service'}[30s])) or sum(rate(node_cpu_seconds_total{mode!='idle'}[30s])) / count(node_cpu_seconds_total{mode='idle'})"
    )

    log("Fetching anomaly ground truth label...")
    anom_map = query_promql("max(mock_app_anomaly_mode_active)")

    rows = []
    for ts in timestamps:
        ts_int = int(ts)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        # Fallbacks if metrics had momentary gaps
        q = q_map.get(ts_int, np.nan)
        r = rps_map.get(ts_int, np.nan)
        lat = lat_map.get(ts_int, np.nan)
        cpu = cpu_map.get(ts_int, np.nan)
        anom = anom_map.get(ts_int, 0.0)

        rows.append({
            "timestamp": dt,
            "queue_depth": q,
            "rps": r,
            "processing_time": lat,
            "cpu_usage": cpu,
            "is_anomaly": int(anom > 0.5),
        })

    df = pd.DataFrame(rows)
    # Forward-fill / backward-fill gaps
    df["queue_depth"] = df["queue_depth"].ffill().bfill().fillna(15.0)
    df["rps"] = df["rps"].ffill().bfill().fillna(50.0)
    df["processing_time"] = df["processing_time"].ffill().bfill().fillna(0.045)
    df["cpu_usage"] = df["cpu_usage"].ffill().bfill().fillna(0.25)
    df["is_anomaly"] = df["is_anomaly"].fillna(0).astype(int)

    return df


def run_experiment(duration_minutes: int, output_csv: Path):
    log("=" * 65)
    log(f"STARTING AUTOMATED TELEMETRY COLLECTION ({duration_minutes} min)")
    log("=" * 65)

    pf_mock = None
    pf_vm = None

    try:
        # 1. Проверяем / возобновляем поды кластера
        log("Checking pod status in monitoring namespace...")
        subprocess.run(["bash", str(SCRIPT_DIR / "start.sh")], check=False)

        # 2. Автоматический проброс портов из k8s на localhost (8000 и 8428)
        pf_mock = start_port_forward("mock-service", 8000)
        pf_vm = start_port_forward("victoria-metrics", 8428)

        # Даем секунду на установление соединения
        time.sleep(2)

        if not check_health(retries=15):
            log("\033[31mFailed to connect to mock-service and VictoriaMetrics even after port-forward. Aborting.\033[0m")
            return

        log("Cluster services are healthy and scraping metrics.")
        start_time_s = time.time()
        
        # Calculate timeline:
        dur_s = duration_minutes * 60.0
        t_inc1_start = start_time_s + 0.35 * dur_s
        t_inc1_end = start_time_s + 0.50 * dur_s
        t_inc2_start = start_time_s + 0.60 * dur_s
        t_inc2_end = start_time_s + 0.75 * dur_s
        t_inc3_start = start_time_s + 0.82 * dur_s
        t_inc3_end = start_time_s + 0.94 * dur_s
        t_finish = start_time_s + dur_s

        log(f"Phase 1: Baseline normal traffic until {(t_inc1_start - start_time_s)/60:.1f}m...")
        
        inc1_active = False
        inc2_active = False
        inc3_active = False

        while time.time() < t_finish:
            now = time.time()
            # Incident 1 trigger
            if now >= t_inc1_start and now < t_inc1_end and not inc1_active:
                log("\033[33m>>> INJECTING INCIDENT 1: Latency degradation (Ramp 20s) <<<\033[0m")
                inject_chaos("latency", enable=True, ramp_seconds=20.0)
                inc1_active = True
            elif now >= t_inc1_end and inc1_active:
                log("\033[32m<<< RESOLVING INCIDENT 1: Latency recovery <<<\033[0m")
                inject_chaos("latency", enable=False, ramp_seconds=15.0)
                inc1_active = False

            # Incident 2 trigger
            if now >= t_inc2_start and now < t_inc2_end and not inc2_active:
                log("\033[33m>>> INJECTING INCIDENT 2: Cascading 5xx Error Storm <<<\033[0m")
                inject_chaos("errors", enable=True, ramp_seconds=20.0)
                inc2_active = True
            elif now >= t_inc2_end and inc2_active:
                log("\033[32m<<< RESOLVING INCIDENT 2: Errors resolved <<<\033[0m")
                inject_chaos("errors", enable=False, ramp_seconds=15.0)
                inc2_active = False

            # Incident 3 trigger
            if now >= t_inc3_start and now < t_inc3_end and not inc3_active:
                log("\033[33m>>> INJECTING INCIDENT 3: Queue saturation <<<\033[0m")
                inject_chaos("queue", enable=True, ramp_seconds=15.0)
                inc3_active = True
            elif now >= t_inc3_end and inc3_active:
                log("\033[32m<<< RESOLVING INCIDENT 3: Queue drained <<<\033[0m")
                inject_chaos("queue", enable=False, ramp_seconds=15.0)
                inc3_active = False

            time.sleep(5)

        end_time_s = time.time()
        log("Experiment timeline completed. Collecting final dataset from TSDB...")

        # Small wait for scrapers to ingest last metrics
        time.sleep(10)
        df = collect_metrics_from_vm(start_time_s, end_time_s)

        output_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_csv, index=False)
        log(f"\033[32mSuccessfully saved {len(df)} samples to {output_csv}\033[0m")
        log(f"Anomaly rate: {df['is_anomaly'].mean():.2%}")

    finally:
        # Terminate port forwards
        if pf_mock:
            pf_mock.terminate()
        if pf_vm:
            pf_vm.terminate()
        # Scale down cluster to 0 replicas to prevent credit burn!
        stop_cluster()
        log("\033[32mCluster successfully scaled to 0. Codespaces will sleep automatically after 5 min.\033[0m")


def main():
    parser = argparse.ArgumentParser(description="Automated Kubernetes Chaos Telemetry Collector")
    parser.add_argument("--duration-minutes", type=int, default=25, help="Experiment duration in minutes.")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_CSV), help="Output CSV path.")
    args = parser.parse_args()

    run_experiment(args.duration_minutes, Path(args.output))


if __name__ == "__main__":
    main()
