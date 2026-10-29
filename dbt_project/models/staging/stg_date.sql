select
    cast(month_start as date) as month_start,
    cast(year as integer)     as year,
    cast(month_num as integer) as month_num,
    trim(month_name)          as month_name,
    trim(quarter)             as quarter
from {{ source('raw', 'dim_date') }}
