{{ config(tags=['marts']) }}

-- Cross-project reconciliation gate.
-- These are the same headline KPIs produced independently by the SQL/Power BI
-- project (23.42 Cr, 75.0%, 32.1%) and the Python project. If a transformation
-- changes business meaning, this test fails and CI stops the release.
with latest as (

    select *
    from {{ ref('mart_monthly_sales') }}
    order by month_start desc
    limit 1

),

pareto as (

    select cumulative_share_pct as top5_share_pct
    from {{ ref('mart_sku_pareto') }}
    where sku_rank = 5

)

select
    latest.net_sales / 1e7 as latest_month_cr,
    latest.ecom_share_pct,
    pareto.top5_share_pct
from latest
cross join pareto
where abs(latest.net_sales / 1e7 - 23.42) > 0.05
   or abs(latest.ecom_share_pct - 32.1) > 0.6
   or abs(pareto.top5_share_pct - 75.0) > 0.6
