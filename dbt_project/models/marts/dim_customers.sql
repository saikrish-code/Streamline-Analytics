select
    customer_unique_id,
    zip_code_prefix,
    city,
    state_code
from {{ ref('int_customers_deduplicated') }}
