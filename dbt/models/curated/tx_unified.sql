-- Unified Transactions Model
-- This model provides access to the unified transaction data created by the staging process

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
