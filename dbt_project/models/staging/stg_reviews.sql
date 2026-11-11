with source as (
    select * from {{ source('raw', 'reviews') }}
)

select
    nullif(trim(review_id), '') as review_id,
    nullif(trim(order_id), '') as order_id,
    nullif(trim(review_score), '')::integer as review_score,
    nullif(trim(review_comment_title), '') as review_comment_title,
    nullif(trim(review_comment_message), '') as review_comment_message,
    nullif(trim(review_creation_date), '')::timestamp as review_created_at,
    nullif(trim(review_answer_timestamp), '')::timestamp as review_answered_at
from source
