# Project 3 — Interview Notes & Resume Framing

> Same honesty rules as Projects 1 and 2: Rekova is fictional, the data is synthetic and
> this is portfolio work. Never claim it was delivered to a client. The value is the
> engineering reasoning, not the logo.

## The 60-second walkthrough

> "I took the simulated CPG dataset from my SQL and forecasting projects and turned it
> into a scheduled pipeline. CSV lands in a raw schema with a load audit; a Python quality
> gate quantifies the six known feed defects and blocks the run on null keys or impossible
> amounts; dbt staging dedupes, types and derives missing net sales; dbt marts build a star
> schema plus monthly, Pareto and promo marts. Airflow orchestrates it monthly with retries,
> and dbt tests run at every layer — including a reconciliation test that asserts the
> warehouse still matches the ₹23.42 Cr latest-month revenue, 75% top-5 share and 32.1%
> e-commerce share from the other two projects. CI rebuilds everything from scratch on
> every push, runs pytest, and uploads the dashboard and Parquet exports."

## Defense Q&A

1. **Why Airflow if the pipeline is small?**
   The point is the contract: schedule, retries, task-level failure, backfills and
   observability. A cron job with a Python script has none of those. The DAG is thin
   because the logic lives in testable modules.

2. **Why DuckDB?**
   A real columnar warehouse with zero infrastructure. It runs identically on a laptop
   and in CI. At production scale I would move to Snowflake/BigQuery; the dbt models and
   tests would port with a profile change.

3. **Why not do everything in one Python script?**
   Then the transformation logic is untestable at layer boundaries and invisible to SQL
   reviewers. dbt gives versioned SQL, lineage, documentation and tests declared next to
   the models.

4. **How do you handle the dirty data?**
   I don't hide it. The raw layer keeps the defects; the quality gate asserts the known
   baseline; staging applies explicit fixes; tests prove the result. A new defect type
   causes a drift warning; a broken key or impossible amount fails the run.

5. **Why full refresh instead of incremental?**
   At 7k rows and 24 months, incremental adds complexity without value. At scale I would
   partition facts by month, use `is_incremental()` with a late-arrival window, and test
   idempotency on reruns.

6. **How do you know the pipeline didn't change the business meaning?**
   `assert_kpi_reconciliation` compares warehouse outputs to numbers produced
   independently by the SQL project and the Python project. Same data, different engines,
   same answer within tolerance. That is a regression test for semantics, not syntax.

7. **What happens when a task fails?**
   Airflow retries twice, then marks the task failed and stops downstream tasks. Because
   every step is idempotent, a rerun after a fix is safe. The quality gate fails before
   dbt, so bad source data does not produce a half-published mart.

8. **How is the DAG tested?**
   Locally, the same code runs through `scripts/run_pipeline.py`; pytest covers generator,
   ingest, quality and marts. The DAG integrity test runs when Airflow is installed
   (skipped on the Windows dev box). In CI, the pipeline itself is the integration test.

9. **Where are secrets and PII?**
   None. Synthetic data, no credentials in the repo, DuckDB local file. In production I
   would use Airflow connections backed by a secrets backend, and keep PII out of the
   analytics zone entirely.

10. **What would you monitor in production?**
    Source freshness, row-count deltas, revenue reconciliation, dbt test failures and
    runtime. Alert on drift, not just failure — a pipeline that runs green with 40% fewer
    rows is still an incident.

## Resume bullets (pick 2–3)

> **Analytics Data Platform (Airflow, dbt, DuckDB, Python)** — Built a scheduled ELT
> pipeline for a simulated CPG client: CSV ingestion with load audit, a Python
> data-quality gate, dbt staging/marts with 54 tests, and automated CSV/Parquet/HTML
> publishing; orchestrated monthly in Airflow with retries and task-level gating.

> **Data Quality & Reconciliation** — Quantified six known feed defects (duplicates,
> missing net sales, returns, orphan keys, whitespace, missing extract); enforced hard
> failures on key/amount errors and added a cross-project reconciliation test that keeps
> warehouse KPIs aligned with independent SQL and Python implementations.

> **CI/CD for Analytics** — GitHub Actions rebuilds the warehouse from a seeded source on
> every push, runs dbt build/test plus 12 pytest checks, and publishes dashboard artifacts;
> the same code runs locally, in Docker Airflow and in CI without modification.

## LinkedIn angle

- "A green pipeline is not the same as a correct pipeline — here's the reconciliation test
  I added so dbt can't silently change what revenue means."
- "I kept the dirty data on purpose. A quality gate that asserts the known defects is more
  useful than a clean CSV that hides them."
- "Why my Airflow DAG is boring: all the logic lives in modules I can test without a
  scheduler."

## What not to claim

- Not real client delivery, not Reckitt/Infosys work, no production traffic.
- Do not imply the 54 dbt tests cover real-world scale; they cover this synthetic dataset.
- Do not call the promo analysis causal.
