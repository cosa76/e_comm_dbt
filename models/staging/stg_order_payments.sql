{{ config(materialized='view') }}

with source as (
    select * from {{ ref('olist_order_payments') }}
),

renamed as (
    select
        order_id,
        payment_sequential,
        payment_type,
        payment_installments,
        payment_value
    from source
)

select * from renamed
