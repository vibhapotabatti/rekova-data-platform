with source as (

    select * from {{ source('raw', 'fact_shipments_monthly') }}

),

deduped as (

    select
        *,
        row_number() over (
            partition by month_start, sku_id, distributor_id, units_shipped
            order by month_start
        ) as rn
    from source

)

select
    cast(month_start as date)  as month_start,
    trim(sku_id)               as sku_id,
    trim(distributor_id)       as distributor_id,
    cast(units_shipped as integer) as units_shipped
from deduped
where rn = 1
  and units_shipped > 0
