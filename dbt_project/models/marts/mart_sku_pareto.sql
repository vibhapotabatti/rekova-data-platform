with latest as (

    select max(month_start) as max_month
    from {{ ref('fct_sellout') }}

),

sales as (

    select
        f.sku_id,
        sum(f.net_sales) as ltm_net_sales
    from {{ ref('fct_sellout') }} f
    cross join latest
    where f.month_start >= latest.max_month - interval '11 months'
    group by 1

),

ranked as (

    select
        s.sku_id,
        p.sku_name,
        p.brand,
        p.category,
        s.ltm_net_sales,
        row_number() over (order by s.ltm_net_sales desc) as sku_rank,
        s.ltm_net_sales / sum(s.ltm_net_sales) over () * 100 as share_pct
    from sales s
    inner join {{ ref('dim_product') }} p using (sku_id)

)

select
    sku_rank,
    sku_id,
    sku_name,
    brand,
    category,
    round(ltm_net_sales, 2) as ltm_net_sales,
    round(share_pct, 2)     as share_pct,
    round(
        sum(share_pct) over (
            order by sku_rank
            rows between unbounded preceding and current row
        ),
        2
    ) as cumulative_share_pct
from ranked
order by sku_rank
