with source as (
    select * from {{ source('raw', 'order_items') }}
)

select
    nullif(trim(order_id), '') as order_id,
    order_item_id,
    nullif(trim(product_id), '') as product_id,
    nullif(trim(seller_id), '') as seller_id,
    nullif(trim(shipping_limit_date), '')::timestamp as shipping_limit_at,
    price::numeric(12, 2) as item_price,
    freight_value::numeric(12, 2) as freight_value
from source
