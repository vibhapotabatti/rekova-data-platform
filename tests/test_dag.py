"""DAG integrity — skipped when Airflow is not installed (local Windows dev)."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("airflow")

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_dag_imports_without_errors():
    from airflow.models import DagBag

    bag = DagBag(dag_folder=str(PROJECT_ROOT / "dags"), include_examples=False)
    assert not bag.import_errors, bag.import_errors
    assert "rekova_monthly_pipeline" in bag.dags

    dag = bag.dags["rekova_monthly_pipeline"]
    assert dag.schedule_interval == "@monthly"
    assert dag.catchup is False
    assert len(dag.tasks) == 7
