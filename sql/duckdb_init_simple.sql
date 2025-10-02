-- =============================================================================
-- CRYPTO NORMALIZER - DUCKDB INITIALIZATION (SIMPLIFIED)
-- =============================================================================

-- Create database if it doesn't exist
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS curated;

-- Set basic configuration
PRAGMA memory_limit='2GB';
PRAGMA threads=2;

-- =============================================================================
-- RAW DATA TABLES (with unique constraints for upsert behavior)
-- =============================================================================

-- Exchange trades table
CREATE TABLE IF NOT EXISTS raw_exchanges_trades (
    source VARCHAR NOT NULL,
    exchange VARCHAR,
    account VARCHAR,
    txid VARCHAR NOT NULL,
    orderid VARCHAR,
    datetime TIMESTAMP,
    symbol VARCHAR,
    side VARCHAR,
    amount DOUBLE,
    price DOUBLE,
    cost DOUBLE,
    fee DOUBLE,
    fee_currency VARCHAR,
    raw_json VARCHAR,
    PRIMARY KEY (source, txid)  -- Composite key for deduplication
);

-- Exchange deposits table
CREATE TABLE IF NOT EXISTS raw_exchanges_deposits (
    source VARCHAR NOT NULL,
    exchange VARCHAR,
    account VARCHAR,
    txid VARCHAR NOT NULL,
    datetime TIMESTAMP,
    currency VARCHAR,
    amount DOUBLE,
    status VARCHAR,
    address VARCHAR,
    tag VARCHAR,
    raw_json VARCHAR,
    PRIMARY KEY (source, txid)  -- Composite key for deduplication
);

-- Exchange withdrawals table
CREATE TABLE IF NOT EXISTS raw_exchanges_withdrawals (
    source VARCHAR NOT NULL,
    exchange VARCHAR,
    account VARCHAR,
    txid VARCHAR NOT NULL,
    datetime TIMESTAMP,
    currency VARCHAR,
    amount DOUBLE,
    status VARCHAR,
    address VARCHAR,
    tag VARCHAR,
    raw_json VARCHAR,
    PRIMARY KEY (source, txid)  -- Composite key for deduplication
);

-- On-chain transfers table
CREATE TABLE IF NOT EXISTS raw_onchain_transfers (
    chain VARCHAR NOT NULL,
    tx_hash VARCHAR NOT NULL,
    log_index INTEGER,
    block_number BIGINT,
    block_timestamp TIMESTAMP,
    from_address VARCHAR,
    to_address VARCHAR,
    contract_address VARCHAR,
    token_symbol VARCHAR,
    token_decimal INTEGER,
    value DOUBLE,
    side VARCHAR,
    tx_type VARCHAR,
    raw_json VARCHAR,
    PRIMARY KEY (chain, tx_hash, log_index)  -- Composite key (multiple logs per tx)
);

-- =============================================================================
-- CURATED DATA TABLES
-- =============================================================================

-- Unified transactions table
CREATE TABLE IF NOT EXISTS curated.transactions_unified (
    txid VARCHAR,
    domain VARCHAR,
    source VARCHAR,
    ts_utc TIMESTAMP,
    asset VARCHAR,
    amount DOUBLE,
    price_usd DOUBLE,
    value_usd DOUBLE,
    fee_usd DOUBLE,
    from_address VARCHAR,
    to_address VARCHAR,
    exchange VARCHAR,
    blockchain VARCHAR,
    raw_json VARCHAR
);

-- =============================================================================
-- METADATA TABLES (For Incremental Loading)
-- =============================================================================

-- Sync log table to track incremental loads
CREATE TABLE IF NOT EXISTS sync_log (
    source VARCHAR PRIMARY KEY,          -- e.g., 'coinbase_trades', 'debank_eth'
    last_sync_ts TIMESTAMP,              -- Last successful sync timestamp
    last_txid VARCHAR,                   -- Last transaction ID (for pagination)
    sync_count INTEGER,                  -- Number of records in last sync
    sync_status VARCHAR,                 -- 'success', 'partial', 'failed'
    error_message VARCHAR,               -- Error details if failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INITIALIZATION COMPLETE
-- =============================================================================
