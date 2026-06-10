{{ config(materialized='table') }}

with customers as (
    select * from {{ ref('stg_customers') }}
),

-- moyenne lat/lng par code postal (la source géoloc a des doublons)
geolocation as (
    select
        zip_code_prefix,
        avg(lat) as lat,
        avg(lng) as lng
    from {{ ref('stg_geolocation') }}
    group by zip_code_prefix
),

-- un client unique peut avoir plusieurs customer_id (plusieurs commandes)
-- On utilise ROW_NUMBER pour forcer une seule ligne par customer_unique_id
customers_dedup as (
    select 
        customer_unique_id,
        city,
        state,
        zip_code_prefix
    from (
        select 
            customer_unique_id,
            city,
            state,
            zip_code_prefix,
            row_number() over (partition by customer_unique_id order by customer_id) as rn
        from customers
    )
    where rn = 1
),

orders_summary as (
    select
        customer_unique_id,
        count(distinct order_id)         as total_orders,
        min(order_purchase_timestamp)    as first_order_at,
        max(order_purchase_timestamp)    as last_order_at,
        sum(total_payment_value)         as lifetime_value,
        avg(avg_review_score)            as avg_review_score
    from {{ ref('int_orders_enriched') }}
    group by customer_unique_id
)

select
    cd.customer_unique_id,
    cd.city,
    cd.state,
    cd.zip_code_prefix,
    g.lat,
    g.lng,
    coalesce(os.total_orders, 0)  as total_orders,
    os.first_order_at,
    os.last_order_at,
    os.lifetime_value,
    os.avg_review_score
from customers_dedup  cd
left join geolocation  g  using (zip_code_prefix)
left join orders_summary os using (customer_unique_id)