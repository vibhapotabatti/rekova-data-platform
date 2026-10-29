select
    s.month_start,
    s.sku_id,
    s.distributor_id,
    d.region,
    d.channel_type,
    s.units,
    s.gross_sales,
    s.net_sales,
    s.promo_flag,
    s.promo_discount_pct
from {{ ref('stg_sellout') }} s
inner join {{ ref('dim_product') }} p using (sku_id)
inner join {{ ref('dim_distributor') }} d using (distributor_id)
