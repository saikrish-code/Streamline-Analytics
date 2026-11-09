select event_id, event_type, event_payload
from {{ ref('stg_streaming_events') }}
where (event_type = 'new_order'
       and event_payload -> 'data' ->> 'status' is distinct from 'created')
   or (event_type = 'order_status_change'
       and not coalesce((
           (event_payload -> 'data' ->> 'previous_status' = 'created'
                and event_payload -> 'data' ->> 'status' in ('approved', 'canceled'))
           or (event_payload -> 'data' ->> 'previous_status' = 'approved'
                and event_payload -> 'data' ->> 'status' in ('shipped', 'canceled'))
           or (event_payload -> 'data' ->> 'previous_status' = 'shipped'
                and event_payload -> 'data' ->> 'status' = 'delivered')
       ), false))
   or event_type not in ('new_order', 'order_status_change')
