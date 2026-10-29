"""Local orchestrator — the same steps the Airflow DAG runs, without Airflow.

Usage:
    python scripts/run_pipeline.py [--skip-generate]

Steps:
    1. ensure landing data exists (generate if missing)
    2. ingest CSV -> DuckDB raw schema (with load audit)
    3. Python data-quality gate (hard errors stop the run)
    4. dbt build staging (models + tests)
    5. dbt build marts   (models + tests)
    6. dbt test          (full suite, including singular business-rule tests)
    7. export CSV/Parquet marts + dashboard.html
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rekova_platform.config import DATA_DIR, DB_PATH, DBT_PROJECT_DIR, OUTPUT_DIR, SOURCE_FILES  # noqa: E402
from rekova_platform.ingest import ingest  # noqa: E402
from rekova_platform.quality import gate  # noqa: E402
from rekova_platform.export import export  # noqa: E402


def _log(message: str) -> None:
    print(f"\n== {message}", flush=True)


def _dbt_env() -> dict[str, str]:
    env = os.environ.copy()
    env["REKOVA_DB"] = str(DB_PATH)
    env["DBT_PROFILES_DIR"] = str(DBT_PROJECT_DIR)
    return env


def _run_dbt(args: list[str]) -> None:
    dbt = shutil.which("dbt")
    if not dbt:
        raise RuntimeError(
            "dbt executable not found. Install requirements first: "
            "pip install -r requirements.txt"
        )
    cmd = [
        dbt,
        *args,
        "--project-dir", str(DBT_PROJECT_DIR),
        "--profiles-dir", str(DBT_PROJECT_DIR),
    ]
    print("  $ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=PROJECT_ROOT, env=_dbt_env(), check=True)


def ensure_source_data() -> None:
    missing = [f for f in SOURCE_FILES.values() if not (DATA_DIR / f).exists()]
    if missing:
        _log("Generating synthetic landing data")
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_data.py")],
            cwd=PROJECT_ROOT,
            env=os.environ.copy(),
            check=True,
        )
    else:
        print(f"Landing data present in {DATA_DIR}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-generate", action="store_true",
                        help="Fail instead of generating if landing data is missing.")
    args = parser.parse_args()

    if args.skip_generate:
        missing = [f for f in SOURCE_FILES.values() if not (DATA_DIR / f).exists()]
        if missing:
            print(f"ERROR: missing source files: {', '.join(missing)}", file=sys.stderr)
            return 1
    else:
        ensure_source_data()

    _log("Ingesting raw CSV into DuckDB")
    counts = ingest()
    for name, count in counts.items():
        print(f"  {name:28s}{count:>8,} rows")

    _log("Running data-quality gate")
    report = gate()
    print(f"  passed={report['passed']} errors={report['error_count']} "
          f"warnings={report['warning_count']}")
    for row in report["checks"]:
        print(f"  [{row['status']:4s}] {row['name']:28s}{row['value']:>7,}")

    _log("dbt build: staging")
    _run_dbt(["build", "--select", "staging"])

    _log("dbt build: marts")
    _run_dbt(["build", "--select", "marts"])

    _log("dbt test: full suite")
    _run_dbt(["test"])

    _log("Exporting marts + dashboard")
    kpis = export()
    print(f"  latest month net sales: Rs {kpis['latest_month_net_sales_cr']} Cr")
    print(f"  LTM net sales:          Rs {kpis['ltm_net_sales_cr']} Cr")
    print(f"  top-5 SKU share:        {kpis['top5_sku_share_pct']}%")
    print(f"  e-commerce share:       {kpis['ecom_share_latest_pct']}%")

    _log("Done")
    print(f"Warehouse: {DB_PATH}")
    print(f"Outputs:   {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
