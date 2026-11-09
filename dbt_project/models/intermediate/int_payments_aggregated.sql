select
    order_id,
    count(*) as payment_count,
    sum(payment_value) as payment_total,
    sum(payment_installments) as installment_count
from {{ ref('stg_payments') }}
group by order_id
