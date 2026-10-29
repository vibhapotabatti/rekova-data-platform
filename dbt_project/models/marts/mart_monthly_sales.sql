with sales as (

    select
        month_start,
        sum(net_sales)                                    as net_sales,
        sum(units)                                        as units,
        sum(case when promo_flag = 1 then units else 0 end) as promo_units
    from {{ ref('fct_sellout') }}
    group by 1

),

targets as (

    select
        month_start,
        sum(target_net_sales) as target_net_sales
    from {{ ref('fct_targets') }}
    group by 1

),

ecom as (

    select
        month_start,
        sum(net_sales) as ecom_net_sales
    from {{ ref('fct_sellout') }}
    where channel_type = 'E-commerce'
    group by 1

)

select
    s.month_start,
    s.net_sales,
    s.units,
    round(s.promo_units / nullif(s.units, 0) * 100, 2)        as promo_unit_share_pct,
    t.target_net_sales,
    round((s.net_sales / nullif(t.target_net_sales, 0) - 1) * 100, 2) as abs_pct,
    round(coalesce(e.ecom_net_sales, 0) / nullif(s.net_sales, 0) * 100, 2) as ecom_share_pct
from sales s
left join targets t using (month_start)
left join ecom e using (month_start)
order by s.month_start
