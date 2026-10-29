"""The quality gate must quantify known defects and fail only on hard errors."""
from __future__ import annotations

from rekova_platform.ingest import ingest
from rekova_platform.quality import run_checks


EXPECTED_VALUES = {
    "duplicate_rows": 32,
    "null_net_sales": 50,
    "returns_rows": 18,
    "orphan_sku_rows": 2,
    "region_whitespace": 3,
    "missing_month_extract": 0,
    "null_business_keys": 0,
    "negative_gross_on_sales": 0,
}


def test_quality_gate_matches_known_baseline(raw_dir, tmp_path):
    db = tmp_path / "quality.duckdb"
    ingest(db_path=db, data_dir=raw_dir)
    report = run_checks(db)

    assert report["passed"] is True
    assert report["error_count"] == 0
    assert report["warning_count"] == 0  # no drift from the documented baseline

    values = {check["name"]: check["value"] for check in report["checks"]}
    for name, expected in EXPECTED_VALUES.items():
        assert values[name] == expected, f"{name}: {values[name]} != {expected}"
