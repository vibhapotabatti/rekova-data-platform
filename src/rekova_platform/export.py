"""Publish the marts: CSV + Parquet exports, KPI JSON and a self-contained dashboard.

No BI server required — the dashboard is a single HTML file with inline CSS and SVG,
generated from the warehouse on every pipeline run.
"""
from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import duckdb

from .config import DB_PATH, OUTPUT_DIR

MARTS = ["mart_monthly_sales", "mart_sku_pareto", "mart_promo_effectiveness"]

CSS = """
:root {
  --ink: #0f2a33; --muted: #5b6b73; --line: #e3e8ea; --paper: #f5f7f8;
  --card: #ffffff; --teal: #0f7b6c; --amber: #d97706; --red: #b42318;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--paper); color: var(--ink);
  font-family: "Segoe UI", system-ui, -apple-system, Roboto, Arial, sans-serif;
}
.wrap { max-width: 1120px; margin: 0 auto; padding: 28px 20px 48px; }
header {
  background: var(--ink); color: #fff; border-radius: 16px;
  padding: 26px 28px; display: flex; gap: 20px; align-items: flex-start;
  justify-content: space-between; flex-wrap: wrap;
}
header h1 { margin: 0 0 6px; font-size: 26px; letter-spacing: .2px; }
header p { margin: 0; color: #b9c9cd; font-size: 13.5px; }
.pill {
  border: 1px solid rgba(255,255,255,.25); border-radius: 999px;
  padding: 7px 13px; font-size: 12.5px; color: #d8f3ee; background: rgba(15,123,108,.25);
}
.grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin: 18px 0; }
.card {
  background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  padding: 16px 16px 14px;
}
.kpi .label { font-size: 11.5px; text-transform: uppercase; letter-spacing: .7px; color: var(--muted); }
.kpi .value { font-size: 25px; font-weight: 700; margin-top: 7px; font-variant-numeric: tabular-nums; }
.kpi .sub { font-size: 12px; color: var(--muted); margin-top: 4px; }
.panel { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 20px 22px; margin-top: 14px; }
.panel h2 { margin: 0 0 4px; font-size: 16px; }
.panel .hint { margin: 0 0 14px; color: var(--muted); font-size: 12.5px; }
.two { display: grid; grid-template-columns: 1.15fr .85fr; gap: 14px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; color: var(--muted); font-weight: 600; font-size: 11.5px; text-transform: uppercase; letter-spacing: .5px; padding: 8px 8px; border-bottom: 1px solid var(--line); }
td { padding: 9px 8px; border-bottom: 1px solid #f0f3f4; font-variant-numeric: tabular-nums; }
td.num, th.num { text-align: right; }
tr:last-child td { border-bottom: 0; }
.pos { color: var(--teal); font-weight: 600; }
.neg { color: var(--red); font-weight: 600; }
footer { color: var(--muted); font-size: 12px; margin-top: 18px; line-height: 1.6; }
.legend { display: flex; gap: 18px; color: var(--muted); font-size: 12px; margin-top: 6px; }
.swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
@media (max-width: 980px) { .grid { grid-template-columns: repeat(3, 1fr); } .two { grid-template-columns: 1fr; } }
@media (max-width: 560px) { .grid { grid-template-columns: repeat(2, 1fr); } }
"""


