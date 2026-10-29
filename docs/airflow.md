# Running the Airflow DAG

Airflow does not officially support Windows, so this repository has two execution paths:

| Path | Use case | Command |
|---|---|---|
| Local runner | Windows dev, CI, quick verification | `python scripts/run_pipeline.py` |
| Airflow (Docker) | Scheduler, retries, backfills, UI | `docker compose -f docker-compose.airflow.yml up -d` |

Both execute the same ingestion, quality, dbt and export code. The DAG only adds
orchestration.

## Local runner

```powershell
pip install -r requirements.txt
python scripts\generate_data.py
python scripts\run_pipeline.py
```

It performs, in order:

1. `ingest` → DuckDB `raw` schema + `raw.load_audit`
2. quality gate → `outputs/dq_report.json`
3. `dbt build --select staging`
4. `dbt build --select marts`
5. `dbt test` (full suite)
6. export → CSV, Parquet, KPI JSON, `dashboard.html`

## Docker Compose

Prerequisites: Docker Desktop with at least 4 GB allocated.

```bash
# one-time metadata DB migration + admin user
docker compose -f docker-compose.airflow.yml up airflow-init

# start webserver + scheduler
docker compose -f docker-compose.airflow.yml up -d
```

- UI: <http://localhost:8080>
- Login: `admin` / `admin`
- DAG: `rekova_monthly_pipeline` (unpaused by the compose config)

The official Airflow image installs `duckdb`, `dbt-core` and `dbt-duckdb` at startup via
`_PIP_ADDITIONAL_REQUIREMENTS`. That is convenient for a demo but slow; a production image
should bake the dependencies in a Dockerfile.

The repository is mounted at `/opt/airflow/repo`, the DAG folder at `/opt/airflow/dags`.
`REKOVA_HOME`, `REKOVA_DB` and `PYTHONPATH` are set in the compose environment.

## DAG structure

```
ensure_source_data  (regenerate seeded CSVs — replace with a real extract in production)
      ↓
ingest_raw          (PythonOperator → raw schema + audit)
      ↓
quality_gate        (PythonOperator → hard errors stop the run)
      ↓
dbt_build_staging   (dbt build --select staging)
      ↓
dbt_build_marts     (dbt build --select marts)
      ↓
dbt_test_all        (dbt test)
      ↓
export_dashboard    (PythonOperator → CSV/Parquet/HTML)
```

Configuration:

- schedule `@monthly`, `catchup=False`, `max_active_runs=1`
- 2 retries with a 5-minute delay
- `start_date=2026-01-01` (adjust before enabling in a real environment)
- tags: `rekova`, `analytics`, `production`

## Production notes

- Replace `ensure_source_data` with a sensor/operator for the real landing bucket.
- Use `MWAA`, `Cloud Composer` or `Astronomer` rather than self-managed Airflow.
- Store connections in a secrets backend; nothing sensitive belongs in the repo.
- Bake Python dependencies into the image; do not use `_PIP_ADDITIONAL_REQUIREMENTS`.
- Configure remote logging (S3/GCS) and alerting (Slack/PagerDuty) on task failure.
- For larger data, switch the facts to incremental models and add source freshness SLAs.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `dbt: command not found` | `pip install -r requirements.txt`; ensure the Python Scripts dir is on PATH |
| `Missing source files` | run `python scripts\generate_data.py` or set `REKOVA_RAW_DIR` |
| DAG not visible | confirm `dags/` is mounted and check `airflow dags list-import-errors` |
| Permission errors in Docker | set `AIRFLOW_UID` (`echo $UID` on Linux/macOS) |
| DuckDB file locked | stop the scheduler/webserver before running the local pipeline |
