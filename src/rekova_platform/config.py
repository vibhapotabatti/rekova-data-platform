"""Shared paths for the Rekova platform.

Everything is overridable by environment variable so the same code runs locally,
inside Airflow containers and in CI without edits.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(os.environ.get("REKOVA_RAW_DIR", PROJECT_ROOT / "data" / "raw"))
DB_PATH = Path(os.environ.get("REKOVA_DB", PROJECT_ROOT / "warehouse" / "rekova.duckdb"))
OUTPUT_DIR = Path(os.environ.get("REKOVA_OUTPUT_DIR", PROJECT_ROOT / "outputs"))
DBT_PROJECT_DIR = PROJECT_ROOT / "dbt_project"

#: Source files expected in the landing zone -> raw table names in DuckDB.
SOURCE_FILES = {
    "dim_product": "dim_product.csv",
    "dim_distributor": "dim_distributor.csv",
    "dim_date": "dim_date.csv",
    "fact_sellout_monthly": "fact_sellout_monthly.csv",
    "fact_shipments_monthly": "fact_shipments_monthly.csv",
    "fact_retail_audit": "fact_retail_audit.csv",
    "fact_targets": "fact_targets.csv",
}
