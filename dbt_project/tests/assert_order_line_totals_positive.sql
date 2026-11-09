select order_line_key, item_price, freight_value, item_total
from {{ ref('fact_orders') }}
where item_price <= 0
   or freight_value < 0
   or item_total <= 0
