{{ config(tags=['marts']) }}

-- The FP&A target feed exists at region × channel × month only.
select
    month_start,
    region,
    channel_type,
    count(*) as row_count
from {{ ref('fct_targets') }}
group by 1, 2, 3
having count(*) > 1
