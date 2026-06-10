
{{ config(materialized='table') }}

with order_items_enriched as (
    select * from {{ ref('int_order_items_enriched') }}
),

orders as (
    select
        order_id,
        customer_unique_id,
        order_status,
        order_purchase_timestamp,
        order_delivered_customer_date,
        avg_review_score
    from {{ ref('int_orders_enriched') }}
)

select
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,

    o.customer_unique_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_delivered_customer_date,
    o.avg_review_score,

    oi.shipping_limit_date,
    oi.price,
    oi.freight_value,
    oi.total_item_value,

    oi.product_category_name,
    oi.product_category_name_english,
    oi.product_weight_g,
    oi.product_length_cm,
    oi.product_height_cm,
    oi.product_width_cm,
    oi.product_photos_qty,

    oi.seller_zip_code_prefix,
    oi.seller_city,
    oi.seller_state

from order_items_enriched oi
left join orders o using (order_id)
