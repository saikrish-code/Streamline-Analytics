select
    product_id,
    category_name,
    product_name_length,
    product_description_length,
    photo_count,
    weight_g,
    length_cm,
    height_cm,
    width_cm
from {{ ref('stg_products') }}
