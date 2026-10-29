select
    trim(sku_id)          as sku_id,
    trim(sku_name)        as sku_name,
    trim(brand)           as brand,
    trim(category)        as category,
    trim(pack_size)       as pack_size,
    cast(mrp as decimal(18, 2)) as mrp
from {{ source('raw', 'dim_product') }}
