select
    order_id,
    count(*) as order_item_count,
    sum(item_price) as item_subtotal,
    sum(freight_value) as freight_total,
    sum(item_price + freight_value) as item_order_total
from {{ ref('stg_order_items') }}
group by order_id
