with source as (
    select * from {{ source('raw', 'products') }}
)

select
    nullif(trim(product_id), '') as product_id,
    lower(nullif(trim(product_category_name), '')) as category_name,
    product_name_length,
    product_description_length,
    product_photos_qty as photo_count,
    product_weight_g as weight_g,
    product_length_cm as length_cm,
    product_height_cm as height_cm,
    product_width_cm as width_cm
from source
