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
-- RAW DATA TABLES
-- =============================================================================

-- Exchange trades table
CREATE TABLE IF NOT EXISTS raw.exchanges_trades (
    source VARCHAR,
    exchange VARCHAR,
    account VARCHAR,
    txid VARCHAR,
    orderid VARCHAR,
    datetime TIMESTAMP,
    symbol VARCHAR,
    side VARCHAR,
    amount DOUBLE,
    price DOUBLE,
    cost DOUBLE,
    fee DOUBLE,
    fee_currency VARCHAR,
    raw_json VARCHAR
);

-- Exchange deposits table
CREATE TABLE IF NOT EXISTS raw.exchanges_deposits (
    source VARCHAR,
    exchange VARCHAR,
    account VARCHAR,
    txid VARCHAR,
    datetime TIMESTAMP,
    currency VARCHAR,
    amount DOUBLE,
    status VARCHAR,
    address VARCHAR,
    tag VARCHAR,
    raw_json VARCHAR
);

-- Exchange withdrawals table
CREATE TABLE IF NOT EXISTS raw.exchanges_withdrawals (
    source VARCHAR,
    exchange VARCHAR,
    account VARCHAR,
    txid VARCHAR,
    datetime TIMESTAMP,
    currency VARCHAR,
    amount DOUBLE,
    status VARCHAR,
    address VARCHAR,
    tag VARCHAR,
    raw_json VARCHAR
);

-- On-chain transfers table
CREATE TABLE IF NOT EXISTS raw.onchain_transfers (
    source VARCHAR,
    blockchain VARCHAR,
    txid VARCHAR,
    block_number BIGINT,
    block_timestamp TIMESTAMP,
    from_address VARCHAR,
    to_address VARCHAR,
    token_address VARCHAR,
    token_symbol VARCHAR,
    amount DOUBLE,
    raw_json VARCHAR
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
-- INITIALIZATION COMPLETE
-- =============================================================================
