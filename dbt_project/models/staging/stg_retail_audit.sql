select
    cast(month_start as date) as month_start,
    trim(category)            as category,
    trim(brand)               as brand,
    trim(manufacturer)        as manufacturer,
    cast(value_share_pct as decimal(8, 2))       as value_share_pct,
    cast(category_value_mn_inr as decimal(18, 2)) as category_value_mn_inr
from {{ source('raw', 'fact_retail_audit') }}
