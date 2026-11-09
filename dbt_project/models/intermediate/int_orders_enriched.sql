select
    orders.order_id,
    orders.customer_id,
    customers.customer_unique_id,
    orders.order_status,
    orders.purchased_at,
    orders.approved_at,
    orders.delivered_to_carrier_at,
    orders.delivered_to_customer_at,
    orders.estimated_delivery_at,
    items.order_item_count,
    items.item_subtotal,
    items.freight_total,
    items.item_order_total,
    payments.payment_count,
    payments.payment_total,
    payments.installment_count,
    reviews.review_id,
    reviews.review_score,
    reviews.review_comment_title,
    reviews.review_comment_message,
    reviews.review_created_at,
    reviews.review_answered_at,
    coalesce(items.item_order_total, payments.payment_total) as order_total
from {{ ref('stg_orders') }} as orders
left join {{ ref('stg_customers') }} as customers
    on orders.customer_id = customers.customer_id
left join {{ ref('int_order_items_aggregated') }} as items
    on orders.order_id = items.order_id
left join {{ ref('int_payments_aggregated') }} as payments
    on orders.order_id = payments.order_id
left join {{ ref('int_reviews_deduplicated') }} as reviews
    on orders.order_id = reviews.order_id
