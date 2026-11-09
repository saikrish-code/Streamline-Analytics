-- Raw-zone landing schema. Source dates and identifiers remain text to preserve source values.
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id text NOT NULL,
    customer_unique_id text,
    customer_zip_code_prefix text,
    customer_city text,
    customer_state text
);

CREATE TABLE IF NOT EXISTS raw.orders (
    order_id text NOT NULL,
    customer_id text,
    order_status text,
    order_purchase_timestamp text,
    order_approved_at text,
    order_delivered_carrier_date text,
    order_delivered_customer_date text,
    order_estimated_delivery_date text
);

CREATE TABLE IF NOT EXISTS raw.order_items (
    order_id text NOT NULL,
    order_item_id integer,
    product_id text,
    seller_id text,
    shipping_limit_date text,
    price numeric(12, 2),
    freight_value numeric(12, 2)
);

CREATE TABLE IF NOT EXISTS raw.payments (
    order_id text NOT NULL,
    payment_sequential integer,
    payment_type text,
    payment_installments integer,
    payment_value numeric(12, 2)
);

CREATE TABLE IF NOT EXISTS raw.reviews (
    review_id text,
    order_id text NOT NULL,
    review_score integer,
    review_comment_title text,
    review_comment_message text,
    review_creation_date text,
    review_answer_timestamp text
);

CREATE TABLE IF NOT EXISTS raw.products (
    product_id text NOT NULL,
    product_category_name text,
    product_name_length integer,
    product_description_length integer,
    product_photos_qty integer,
    product_weight_g bigint,
    product_length_cm bigint,
    product_height_cm bigint,
    product_width_cm bigint
);
