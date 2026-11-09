with ranked as (
    select
        customers.*,
        orders.purchased_at,
        row_number() over (
            partition by customers.customer_unique_id
            order by orders.purchased_at desc nulls last, customers.customer_id desc
        ) as customer_rank
    from {{ ref('stg_customers') }} as customers
    left join {{ ref('stg_orders') }} as orders
        on customers.customer_id = orders.customer_id
)

select
    customer_unique_id,
    zip_code_prefix,
    city,
    state_code
from ranked
where customer_rank = 1
