-- Crypto Normalizer - DuckDB Initialization Script
-- Creates database schema and optimizes for performance

-- =============================================================================
-- DATABASE CONFIGURATION
-- =============================================================================

-- Set memory and thread limits
PRAGMA memory_limit='4GB';
PRAGMA threads=4;
PRAGMA enable_progress_bar=true;
-- PRAGMA enable_verification=false;  -- Not supported in this DuckDB version

-- =============================================================================
-- RAW DATA SCHEMAS
-- =============================================================================

-- Exchange Trades Schema
CREATE TABLE IF NOT EXISTS raw_exchanges_trades (
    source VARCHAR,
    exchange VARCHAR,
    account VARCHAR,
    txid VARCHAR,
    orderid VARCHAR,
    datetime TIMESTAMP,
    base VARCHAR,
    quote VARCHAR,
    side VARCHAR,
    amount DECIMAL(38,18),
    price DECIMAL(38,18),
    fee_currency VARCHAR,
    fee_amount DECIMAL(38,18),
    address VARCHAR,
    status VARCHAR,
    raw_json JSON
);

-- Exchange Deposits Schema
CREATE TABLE IF NOT EXISTS raw_exchanges_deposits (
    source VARCHAR,
    exchange VARCHAR,
    account VARCHAR,
    txid VARCHAR,
    orderid VARCHAR,
    datetime TIMESTAMP,
    base VARCHAR,
    quote VARCHAR,
    side VARCHAR,
    amount DECIMAL(38,18),
    price DECIMAL(38,18),
    fee_currency VARCHAR,
    fee_amount DECIMAL(38,18),
    address VARCHAR,
    status VARCHAR,
    raw_json JSON
);

-- Exchange Withdrawals Schema
CREATE TABLE IF NOT EXISTS raw_exchanges_withdrawals (
    source VARCHAR,
    exchange VARCHAR,
    account VARCHAR,
    txid VARCHAR,
    orderid VARCHAR,
    datetime TIMESTAMP,
    base VARCHAR,
    quote VARCHAR,
    side VARCHAR,
    amount DECIMAL(38,18),
    price DECIMAL(38,18),
    fee_currency VARCHAR,
    fee_amount DECIMAL(38,18),
    address VARCHAR,
    status VARCHAR,
    raw_json JSON
);

-- On-Chain Token Transfers Schema
CREATE TABLE IF NOT EXISTS raw_onchain_transfers (
    tx_hash VARCHAR,
    log_index INTEGER,
    contract_address VARCHAR,
    from_address VARCHAR,
    to_address VARCHAR,
    value DECIMAL(38,18),
    token_symbol VARCHAR,
    token_decimal INTEGER,
    block_number BIGINT,
    block_timestamp TIMESTAMP,
    chain VARCHAR,
    raw_json JSON
);

-- On-Chain Transaction Receipts Schema
CREATE TABLE IF NOT EXISTS raw_onchain_receipts (
    tx_hash VARCHAR,
    block_number BIGINT,
    block_timestamp TIMESTAMP,
    from_address VARCHAR,
    to_address VARCHAR,
    value DECIMAL(38,18),
    gas_used BIGINT,
    gas_price DECIMAL(38,18),
    status INTEGER,
    chain VARCHAR,
    raw_json JSON
);

-- =============================================================================
-- STAGING SCHEMAS
-- =============================================================================

-- Staged Exchange Data (cleaned and typed)
CREATE TABLE IF NOT EXISTS staged_exchanges (
    domain VARCHAR DEFAULT 'exchange',
    source VARCHAR,
    ts_utc TIMESTAMP,
    txid VARCHAR,
    base VARCHAR,
    quote VARCHAR,
    side VARCHAR,
    amount DECIMAL(38,18),
    price DECIMAL(38,18),
    fee_ccy VARCHAR,
    fee_amt DECIMAL(38,18),
    addr_from VARCHAR,
    addr_to VARCHAR,
    chain VARCHAR,
    token_symbol VARCHAR,
    token_decimal INTEGER,
    raw_json JSON,
    year INTEGER,
    month INTEGER
);

-- Staged On-Chain Data (cleaned and typed)
CREATE TABLE IF NOT EXISTS staged_onchain (
    domain VARCHAR DEFAULT 'onchain',
    source VARCHAR,
    ts_utc TIMESTAMP,
    txid VARCHAR,
    base VARCHAR,
    quote VARCHAR,
    side VARCHAR,
    amount DECIMAL(38,18),
    price DECIMAL(38,18),
    fee_ccy VARCHAR,
    fee_amt DECIMAL(38,18),
    addr_from VARCHAR,
    addr_to VARCHAR,
    chain VARCHAR,
    token_symbol VARCHAR,
    token_decimal INTEGER,
    raw_json JSON,
    year INTEGER,
    month INTEGER
);

-- =============================================================================
-- CURATED SCHEMAS
-- =============================================================================

