select
    month_start,
    year,
    month_num,
    month_name,
    quarter,
    cast(strftime(month_start, '%Y%m') as integer) as month_key,
    strftime(month_start, '%Y-%m') as year_month
from {{ ref('stg_date') }}
