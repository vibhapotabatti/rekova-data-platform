with source as (

    select * from {{ source('raw', 'fact_sellout_monthly') }}

),

deduped as (

    select
        *,
        row_number() over (
            partition by month_start, sku_id, distributor_id, units,
                         gross_sales, net_sales, promo_flag, promo_discount_pct
            order by month_start
        ) as rn
    from source

),

cleaned as (

    select
        cast(month_start as date)        as month_start,
        trim(sku_id)                     as sku_id,
        trim(distributor_id)             as distributor_id,
        cast(units as integer)           as units,
        cast(gross_sales as decimal(18, 2)) as gross_sales,
        cast(net_sales as decimal(18, 2))   as net_sales,
        cast(promo_flag as integer)      as promo_flag,
        coalesce(cast(promo_discount_pct as decimal(6, 2)), 0) as promo_discount_pct
    from deduped
    where rn = 1
      and units > 0          -- returns live in stg_returns

),

with_channel as (

    select c.*, d.channel_type
    from cleaned c
    left join {{ ref('stg_distributor') }} d using (distributor_id)

),

final as (

    select
        month_start,
        sku_id,
        distributor_id,
        channel_type,
        units,
        gross_sales,
        coalesce(
            net_sales,
            round(
                gross_sales * (
                    1
                    - case channel_type
                        when 'General Trade' then 0.12
                        when 'Modern Trade'  then 0.10
                        when 'Pharmacy'      then 0.06
                        when 'E-commerce'    then 0.16
                        else 0.12
                      end
                    - promo_discount_pct / 100.0
                ),
                2
            )
        ) as net_sales,
        promo_flag,
        promo_discount_pct
    from with_channel

)

select * from final
