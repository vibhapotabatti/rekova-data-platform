with source as (

    select * from {{ source('raw', 'fact_sellout_monthly') }}
    where units < 0

),

deduped as (

    select
        *,
        row_number() over (
            partition by month_start, sku_id, distributor_id, units,
                         gross_sales, net_sales, promo_flag, promo_discount_pct
            order by month_start
        ) as rn
    from source

)

select
    cast(r.month_start as date)        as month_start,
    trim(r.sku_id)                     as sku_id,
    trim(r.distributor_id)             as distributor_id,
    d.channel_type,
    d.region,
    cast(r.units as integer)           as units,
    cast(r.gross_sales as decimal(18, 2)) as gross_sales,
    cast(r.net_sales as decimal(18, 2))   as net_sales
from deduped r
left join {{ ref('stg_distributor') }} d using (distributor_id)
where r.rn = 1
