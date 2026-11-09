-- Run once after `dbt run`. Dashboard read paths use compact, indexed snapshots.
create materialized view if not exists marts.dashboard_revenue_daily as
select date_key, min(purchased_at::date) as date_day,
       sum(item_total)::numeric(14,2) as revenue
from marts.fact_orders
where order_status = 'delivered'
group by date_key;
create unique index if not exists dashboard_revenue_daily_date_idx
  on marts.dashboard_revenue_daily (date_key);

create materialized view if not exists marts.dashboard_product_revenue as
select coalesce(nullif(p.category_name, ''), 'uncategorized') as category_name,
       sum(f.item_total)::numeric(14,2) as revenue,
       count(distinct f.order_id)::bigint as orders
from marts.fact_orders f
left join marts.dim_products p using (product_id)
where f.order_status = 'delivered'
group by 1;
create unique index if not exists dashboard_product_revenue_category_idx
  on marts.dashboard_product_revenue (category_name);

create materialized view if not exists marts.dashboard_order_funnel as
select stage, count(*)::bigint as orders from (
  select order_id,
    case when bool_or(delivered_to_customer_at is not null) then 'Delivered'
         when bool_or(delivered_to_carrier_at is not null) then 'Shipped'
         when bool_or(approved_at is not null) then 'Approved'
         else 'Placed' end as stage
  from marts.fact_orders group by order_id
) orders
group by stage;
create unique index if not exists dashboard_order_funnel_stage_idx
  on marts.dashboard_order_funnel (stage);
