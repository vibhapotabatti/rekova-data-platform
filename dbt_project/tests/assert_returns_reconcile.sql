{{ config(tags=['marts']) }}

-- Returns are separated from sales: exactly the 18 negative-unit feed rows.
select count(*) as returns_rows
from {{ ref('stg_returns') }}
having count(*) <> 18
