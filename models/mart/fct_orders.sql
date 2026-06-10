{{ config(materialized='table') }}

with orders_enriched as (
    select * from {{ ref('int_orders_enriched') }}
),

items_summary as (
    select
        order_id,
        count(*)                                    as item_count,
        sum(price)                                  as items_revenue,
        sum(freight_value)                          as items_freight,
        sum(total_item_value)                       as items_total_value,
        count(distinct seller_id)                   as distinct_sellers,
        count(distinct product_category_name_english) as distinct_categories
    from {{ ref('int_order_items_enriched') }}
    group by order_id
)

select
    oe.order_id,
    oe.customer_id,
    oe.customer_unique_id,
    oe.customer_city,
    oe.customer_state,
    oe.customer_zip_code_prefix,

    oe.order_status,
    oe.order_purchase_timestamp,
    oe.order_approved_at,
    oe.order_delivered_carrier_date,
    oe.order_delivered_customer_date,
    oe.order_estimated_delivery_date,
    oe.delivery_days,
    oe.days_early_vs_estimate,

    oe.avg_review_score,
    oe.review_count,

    oe.total_payment_value,
    oe.payment_type_count,
    oe.max_payment_installments,

    is_.item_count,
    is_.items_revenue,
    is_.items_freight,
    is_.items_total_value,
    is_.distinct_sellers,
    is_.distinct_categories

from orders_enriched oe
left join items_summary is_ using (order_id)
