# Architecture — Rekova Data Platform

## 1. Context

The Rekova portfolio simulates a CPG client with 24 months of sell-out, sell-in,
retail-audit and target data. Projects 1 and 2 answered *what happened* and *what happens
next* using SQL, Power BI and Python. This project answers the engineering question:

> Can the analysis be rerun every month, by a scheduler, with tests that stop a bad
> release before a stakeholder sees it?

Everything is synthetic and seeded. No employer data, credentials or client information
is used anywhere in the repository.

## 2. Layers

| Layer | Schema | Materialization | Responsibility |
|---|---|---|---|
| Landing | `raw` | tables | Byte-for-byte CSV load plus `raw.load_audit` (row count + SHA-256) |
| Staging | `staging` | views | Dedupe, type casting, trim regions, derive missing net sales, split returns |
| Marts | `marts` | tables | Star-schema dimensions/facts and three business marts |
| Publish | `outputs/` | files | CSV + Parquet for BI, KPI JSON and a self-contained HTML dashboard |

The raw layer intentionally preserves defects. Staging is the only place allowed to fix
them, and dbt tests prove the fixes at the correct grain.

### Star schema

- `dim_product` — 12 SKUs, brand, category, pack, MRP
- `dim_distributor` — 27 distributors, channel, region, city tier
- `dim_date` — 24 months, month key, quarter
- `fct_sellout` — SKU × distributor × month; clean units, gross, net, promo flags
- `fct_shipments` — SKU × distributor × month; sell-in units
- `fct_targets` — region × channel × month; FP&A targets
- `fct_retail_audit` — category × brand × month; market share
- `stg_returns` — 18 return rows, deliberately outside the sales fact

`fct_sellout` and `fct_targets` both carry `region`/`channel_type` so every measure can be
filtered consistently — the same design decision documented in the Power BI project.

## 3. Data flow

```
generator (seeded, 6 defects)
   → CSV landing zone
   → ingest (DuckDB raw + audit)
   → Python quality gate (hard errors fail)
   → dbt staging (views) + schema tests
   → dbt marts (tables) + schema tests + singular business rules
   → dbt test (full suite)
   → export (CSV, Parquet, KPI JSON, dashboard.html)
```

## 4. Orchestration

The Airflow DAG (`dags/rekova_pipeline.py`) is scheduled monthly with `catchup=False` and
`max_active_runs=1`. Each task is idempotent:

- **Ingest** replaces raw tables and rebuilds the load audit.
- **dbt** rebuilds views/tables from source, so retries cannot double-count.
- **Export** overwrites files.

Retries are set to 2 with a 5-minute delay. The quality gate is a separate task so a
failure is attributable: bad source data stops the run before dbt burns time on models.

Local development uses `scripts/run_pipeline.py`, which executes exactly the same code
paths without the scheduler. This avoids a common portfolio trap: an "Airflow project"
that cannot run outside Airflow.

## 5. Quality strategy

Two kinds of checks, deliberately separated:

1. **Hard errors** — null business keys, negative gross on a sale, negative units in the
   sales fact. These fail the pipeline.
2. **Baselined defects** — duplicates (32), missing net sales (50), returns (18), orphan
   SKUs (2), whitespace regions (3) and the missing GT05 December extract. The gate
   asserts the baseline. Any drift is reported; the staging layer is expected to handle
   the known cases.

Post-transform tests are stricter than the source:

- uniqueness at SKU × distributor × month
- net sales between 0 and gross sales
- target uniqueness at region × channel × month
- no orphan keys after the star-schema joins
- returns count fixed at 18
- revenue, top-5 share and e-commerce share must reconcile to the independent SQL/Python
  projects within tolerance

The last test is the most valuable: it catches semantic drift, not just SQL syntax errors.

## 6. Testing pyramid

| Level | Where | What |
|---|---|---|
| Unit / contract | `tests/test_generator.py` | seeded output is byte-identical across runs |
| Integration | `tests/test_ingest.py` | raw row counts, audit, idempotent reload |
| Quality | `tests/test_quality.py` | defect baseline and gate status |
| End-to-end | `tests/test_marts.py` | built warehouse KPIs and published artifacts |
| DAG integrity | `tests/test_dag.py` | DAG imports, schedule, task count (skipped without Airflow) |
| Warehouse tests | `dbt_project/tests` + YAML | 54 dbt tests at model grain |

CI runs the pipeline and then pytest on a clean Ubuntu runner, so a fresh clone is the
test environment — not a developer's warm warehouse.

## 7. CI/CD

`.github/workflows/ci.yml`:

1. install Python 3.11 + dbt-duckdb
2. regenerate synthetic data
3. run ingest → quality gate → dbt build → dbt test → export
4. run pytest
5. upload `outputs/` as a build artifact

There are no secrets. A production version would add a deployment job (MWAA/Composer
DAG sync, dbt Cloud job trigger, Power BI dataset refresh) behind an environment approval.

## 8. Production mapping

| Local | Production equivalent |
|---|---|
| DuckDB file | Snowflake / BigQuery / Databricks SQL warehouse |
| dbt-duckdb | dbt-snowflake / dbt-bigquery |
| Airflow in Docker | MWAA / Cloud Composer / Astronomer |
| CSV landing zone | S3 / ADLS / GCS with source freshness checks |
| `outputs/*.parquet` | BI extracts or direct warehouse connection |
| pytest + dbt tests | same, plus contract tests and anomaly detection |

The SQL is ANSI-style; the only DuckDB-specific pieces are the profile and a few date
functions. Porting is a profile change plus a review of date/interval syntax.

## 9. Limitations

- Static 24-month dataset; no late-arriving data or schema evolution.
- Full-refresh models; at scale the facts should be incremental on month partitions.
- Promo uplift remains descriptive (promotions are not randomized).
- Docker Compose is a reference deployment; CI does not run Airflow (image build cost).
- The dashboard is intentionally simple: it proves the publish step, not front-end skill.
