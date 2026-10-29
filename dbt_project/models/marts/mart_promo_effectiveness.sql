with latest as (

    select max(month_start) as max_month
    from {{ ref('fct_sellout') }}

),

windowed as (

    select
        f.brand,
        f.channel_type,
        f.units,
        f.promo_flag
    from (
        select s.*, p.brand
        from {{ ref('fct_sellout') }} s
        inner join {{ ref('dim_product') }} p using (sku_id)
    ) f
    cross join latest
    where f.month_start >= latest.max_month - interval '11 months'

),

agg as (

    select
        brand,
        channel_type,
        count(*) filter (where promo_flag = 1) as promo_rows,
        count(*) filter (where promo_flag = 0) as base_rows,
        avg(units) filter (where promo_flag = 1) as promo_avg_units,
        avg(units) filter (where promo_flag = 0) as base_avg_units
    from windowed
    group by 1, 2

)

select
    brand,
    channel_type,
    cast(round(promo_avg_units) as integer) as promo_avg_units,
    cast(round(base_avg_units) as integer)  as base_avg_units,
    round((promo_avg_units / nullif(base_avg_units, 0) - 1) * 100, 1) as uplift_pct,
    promo_rows,
    base_rows
from agg
where promo_rows >= 5
  and base_rows >= 20
order by uplift_pct desc
