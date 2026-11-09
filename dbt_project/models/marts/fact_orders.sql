-- Grain: one row per Olist order item. Monetary item measures are additive across rows.
select
    md5(items.order_id || '|' || items.order_item_id::text) as order_line_key,
    items.order_id,
    items.order_item_id,
    orders.customer_unique_id,
    items.product_id,
    to_char(orders.purchased_at::date, 'YYYYMMDD')::integer as date_key,
    orders.order_status,
    orders.purchased_at,
    orders.approved_at,
    orders.delivered_to_carrier_at,
    orders.delivered_to_customer_at,
    orders.estimated_delivery_at,
    items.item_price,
    items.freight_value,
    items.item_price + items.freight_value as item_total
from {{ ref('stg_order_items') }} as items
inner join {{ ref('int_orders_enriched') }} as orders
    on items.order_id = orders.order_id
