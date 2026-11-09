-- Grain: the latest Olist review for an order, with the customer's unique ID.
select
    review_id,
    order_id,
    customer_unique_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_created_at,
    review_answered_at
from {{ ref('int_orders_enriched') }}
where review_id is not null