def _query(con: duckdb.DuckDBPyConnection, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = []
    for row in cur.fetchall():
        rows.append({
            col: (float(value) if isinstance(value, Decimal) else value)
            for col, value in zip(cols, row)
        })
    return rows


def _cr(value: float) -> str:
    return f"{value / 1e7:,.2f}"


def _nice_top(max_value: float, ticks: int = 6) -> float:
    """Round a chart maximum up to a clean 1/2/2.5/5 × 10^k scale."""
    raw = max_value / ticks
    magnitude = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    step = 10 * magnitude
    for multiplier in (1, 2, 2.5, 5, 10):
        if raw <= multiplier * magnitude:
            step = multiplier * magnitude
            break
    return step * ticks


def _svg_chart(monthly: list[dict]) -> str:
    width, height = 1040, 310
    left, right, top, bottom = 58, 26, 24, 46
    plot_w, plot_h = width - left - right, height - top - bottom
    n = len(monthly)
    step = plot_w / n
    bar_w = step * 0.62
    values = [m["net_sales"] / 1e7 for m in monthly]
    targets = [(m["target_net_sales"] or 0) / 1e7 for m in monthly]
    max_v = _nice_top(max(max(values), max(targets)) * 1.05)
    ticks = 6

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="Monthly net sales versus target">']
    for i in range(ticks + 1):
        v = max_v * i / ticks
        y = top + plot_h * (1 - i / ticks)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="#e8edef" stroke-width="1"/>')
        parts.append(f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="10.5" fill="#7a8a91">{v:,.0f}</text>')

    for i, (m, v) in enumerate(zip(monthly, values)):
        x = left + i * step + (step - bar_w) / 2
        y = top + plot_h * (1 - v / max_v)
        label = m["month_start"].strftime("%b %y")
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{top + plot_h - y:.1f}" '
            f'rx="2.5" fill="#0f7b6c"><title>{label}: Rs {v:,.2f} Cr</title></rect>'
        )
        if i % 3 == 0 or i == n - 1:
            parts.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{height - bottom + 18}" text-anchor="middle" '
                f'font-size="10.5" fill="#7a8a91">{label}</text>'
            )

    pts = []
    for i, t in enumerate(targets):
        x = left + i * step + step / 2
        y = top + plot_h * (1 - t / max_v)
        pts.append(f"{x:.1f},{y:.1f}")
    parts.append(
        f'<polyline points="{" ".join(pts)}" fill="none" stroke="#d97706" '
        f'stroke-width="2" stroke-dasharray="5 4" stroke-linejoin="round"/>'
    )
    parts.append("</svg>")
    return "".join(parts)


def _status_class(value: float) -> str:
    return "pos" if value >= 0 else "neg"


def _fmt_pct(value: float, signed: bool = False) -> str:
    return f"{value:+.1f}%" if signed else f"{value:.1f}%"


