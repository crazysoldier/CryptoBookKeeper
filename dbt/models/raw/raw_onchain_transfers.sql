-- Raw On-Chain Transfers Model
-- This model provides access to raw on-chain token transfer data
-- Returns empty result if no on-chain data is available

{% if execute %}
  {% set table_exists = run_query("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'raw_onchain_transfers'") %}
  {% if table_exists[0][0] > 0 %}
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
  {% else %}
    SELECT
        NULL as tx_hash,
        NULL as log_index,
        NULL as contract_address,
        NULL as from_address,
        NULL as to_address,
        NULL as value,
        NULL as token_symbol,
        NULL as token_decimal,
        NULL as block_number,
        NULL as block_timestamp,
        NULL as chain,
        NULL as raw_json
    WHERE FALSE
  {% endif %}
{% endif %}
