with orders as (
    select * from {{ ref('stg_orders') }}
),

customers as (
    select * from {{ ref('stg_customers') }}
),

reviews_agg as (
    select
        order_id,
        avg(review_score)  as avg_review_score,
        count(*)           as review_count
    from {{ ref('stg_order_reviews') }}
    group by order_id
),

payments_agg as (
    select
        order_id,
        sum(payment_value)              as total_payment_value,
        count(distinct payment_type)    as payment_type_count,
        max(payment_installments)       as max_payment_installments
    from {{ ref('stg_order_payments') }}
    group by order_id
)

select
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.zip_code_prefix                                  as customer_zip_code_prefix,
    c.city                                             as customer_city,
    c.state                                            as customer_state,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,

    -- délais en jours
    date_diff(
        cast(o.order_delivered_customer_date as date),
        cast(o.order_purchase_timestamp as date),
        day
    )                                                  as delivery_days,

    date_diff(
        cast(o.order_estimated_delivery_date as date),
        cast(o.order_delivered_customer_date as date),
        day
    )                                                  as days_early_vs_estimate,

    r.avg_review_score,
    r.review_count,
    p.total_payment_value,
    p.payment_type_count,
    p.max_payment_installments

from orders o
left join customers      c using (customer_id)
left join reviews_agg    r using (order_id)
left join payments_agg   p using (order_id)
