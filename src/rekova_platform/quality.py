"""Pre-transform data-quality gate.

Philosophy: a pipeline should *know* its defects, not hope they are absent.

- Hard errors (null business keys, negative gross on a sale) stop the run.
- Known feed defects (duplicates, missing net sales, returns, orphan SKUs, region
  whitespace, one missing extract) are quantified against the generator's baseline.
  If the count drifts, the run still continues but the report is marked WARN —
  exactly how a real team would treat a known but bounded issue.

The report is written to outputs/dq_report.json so it can be published with the run.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from .config import DB_PATH, OUTPUT_DIR

# name, severity, SQL, expected value (None = just require >= min_value), min_value
CHECKS: list[dict] = [
    {
        "name": "sellout_rows_present",
        "severity": "error",
        "sql": "SELECT count(*) FROM raw.fact_sellout_monthly",
        "expected": None,
        "min_value": 1,
        "description": "The sell-out feed is not empty.",
    },
    {
        "name": "null_business_keys",
        "severity": "error",
        "sql": """
            SELECT count(*) FROM raw.fact_sellout_monthly
            WHERE month_start IS NULL OR sku_id IS NULL OR distributor_id IS NULL
        """,
        "expected": 0,
        "description": "No null month/SKU/distributor keys.",
    },
    {
        "name": "negative_gross_on_sales",
        "severity": "error",
        "sql": """
            SELECT count(*) FROM raw.fact_sellout_monthly
            WHERE units > 0 AND gross_sales < 0
        """,
        "expected": 0,
        "description": "A positive sale cannot have negative gross value.",
    },
    {
        "name": "duplicate_rows",
        "severity": "warn",
        "sql": """
            SELECT coalesce(sum(c - 1), 0) FROM (
                SELECT count(*) AS c
                FROM raw.fact_sellout_monthly
                GROUP BY month_start, sku_id, distributor_id, units,
                         gross_sales, net_sales, promo_flag, promo_discount_pct
                HAVING count(*) > 1
            )
        """,
        "expected": 32,
        "description": "Known defect: duplicated sell-out rows to be removed in staging.",
    },
    {
        "name": "null_net_sales",
        "severity": "warn",
        "sql": "SELECT count(*) FROM raw.fact_sellout_monthly WHERE net_sales IS NULL",
        "expected": 50,
        "description": "Known defect: missing net sales to be derived from gross and channel terms.",
    },
    {
        "name": "returns_rows",
        "severity": "warn",
        "sql": "SELECT count(*) FROM raw.fact_sellout_monthly WHERE units < 0",
        "expected": 18,
        "description": "Known defect: returns mixed into the sales feed; kept in a separate model.",
    },
    {
        "name": "orphan_sku_rows",
        "severity": "warn",
        "sql": """
            SELECT count(*)
            FROM raw.fact_sellout_monthly s
            LEFT JOIN raw.dim_product p USING (sku_id)
            WHERE p.sku_id IS NULL
        """,
        "expected": 2,
        "description": "Known defect: sell-out rows pointing at unknown SKUs.",
    },
    {
        "name": "region_whitespace",
        "severity": "warn",
        "sql": """
            SELECT count(*) FROM raw.dim_distributor
            WHERE region <> trim(region)
        """,
        "expected": 3,
        "description": "Known defect: trailing spaces in distributor region names.",
    },
    {
        "name": "missing_month_extract",
        "severity": "warn",
        "sql": """
            SELECT count(*) FROM raw.fact_sellout_monthly
            WHERE distributor_id = 'GT05' AND month_start = DATE '2025-12-01'
        """,
        "expected": 0,
        "description": "Known defect: one distributor-month extract is absent (Dec 2025, GT05).",
    },
]


def run_checks(db_path: str | Path | None = None) -> dict:
    db_path = Path(db_path or DB_PATH)
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        results = []
        for check in CHECKS:
            value = con.execute(check["sql"]).fetchone()[0]
            value = int(value) if value is not None else 0
            if check["expected"] is None:
                status = "pass" if value >= check["min_value"] else "fail"
            else:
                status = "pass" if value == check["expected"] else (
                    "fail" if check["severity"] == "error" else "warn"
                )
            results.append({
                "name": check["name"],
                "severity": check["severity"],
                "status": status,
                "value": value,
                "expected": check["expected"],
                "description": check["description"],
            })

        passed = all(r["status"] != "fail" for r in results)
        report = {
            "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds"),
            "database": str(db_path),
            "passed": passed,
            "error_count": sum(1 for r in results if r["status"] == "fail"),
            "warning_count": sum(1 for r in results if r["status"] == "warn"),
            "checks": results,
        }

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "dq_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        return report
    finally:
        con.close()


def gate(db_path: str | Path | None = None) -> dict:
    """Run checks and raise if a hard error is present (used by Airflow/runner)."""
    report = run_checks(db_path)
    if not report["passed"]:
        failed = [r["name"] for r in report["checks"] if r["status"] == "fail"]
        raise RuntimeError(f"Data-quality gate failed: {', '.join(failed)}")
    return report


if __name__ == "__main__":
    rep = gate()
    print(f"Quality gate passed={rep['passed']} "
          f"warnings={rep['warning_count']}")
    for row in rep["checks"]:
        print(f"  [{row['status']:4s}] {row['name']:28s} {row['value']:>6,} "
              f"(expected {row['expected']})")
