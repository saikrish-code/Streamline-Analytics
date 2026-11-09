with source as (
    select * from {{ source('raw', 'payments') }}
)

select
    nullif(trim(order_id), '') as order_id,
    payment_sequential,
    lower(nullif(trim(payment_type), '')) as payment_type,
    payment_installments,
    payment_value::numeric(12, 2) as payment_value
from source
