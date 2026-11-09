select
    event_id,
    lower(trim(event_type)) as event_type,
    event_timestamp,
    order_id,
    payload as event_payload,
    kafka_topic,
    kafka_partition,
    kafka_offset,
    kafka_timestamp,
    ingested_at
from {{ source('raw', 'streaming_events') }}