def export(db_path: str | Path | None = None,
           output_dir: str | Path | None = None) -> dict:
    db_path = Path(db_path or DB_PATH)
    output_dir = Path(output_dir or OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        # ---- machine-readable exports -------------------------------------
        for mart in MARTS:
            csv_path = output_dir / f"{mart}.csv"
            pq_path = output_dir / f"{mart}.parquet"
            con.execute(
                f"COPY (SELECT * FROM marts.{mart}) TO '{str(csv_path).replace(chr(39), chr(39) * 2)}' "
                "(HEADER, DELIMITER ',')"
            )
            con.execute(
                f"COPY (SELECT * FROM marts.{mart}) TO '{str(pq_path).replace(chr(39), chr(39) * 2)}' "
                "(FORMAT PARQUET)"
            )

        monthly = _query(con, "SELECT * FROM marts.mart_monthly_sales ORDER BY month_start")
        pareto = _query(con, "SELECT * FROM marts.mart_sku_pareto ORDER BY sku_rank")
        promo = _query(
            con,
            "SELECT * FROM marts.mart_promo_effectiveness ORDER BY uplift_pct DESC",
        )
        clean_rows = con.execute("SELECT count(*) FROM marts.fct_sellout").fetchone()[0]

        latest = monthly[-1]
        ltm_rows = monthly[-12:]
        ltm_sales = sum(r["net_sales"] for r in ltm_rows)
        top5 = next((r["cumulative_share_pct"] for r in pareto if r["sku_rank"] == 5), None)

        dq_path = output_dir / "dq_report.json"
        dq = json.loads(dq_path.read_text(encoding="utf-8")) if dq_path.exists() else None

        kpis = {
            "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds"),
            "latest_month": latest["month_start"].isoformat(),
            "latest_month_net_sales_cr": round(latest["net_sales"] / 1e7, 2),
            "ltm_net_sales_cr": round(ltm_sales / 1e7, 2),
            "latest_abs_pct": round(latest["abs_pct"], 1),
            "ecom_share_latest_pct": round(latest["ecom_share_pct"], 1),
            "top5_sku_share_pct": round(top5, 1) if top5 is not None else None,
            "clean_sellout_rows": int(clean_rows),
            "dq_passed": dq["passed"] if dq else None,
            "dq_errors": dq["error_count"] if dq else None,
            "dq_warnings": dq["warning_count"] if dq else None,
            "dq_checks_total": len(dq["checks"]) if dq else None,
            "dq_checks_passed": (
                sum(1 for c in dq["checks"] if c["status"] == "pass") if dq else None
            ),
        }
        (output_dir / "kpi_summary.json").write_text(
            json.dumps(kpis, indent=2), encoding="utf-8"
        )

        # ---- dashboard ----------------------------------------------------
        chart = _svg_chart(monthly)
        top_skus = pareto[:6]
        top_promo = promo[:6]
        dq_pill = "DQ gate: PASSED" if (dq and dq["passed"]) else "DQ gate: CHECK"
        gen_ts = kpis["generated_at"].replace("T", " ")[:16]

        sku_rows = "".join(
            f"<tr><td>{r['sku_rank']}</td><td>{html.escape(r['sku_name'])}</td>"
            f"<td>{html.escape(r['brand'])}</td>"
            f"<td class='num'>₹{_cr(r['ltm_net_sales'])} Cr</td>"
            f"<td class='num'>{_fmt_pct(r['share_pct'])}</td>"
            f"<td class='num'>{_fmt_pct(r['cumulative_share_pct'])}</td></tr>"
            for r in top_skus
        )
        promo_rows = "".join(
            f"<tr><td>{html.escape(r['brand'])}</td><td>{html.escape(r['channel_type'])}</td>"
            f"<td class='num pos'>{_fmt_pct(r['uplift_pct'], signed=True)}</td>"
            f"<td class='num'>{r['promo_rows']}</td></tr>"
            for r in top_promo
        )

        dashboard = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Rekova Sales Command Center</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>Rekova Sales Command Center</h1>
      <p>Automated by Airflow + dbt + DuckDB · simulated client, synthetic data · generated {gen_ts} UTC</p>
    </div>
    <span class="pill">{dq_pill}</span>
  </header>

  <div class="grid">
    <div class="card kpi"><div class="label">Latest month</div>
      <div class="value">₹{kpis['latest_month_net_sales_cr']:,.2f} Cr</div>
      <div class="sub">{latest['month_start'].strftime('%b %Y')} net sales</div></div>
    <div class="card kpi"><div class="label">Last 12 months</div>
      <div class="value">₹{kpis['ltm_net_sales_cr']:,.1f} Cr</div>
      <div class="sub">rolling net sales</div></div>
    <div class="card kpi"><div class="label">Sales vs target</div>
      <div class="value {_status_class(latest['abs_pct'])}">{_fmt_pct(latest['abs_pct'], signed=True)}</div>
      <div class="sub">latest month (ABS %)</div></div>
    <div class="card kpi"><div class="label">Top-5 SKU share</div>
      <div class="value">{_fmt_pct(kpis['top5_sku_share_pct'])}</div>
      <div class="sub">of LTM net sales</div></div>
    <div class="card kpi"><div class="label">E-commerce share</div>
      <div class="value">{_fmt_pct(kpis['ecom_share_latest_pct'])}</div>
      <div class="sub">latest month</div></div>
    <div class="card kpi"><div class="label">Quality gate</div>
      <div class="value">{kpis['dq_checks_passed']}/{kpis['dq_checks_total']} checks</div>
      <div class="sub">{kpis['dq_errors']} errors · {kpis['clean_sellout_rows']:,} clean rows</div></div>
  </div>

  <div class="panel">
    <h2>Monthly net sales vs target</h2>
    <p class="hint">Net sales in ₹ Cr. Target line is the sum of the FP&amp;A feed at region × channel grain.</p>
    {chart}
    <div class="legend">
      <span><span class="swatch" style="background:#0f7b6c"></span>Net sales</span>
      <span><span class="swatch" style="background:#d97706"></span>Target</span>
    </div>
  </div>

  <div class="two">
    <div class="panel">
      <h2>Top SKUs — last 12 months</h2>
      <p class="hint">Pareto concentration: the first five SKUs carry most of the revenue.</p>
      <table>
        <thead><tr><th>#</th><th>SKU</th><th>Brand</th><th class="num">LTM sales</th><th class="num">Share</th><th class="num">Cumulative</th></tr></thead>
        <tbody>{sku_rows}</tbody>
      </table>
    </div>
    <div class="panel">
      <h2>Promo uplift — brand × channel</h2>
      <p class="hint">Promo months vs base months, last 12 months. Descriptive, not causal.</p>
      <table>
        <thead><tr><th>Brand</th><th>Channel</th><th class="num">Uplift</th><th class="num">Promo rows</th></tr></thead>
        <tbody>{promo_rows}</tbody>
      </table>
    </div>
  </div>

  <footer>
    Generated from <code>marts</code> on every pipeline run. Export formats:
    <code>mart_monthly_sales</code>, <code>mart_sku_pareto</code>,
    <code>mart_promo_effectiveness</code> as CSV and Parquet.
    Client, brands and figures are fictional; no employer data is used.
  </footer>
</div>
</body>
</html>"""
        (output_dir / "dashboard.html").write_text(dashboard, encoding="utf-8")
        return kpis
    finally:
        con.close()


if __name__ == "__main__":
    kpis = export()
    print(json.dumps(kpis, indent=2))
