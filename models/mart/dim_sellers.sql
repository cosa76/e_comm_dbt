
{{ config(materialized='table') }}

with sellers as (
    select * from {{ ref('stg_sellers') }}
),

geolocation as (
    select
        zip_code_prefix,
        avg(lat) as lat,
        avg(lng) as lng
    from {{ ref('stg_geolocation') }}
    group by zip_code_prefix
),

sales_summary as (
    select
        seller_id,
        count(distinct order_id)    as total_orders,
        count(*)                    as total_items_sold,
        sum(price)                  as total_revenue,
        avg(price)                  as avg_item_price,
        count(distinct product_id)  as distinct_products
    from {{ ref('int_order_items_enriched') }}
    group by seller_id
)

select
    s.seller_id,
    s.city,
    s.state,
    s.zip_code_prefix,
    g.lat,
    g.lng,
    coalesce(ss.total_orders, 0)        as total_orders,
    coalesce(ss.total_items_sold, 0)    as total_items_sold,
    ss.total_revenue,
    ss.avg_item_price,
    coalesce(ss.distinct_products, 0)   as distinct_products
from sellers         s
left join geolocation   g  using (zip_code_prefix)
left join sales_summary ss using (seller_id)
