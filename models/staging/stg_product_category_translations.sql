
{{ config(materialized='view') }}

with source as (
    select * from {{ ref('product_category_name_translation') }}
),

renamed as (
    select
        -- le CSV contient un BOM sur la première colonne, nettoyé ici
        trim(product_category_name)         as product_category_name,
        product_category_name_english
    from source
)

select * from renamed
