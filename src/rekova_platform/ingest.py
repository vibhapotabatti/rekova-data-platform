"""Load the landing CSVs into DuckDB's raw schema with a load audit.

Idempotent by design: each table is replaced and the audit is rebuilt. That makes
reruns safe in Airflow retries and in CI.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from .config import DATA_DIR, DB_PATH, SOURCE_FILES


def ingest(db_path: str | Path | None = None,
           data_dir: str | Path | None = None) -> dict[str, int]:
    """Create/replace raw.* tables from the source CSVs. Returns row counts."""
    db_path = Path(db_path or DB_PATH)
    data_dir = Path(data_dir or DATA_DIR)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    missing = [name for name in SOURCE_FILES.values() if not (data_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing source files in {data_dir}: {', '.join(missing)}. "
            "Run `python scripts/generate_data.py` first."
        )

    con = duckdb.connect(str(db_path))
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.execute("DROP TABLE IF EXISTS raw.load_audit")
        con.execute(
            """
            CREATE TABLE raw.load_audit (
                table_name   VARCHAR,
                source_file  VARCHAR,
                row_count    BIGINT,
                sha256       VARCHAR,
                loaded_at    TIMESTAMP
            )
            """
        )

        summary: dict[str, int] = {}
        loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)
        for table, filename in SOURCE_FILES.items():
            path = data_dir / filename
            con.execute(
                f"CREATE OR REPLACE TABLE raw.{table} AS "
                "SELECT * FROM read_csv_auto(?)",
                [str(path)],
            )
            rows = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            con.execute(
                "INSERT INTO raw.load_audit VALUES (?, ?, ?, ?, ?)",
                [table, filename, rows, digest, loaded_at],
            )
            summary[table] = int(rows)
        return summary
    finally:
        con.close()


if __name__ == "__main__":
    counts = ingest()
    print(f"Loaded into {DB_PATH}")
    for name, count in counts.items():
        print(f"  {name:28s}{count:>8,} rows")
