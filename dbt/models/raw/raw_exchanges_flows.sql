-- Raw Exchange Flows Model (Deposits + Withdrawals)
-- This model combines deposits and withdrawals into a single view

SELECT
    source,
    exchange,
    account,
    txid,
    orderid,
    datetime,
    base,
    quote,
    side,
    amount,
    price,
    fee_currency,
    fee_amount,
    address,
    status,
    raw_json,
    'deposit' as flow_type
FROM main.raw_exchanges_deposits

UNION ALL

SELECT
    source,
    exchange,
    account,
    txid,
    orderid,
    datetime,
    base,
    quote,
    side,
    amount,
    price,
    fee_currency,
    fee_amount,
    address,
    status,
    raw_json,
    'withdrawal' as flow_type
FROM main.raw_exchanges_withdrawals
