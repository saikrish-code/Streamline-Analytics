with source as (
    select * from {{ source('raw', 'customers') }}
)

select
    nullif(trim(customer_id), '') as customer_id,
    nullif(trim(customer_unique_id), '') as customer_unique_id,
    nullif(trim(customer_zip_code_prefix), '') as zip_code_prefix,
    nullif(trim(customer_city), '') as city,
    upper(nullif(trim(customer_state), '')) as state_code
from source
