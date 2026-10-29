{{ config(tags=['marts']) }}

-- No fact row may reference a missing dimension member.
select
    f.sku_id,
    f.distributor_id
from {{ ref('fct_sellout') }} f
left join {{ ref('dim_product') }} p using (sku_id)
left join {{ ref('dim_distributor') }} d using (distributor_id)
where p.sku_id is null
   or d.distributor_id is null
