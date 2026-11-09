with order_bounds as (
    select
        min(purchased_at::date) as first_date,
        max(purchased_at::date) as last_date
    from {{ ref('int_orders_enriched') }}
    where purchased_at is not null
),
calendar as (
    select series.date_day::date as date_day
    from order_bounds
    cross join lateral generate_series(first_date, last_date, interval '1 day') as series(date_day)
)

select
    to_char(date_day, 'YYYYMMDD')::integer as date_key,
    date_day,
    extract(year from date_day)::integer as year,
    extract(quarter from date_day)::integer as quarter,
    extract(month from date_day)::integer as month,
    to_char(date_day, 'FMMonth') as month_name,
    extract(day from date_day)::integer as day_of_month,
    extract(isodow from date_day)::integer as day_of_week,
    to_char(date_day, 'FMDay') as day_name,
    (extract(isodow from date_day) in (6, 7)) as is_weekend
from calendar
