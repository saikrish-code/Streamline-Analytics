select order_id, order_total
from {{ ref('int_orders_enriched') }}
where order_status is null
   or (order_status not in ('canceled', 'unavailable')
       and (order_total is null or order_total <= 0))
