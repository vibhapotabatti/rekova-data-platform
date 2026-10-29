{{ config(tags=['marts']) }}

-- Amount sanity: positive units, positive gross and net, net never above gross.
select *
from {{ ref('fct_sellout') }}
where units <= 0
   or gross_sales <= 0
   or net_sales <= 0
   or net_sales > gross_sales + 0.01
