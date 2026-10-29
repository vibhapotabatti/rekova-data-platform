select
    cast(month_start as date)  as month_start,
    trim(region)               as region,
    trim(channel_type)         as channel_type,
    cast(target_net_sales as decimal(18, 2)) as target_net_sales
from {{ source('raw', 'fact_targets') }}
