{{ config(materialized='table') }}

with products as (
    select * from {{ ref('stg_products') }}
),

translations as (
    select * from {{ ref('stg_product_category_translations') }}
),

sales_summary as (
    select
        product_id,
        count(distinct order_id)  as total_orders,
        sum(price)                as total_revenue,
        avg(price)                as avg_price,
        avg(freight_value)        as avg_freight_value
    from {{ ref('int_order_items_enriched') }}
    group by product_id
)

select
    p.product_id,
    p.product_category_name,
    coalesce(t.product_category_name_english, p.product_category_name) as product_category_name_english,
    p.product_name_length,
    p.product_description_length,
    p.product_photos_qty,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm,
    coalesce(ss.total_orders, 0)  as total_orders,
    ss.total_revenue,
    ss.avg_price,
    ss.avg_freight_value
from products        p
left join translations  t  using (product_category_name)
left join sales_summary ss using (product_id)
