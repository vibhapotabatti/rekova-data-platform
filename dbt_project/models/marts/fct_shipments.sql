select
    s.month_start,
    s.sku_id,
    s.distributor_id,
    d.region,
    d.channel_type,
    s.units_shipped
from {{ ref('stg_shipments') }} s
inner join {{ ref('dim_product') }} p using (sku_id)
inner join {{ ref('dim_distributor') }} d using (distributor_id)
