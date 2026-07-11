with source as (
    select * from {{ source('raw', 'land_registry_transactions') }}
),

renamed as (
    select
        transaction_id,
        price,
        parse_date('%Y-%m-%d', left(transaction_date, 10)) as transaction_date,
        upper(trim(postcode)) as postcode,
        property_type,
        old_new,
        duration,
        paon,
        saon,
        street,
        locality,
        town_city,
        district,
        county as region,
        ppd_category,
        record_status
    from source
    where record_status = 'A'
        and left(transaction_date, 10) >= '{{ var("min_transaction_date") }}'
)

select * from renamed
