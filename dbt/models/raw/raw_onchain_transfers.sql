-- Raw On-Chain Transfers Model
-- This model provides access to raw on-chain token transfer data

SELECT
    tx_hash,
    log_index,
    contract_address,
    from_address,
    to_address,
    value,
    token_symbol,
    token_decimal,
    block_number,
    block_timestamp,
    chain,
    raw_json
FROM main.raw_onchain_transfers
