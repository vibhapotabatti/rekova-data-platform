"""Rekova monthly analytics pipeline.

Orchestration only — every task calls the same code the local runner uses, so the
DAG is thin and testable. In production the repo is mounted at REKOVA_HOME
(default /opt/airflow/repo) and dbt/duckdb are installed in the Airflow image.

Task flow:
    ensure_source_data -> ingest_raw -> quality_gate
    -> dbt_build_staging -> dbt_build_marts -> dbt_test_all -> export_dashboard
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

PROJECT_ROOT = os.environ.get("REKOVA_HOME", "/opt/airflow/repo")


def _with_src_path() -> None:
    src = os.path.join(PROJECT_ROOT, "src")
    if src not in sys.path:
        sys.path.insert(0, src)


def _ingest() -> dict:
    _with_src_path()
    from rekova_platform.ingest import ingest

    return ingest()


def _quality_gate() -> dict:
    _with_src_path()
    from rekova_platform.quality import gate

    report = gate()
    return {
        "passed": report["passed"],
        "errors": report["error_count"],
        "warnings": report["warning_count"],
    }


def _export() -> dict:
    _with_src_path()
    from rekova_platform.export import export

    return export()


def _dbt_command(selection: str | None, command: str = "build") -> str:
    selector = f"--select {selection} " if selection else ""
    return (
        f"cd {PROJECT_ROOT} && dbt {command} {selector}"
        "--project-dir dbt_project --profiles-dir dbt_project"
    )


default_args = {
    "owner": "vibha",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="rekova_monthly_pipeline",
    description="Rekova CPG analytics: ingest, quality gate, dbt transforms, tests, publish",
    start_date=datetime(2026, 1, 1),
    schedule="@monthly",
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["rekova", "analytics", "production"],
) as dag:

    ensure_source = BashOperator(
        task_id="ensure_source_data",
        bash_command=f"cd {PROJECT_ROOT} && python scripts/generate_data.py",
    )

    ingest_raw = PythonOperator(
        task_id="ingest_raw",
        python_callable=_ingest,
    )

    quality_gate = PythonOperator(
        task_id="quality_gate",
        python_callable=_quality_gate,
    )

    dbt_staging = BashOperator(
        task_id="dbt_build_staging",
        bash_command=_dbt_command("staging"),
    )

    dbt_marts = BashOperator(
        task_id="dbt_build_marts",
        bash_command=_dbt_command("marts"),
    )

    dbt_test_all = BashOperator(
        task_id="dbt_test_all",
        bash_command=_dbt_command(None, command="test"),
    )

    export_dashboard = PythonOperator(
        task_id="export_dashboard",
        python_callable=_export,
    )

    (
        ensure_source
        >> ingest_raw
        >> quality_gate
        >> dbt_staging
        >> dbt_marts
        >> dbt_test_all
        >> export_dashboard
    )
