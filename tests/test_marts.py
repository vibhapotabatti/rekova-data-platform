"""End-to-end assertions against the built warehouse and published outputs."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb


def _scalar(db: Path, sql: str):
    con = duckdb.connect(str(db), read_only=True)
    try:
        return con.execute(sql).fetchone()[0]
    finally:
        con.close()


def test_clean_fact_row_count(built):
    assert _scalar(built["db"], "select count(*) from marts.fct_sellout") == 7042


def test_monthly_mart_covers_24_months(built):
    assert _scalar(built["db"], "select count(*) from marts.mart_monthly_sales") == 24


def test_latest_month_kpis(built):
    latest = _scalar(
        built["db"],
        "select net_sales / 1e7 from marts.mart_monthly_sales "
        "order by month_start desc limit 1",
    )
    assert abs(latest - 23.42) < 0.05


def test_ltm_net_sales(built):
    ltm = _scalar(
        built["db"],
        "select sum(net_sales) / 1e7 from ("
        "  select net_sales from marts.mart_monthly_sales "
        "  order by month_start desc limit 12"
        ")",
    )
    assert abs(ltm - 249.32) < 0.5


def test_top5_sku_share(built):
    share = _scalar(
        built["db"],
        "select cumulative_share_pct from marts.mart_sku_pareto where sku_rank = 5",
    )
    assert abs(share - 75.0) < 0.6


def test_ecommerce_share(built):
    share = _scalar(
        built["db"],
        "select ecom_share_pct from marts.mart_monthly_sales "
        "order by month_start desc limit 1",
    )
    assert abs(share - 32.1) < 0.6


def test_top_promo_uplift(built):
    row = _scalar(
        built["db"],
        "select uplift_pct from marts.mart_promo_effectiveness "
        "order by uplift_pct desc limit 1",
    )
    assert abs(row - 57.8) < 0.3


def test_published_outputs_exist(built):
    out = built["out"]
    for name in [
        "dashboard.html",
        "kpi_summary.json",
        "dq_report.json",
        "mart_monthly_sales.csv",
        "mart_monthly_sales.parquet",
        "mart_sku_pareto.csv",
        "mart_promo_effectiveness.csv",
    ]:
        assert (out / name).exists(), name

    kpis = json.loads((out / "kpi_summary.json").read_text(encoding="utf-8"))
    assert kpis["dq_passed"] is True
    assert kpis["clean_sellout_rows"] == 7042
    assert kpis["top5_sku_share_pct"] == 75.0
