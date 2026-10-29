"""Ingestion loads every expected table and records a load audit."""
from __future__ import annotations

import duckdb

from rekova_platform.ingest import ingest


EXPECTED_ROWS = {
    "dim_product": 12,
    "dim_distributor": 27,
    "dim_date": 24,
    "fact_sellout_monthly": 7094,
    "fact_shipments_monthly": 7056,
    "fact_retail_audit": 576,
    "fact_targets": 312,
}


def test_ingest_loads_expected_row_counts(raw_dir, tmp_path):
    db = tmp_path / "ingest.duckdb"
    counts = ingest(db_path=db, data_dir=raw_dir)
    assert counts == EXPECTED_ROWS

    con = duckdb.connect(str(db), read_only=True)
    try:
        audit_rows = con.execute("select count(*) from raw.load_audit").fetchone()[0]
        assert audit_rows == len(EXPECTED_ROWS)
        assert con.execute("select count(*) from raw.fact_sellout_monthly").fetchone()[0] == 7094
    finally:
        con.close()


def test_ingest_is_idempotent(raw_dir, tmp_path):
    db = tmp_path / "idempotent.duckdb"
    first = ingest(db_path=db, data_dir=raw_dir)
    second = ingest(db_path=db, data_dir=raw_dir)
    assert first == second

    con = duckdb.connect(str(db), read_only=True)
    try:
        assert con.execute("select count(*) from raw.load_audit").fetchone()[0] == 7
    finally:
        con.close()
