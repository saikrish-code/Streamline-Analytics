"""Olist source-file to raw PostgreSQL table definitions."""

from sqlalchemy import BigInteger, Column, Integer, MetaData, Numeric, String, Table, Text

RAW_SCHEMA = "raw"
metadata = MetaData(schema=RAW_SCHEMA)

# Keep source date fields as text in raw so source formatting and partial timestamps are retained.
TABLES = {
    "customers": Table(
        "customers", metadata,
        Column("customer_id", String(64), nullable=False),
        Column("customer_unique_id", String(64)),
        Column("customer_zip_code_prefix", String(16)),
        Column("customer_city", Text),
        Column("customer_state", String(8)),
    ),
    "orders": Table(
        "orders", metadata,
        Column("order_id", String(64), nullable=False),
        Column("customer_id", String(64)),
        Column("order_status", String(32)),
        Column("order_purchase_timestamp", String(40)),
        Column("order_approved_at", String(40)),
        Column("order_delivered_carrier_date", String(40)),
        Column("order_delivered_customer_date", String(40)),
        Column("order_estimated_delivery_date", String(40)),
    ),
    "order_items": Table(
        "order_items", metadata,
        Column("order_id", String(64), nullable=False),
        Column("order_item_id", Integer),
        Column("product_id", String(64)),
        Column("seller_id", String(64)),
        Column("shipping_limit_date", String(40)),
        Column("price", Numeric(12, 2)),
        Column("freight_value", Numeric(12, 2)),
    ),
    "payments": Table(
        "payments", metadata,
        Column("order_id", String(64), nullable=False),
        Column("payment_sequential", Integer),
        Column("payment_type", String(40)),
        Column("payment_installments", Integer),
        Column("payment_value", Numeric(12, 2)),
    ),
    "reviews": Table(
        "reviews", metadata,
        Column("review_id", String(64)),
        Column("order_id", String(64), nullable=False),
        Column("review_score", Integer),
        Column("review_comment_title", Text),
        Column("review_comment_message", Text),
        Column("review_creation_date", String(40)),
        Column("review_answer_timestamp", String(40)),
    ),
    "products": Table(
        "products", metadata,
        Column("product_id", String(64), nullable=False),
        Column("product_category_name", Text),
        Column("product_name_length", Integer),
        Column("product_description_length", Integer),
        Column("product_photos_qty", Integer),
        Column("product_weight_g", BigInteger),
        Column("product_length_cm", BigInteger),
        Column("product_height_cm", BigInteger),
        Column("product_width_cm", BigInteger),
    ),
}

CSV_FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
}
EXPECTED_COLUMNS = {
    name: tuple(column.name for column in table.columns)
    for name, table in TABLES.items()
}
