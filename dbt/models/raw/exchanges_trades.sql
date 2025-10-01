-- Raw Exchange Trades Model
-- This model provides access to raw exchange trade data

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
    raw_json
FROM main.raw_exchanges_trades
