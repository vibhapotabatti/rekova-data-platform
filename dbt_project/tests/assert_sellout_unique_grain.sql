{{ config(tags=['marts']) }}

-- Business rule: the sales fact must be unique at SKU × distributor × month.
select
    sku_id,
    distributor_id,
    month_start,
    count(*) as row_count
from {{ ref('fct_sellout') }}
group by 1, 2, 3
having count(*) > 1
