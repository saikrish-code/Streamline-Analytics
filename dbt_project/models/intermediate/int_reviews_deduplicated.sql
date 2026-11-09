with ranked as (
    select
        *,
        row_number() over (
            partition by order_id
            order by review_answered_at desc nulls last,
                     review_created_at desc nulls last,
                     review_score desc nulls last,
                     review_id
        ) as review_rank
    from {{ ref('stg_reviews') }}
)

select
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_created_at,
    review_answered_at
from ranked
where review_rank = 1
