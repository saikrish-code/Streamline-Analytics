with source as (
    select * from {{ source('raw', 'orders') }}
)

select
    nullif(trim(order_id), '') as order_id,
    nullif(trim(customer_id), '') as customer_id,
    lower(nullif(trim(order_status), '')) as order_status,
    nullif(trim(order_purchase_timestamp), '')::timestamp as purchased_at,
    nullif(trim(order_approved_at), '')::timestamp as approved_at,
    nullif(trim(order_delivered_carrier_date), '')::timestamp as delivered_to_carrier_at,
    nullif(trim(order_delivered_customer_date), '')::timestamp as delivered_to_customer_at,
    nullif(trim(order_estimated_delivery_date), '')::timestamp as estimated_delivery_at
from source