-- Unified Transactions (final business model)
CREATE TABLE IF NOT EXISTS transactions_unified (
    domain VARCHAR,
    source VARCHAR,
    ts_utc TIMESTAMP,
    txid VARCHAR,
    base VARCHAR,
    quote VARCHAR,
    side VARCHAR,
    amount DECIMAL(38,18),
    price DECIMAL(38,18),
    fee_ccy VARCHAR,
    fee_amt DECIMAL(38,18),
    addr_from VARCHAR,
    addr_to VARCHAR,
    chain VARCHAR,
    token_symbol VARCHAR,
    token_decimal INTEGER,
    raw_json JSON,
    year INTEGER,
    month INTEGER
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Time-based indexes
CREATE INDEX IF NOT EXISTS idx_staged_exchanges_ts ON staged_exchanges(ts_utc);
CREATE INDEX IF NOT EXISTS idx_staged_onchain_ts ON staged_onchain(ts_utc);
CREATE INDEX IF NOT EXISTS idx_transactions_unified_ts ON transactions_unified(ts_utc);

-- Domain/Source indexes
CREATE INDEX IF NOT EXISTS idx_staged_exchanges_domain_source ON staged_exchanges(domain, source);
CREATE INDEX IF NOT EXISTS idx_staged_onchain_domain_source ON staged_onchain(domain, source);
CREATE INDEX IF NOT EXISTS idx_transactions_unified_domain_source ON transactions_unified(domain, source);

-- Asset indexes
CREATE INDEX IF NOT EXISTS idx_staged_exchanges_base_quote ON staged_exchanges(base, quote);
CREATE INDEX IF NOT EXISTS idx_staged_onchain_token ON staged_onchain(token_symbol);
CREATE INDEX IF NOT EXISTS idx_transactions_unified_base_quote ON transactions_unified(base, quote);

-- Transaction ID indexes
CREATE INDEX IF NOT EXISTS idx_staged_exchanges_txid ON staged_exchanges(txid);
CREATE INDEX IF NOT EXISTS idx_staged_onchain_txid ON staged_onchain(txid);
CREATE INDEX IF NOT EXISTS idx_transactions_unified_txid ON transactions_unified(txid);

-- =============================================================================
-- UTILITY FUNCTIONS
-- =============================================================================

-- Function to extract year from timestamp
CREATE OR REPLACE FUNCTION extract_year(ts TIMESTAMP) AS (EXTRACT(YEAR FROM ts)::INTEGER);

-- Function to extract month from timestamp
CREATE OR REPLACE FUNCTION extract_month(ts TIMESTAMP) AS (EXTRACT(MONTH FROM ts)::INTEGER);

-- =============================================================================
-- DATA QUALITY VIEWS
-- =============================================================================

-- View for data quality checks
CREATE OR REPLACE VIEW data_quality_checks AS
SELECT 
    'staged_exchanges' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT txid) as unique_txids,
    COUNT(*) - COUNT(DISTINCT txid) as duplicate_txids,
    COUNT(*) FILTER (WHERE ts_utc IS NULL) as null_timestamps,
    COUNT(*) FILTER (WHERE amount <= 0) as invalid_amounts
FROM staged_exchanges

UNION ALL

SELECT 
    'staged_onchain' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT txid) as unique_txids,
    COUNT(*) - COUNT(DISTINCT txid) as duplicate_txids,
    COUNT(*) FILTER (WHERE ts_utc IS NULL) as null_timestamps,
    COUNT(*) FILTER (WHERE amount <= 0) as invalid_amounts
FROM staged_onchain

UNION ALL

SELECT 
    'transactions_unified' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT txid) as unique_txids,
    COUNT(*) - COUNT(DISTINCT txid) as duplicate_txids,
    COUNT(*) FILTER (WHERE ts_utc IS NULL) as null_timestamps,
    COUNT(*) FILTER (WHERE amount <= 0) as invalid_amounts
FROM transactions_unified;

-- =============================================================================
-- SUMMARY VIEWS
-- =============================================================================

-- View for transaction summary by source
CREATE OR REPLACE VIEW transaction_summary_by_source AS
SELECT 
    domain,
    source,
    COUNT(*) as transaction_count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount,
    MIN(ts_utc) as earliest_transaction,
    MAX(ts_utc) as latest_transaction
FROM transactions_unified
GROUP BY domain, source
ORDER BY transaction_count DESC;

-- View for transaction summary by asset
CREATE OR REPLACE VIEW transaction_summary_by_asset AS
SELECT 
    base,
    quote,
    COUNT(*) as transaction_count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount,
    AVG(price) as avg_price
FROM transactions_unified
WHERE base IS NOT NULL AND quote IS NOT NULL
GROUP BY base, quote
ORDER BY transaction_count DESC;

-- View for monthly transaction volume
CREATE OR REPLACE VIEW monthly_transaction_volume AS
SELECT 
    year,
    month,
    domain,
    source,
    COUNT(*) as transaction_count,
    SUM(amount) as total_amount
FROM transactions_unified
GROUP BY year, month, domain, source
ORDER BY year, month, domain, source;

-- =============================================================================
-- CLEANUP FUNCTIONS
-- =============================================================================

-- Data cleanup functions (simplified for DuckDB)
-- Note: DuckDB doesn't support complex stored procedures with DEFAULT parameters
-- Cleanup would be done via Python scripts or manual SQL commands

-- =============================================================================
-- INITIALIZATION COMPLETE
-- =============================================================================

-- Log successful initialization
SELECT 'DuckDB initialization completed successfully' as status;
