{{
    config(
        materialized='incremental',
        unique_key='txid',
        on_schema_change='sync_all_columns'
    )
}}

-- Unified Transactions Model (Incremental)
-- This model incrementally processes new transaction data
-- Uses txid as unique key for automatic deduplication

SELECT 
    domain,
    source,
    ts_utc,
    txid,
    base,
    quote,
    side,
    amount,
    price,
    fee_ccy,
    fee_amt,
    addr_from,
    addr_to,
    chain,
    token_symbol,
    token_decimal,
    raw_json,
    year,
    month
FROM transactions_unified
WHERE txid IS NOT NULL AND txid != ''

{% if is_incremental() %}
    -- Only process new transactions since last dbt run
    -- This dramatically speeds up processing and reduces compute
    AND ts_utc > (SELECT MAX(ts_utc) FROM {{ this }})
{% endif %}
