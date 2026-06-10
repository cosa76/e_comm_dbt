with order_items as (
    select * from {{ ref('stg_order_items') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

sellers as (
    select * from {{ ref('stg_sellers') }}
),

translations as (
    select * from {{ ref('stg_product_category_translations') }}
)

select
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    oi.shipping_limit_date,
    oi.price,
    oi.freight_value,
    oi.price + oi.freight_value                                         as total_item_value,

    -- produit
    p.product_category_name,
    coalesce(t.product_category_name_english, p.product_category_name) as product_category_name_english,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm,
    p.product_photos_qty,

    -- vendeur
    s.zip_code_prefix  as seller_zip_code_prefix,
    s.city             as seller_city,
    s.state            as seller_state

from order_items oi
left join products     p using (product_id)
left join translations t using (product_category_name)
left join sellers      s using (seller_id)
