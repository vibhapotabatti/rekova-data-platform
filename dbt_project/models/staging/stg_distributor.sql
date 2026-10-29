select
    trim(distributor_id)   as distributor_id,
    trim(distributor_name) as distributor_name,
    trim(channel_type)     as channel_type,
    trim(region)           as region,          -- fixes the trailing-space defect
    cast(city_tier as integer) as city_tier
from {{ source('raw', 'dim_distributor') }}
