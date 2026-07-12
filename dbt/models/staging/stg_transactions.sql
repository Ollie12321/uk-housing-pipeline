with source as (
    select * from {{ source('raw', 'land_registry_transactions') }}
),

-- Deduplicate: raw table can have the same transaction loaded multiple times
-- when pp-{year}.csv is refreshed. Keep one row per transaction_id.
deduped as (
    select *
    from source
    qualify row_number() over (partition by transaction_id order by transaction_date desc) = 1
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
        {{ county_to_region('upper(trim(county))') }} as broad_region,
        ppd_category,
        record_status
    from deduped
    where record_status = 'A'
        and left(transaction_date, 10) >= '{{ var("min_transaction_date") }}'
)

select * from renamed
