# Incremental Data Loading Strategy

## 🎯 Current Problem

**Current Behavior (Full Refresh):**
- ❌ Every run exports ALL transactions from `START_TS`
- ❌ Wastes API rate limits (Coinbase, DeBank)
- ❌ Wastes DeBank units (costs money!)
- ❌ Slow for large datasets
- ❌ No deduplication logic

**Issues:**
- DeBank API: 100 requests/second, but each call costs units
- Exchange APIs: Rate limited (Coinbase: 10 requests/second)
- Re-fetching the same data repeatedly is inefficient

## 🚀 Proposed Solution: Incremental Loading

### Strategy Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Smart Export (Only New Data)                     │
│  - Track last successful export timestamp per source        │
│  - Only fetch transactions after last_sync_time             │
│  - Store metadata in DuckDB (sync_log table)                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: Staging with Upsert                               │
│  - Use UNIQUE constraints on (source, txid)                 │
│  - INSERT OR REPLACE to handle updates                      │
│  - Keep historical versions in audit table (optional)       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: dbt Incremental Materialization                   │
│  - Use dbt incremental models                               │
│  - Only process new/changed records                         │
│  - Configurable merge strategy per model                    │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Implementation Plan

### 1. Sync State Management

Create `sync_log` table to track what's been synced:

```sql
CREATE TABLE IF NOT EXISTS sync_log (
    source VARCHAR PRIMARY KEY,          -- e.g., 'coinbase', 'debank_eth'
    last_sync_ts TIMESTAMP,              -- Last successful sync timestamp
    last_txid VARCHAR,                   -- Last transaction ID (for pagination)
    sync_count INTEGER,                  -- Number of records in last sync
    sync_status VARCHAR,                 -- 'success', 'partial', 'failed'
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2. Export Scripts Enhancement

**A. Exchange Export (export_exchanges.py)**

```python
def get_last_sync_timestamp(conn, source: str) -> datetime:
    """Get last successful sync timestamp for a source."""
    result = conn.execute(
        "SELECT last_sync_ts FROM sync_log WHERE source = ?",
        [source]
    ).fetchone()
    
    if result:
        return result[0]
    else:
        # First run, use START_TS from .env
        return datetime.fromisoformat(os.getenv('START_TS'))

def export_trades_incremental(exchange, client):
    """Export only new trades since last sync."""
    source = f"{exchange}_trades"
    last_sync = get_last_sync_timestamp(conn, source)
    
    # Fetch only new trades
    trades = client.fetch_my_trades(
        since=int(last_sync.timestamp() * 1000),
        limit=1000
    )
    
    # Save to CSV
    save_to_csv(trades, source)
    
    # Update sync log
    if trades:
        conn.execute("""
            INSERT OR REPLACE INTO sync_log 
            (source, last_sync_ts, sync_count, sync_status)
            VALUES (?, ?, ?, 'success')
        """, [source, datetime.now(), len(trades)])
```

**B. DeBank Export (export_debank.py)**

```python
def export_incremental(address: str, chain: str):
    """Export only new transactions since last sync."""
    source = f"debank_{chain}"
    last_sync = get_last_sync_timestamp(conn, source)
    
    # DeBank API: Get transactions after last_sync
    # Use pagination with start_time parameter
    transactions = []
    page = 0
    
    while True:
        batch = get_user_history(
            address=address,
            chain_id=chain,
            start_time=int(last_sync.timestamp()),
            page_count=100
        )
        
        if not batch:
            break
            
        # Filter transactions newer than last_sync
        new_txs = [tx for tx in batch if tx['time_at'] > last_sync.timestamp()]
        transactions.extend(new_txs)
        
        if len(batch) < 100:  # Last page
            break
        page += 1
    
    # Save and update sync log
    save_to_csv(transactions, source)
    update_sync_log(source, len(transactions))
```

### 3. DuckDB Staging with Upsert

**A. Add Unique Constraints**

```sql
-- Modify raw tables to have unique constraints
CREATE TABLE IF NOT EXISTS raw_exchanges_trades (
    source VARCHAR,
    txid VARCHAR,
    datetime TIMESTAMP,
    base VARCHAR,
    quote VARCHAR,
    side VARCHAR,
    amount DOUBLE,
    price DOUBLE,
    raw_json VARCHAR,
    PRIMARY KEY (source, txid)  -- Composite key
);

CREATE TABLE IF NOT EXISTS raw_onchain_transfers (
    chain VARCHAR,
    tx_hash VARCHAR,
    block_timestamp TIMESTAMP,
    from_address VARCHAR,
    to_address VARCHAR,
    token_symbol VARCHAR,
    value DOUBLE,
    raw_json VARCHAR,
    PRIMARY KEY (chain, tx_hash)  -- Composite key
);
```

**B. Use INSERT OR REPLACE in stage_duckdb.py**

```python
def load_exchange_data_incremental(self):
    """Load exchange data with upsert logic."""
    for file_path in csv_files:
        df = pd.read_csv(file_path)
        
        # Register DataFrame
        self.conn.register('temp_df', df)
        
        # Upsert: INSERT OR REPLACE
        self.conn.execute(f"""
            INSERT OR REPLACE INTO raw_exchanges_trades
            SELECT * FROM temp_df
        """)
```

### 4. dbt Incremental Models

**A. Modify dbt models to use incremental materialization**

`dbt/models/curated/tx_unified.sql`:

```sql
{{
    config(
        materialized='incremental',
        unique_key=['domain', 'source', 'txid'],
        on_schema_change='sync_all_columns'
    )
}}

WITH exchanges AS (
    SELECT * FROM {{ ref('staged_exchanges') }}
    {% if is_incremental() %}
        -- Only process new records
        WHERE ts_utc > (SELECT MAX(ts_utc) FROM {{ this }})
    {% endif %}
),

onchain AS (
    SELECT * FROM {{ ref('staged_onchain') }}
    {% if is_incremental() %}
        WHERE ts_utc > (SELECT MAX(ts_utc) FROM {{ this }})
    {% endif %}
)

SELECT * FROM exchanges
UNION ALL
SELECT * FROM onchain
```

**B. Incremental merge strategies**

```yaml
# dbt/models/curated/schema.yml
models:
  - name: tx_unified
    config:
      materialized: incremental
      unique_key: ['domain', 'source', 'txid']
      incremental_strategy: merge  # or 'delete+insert', 'append'
      
  - name: daily_balances
    config:
      materialized: incremental
      unique_key: ['date', 'token']
      incremental_strategy: delete+insert
```

### 5. Makefile Updates

```makefile
# Full refresh (existing behavior)
all: export-exchanges export-debank stage dbt

# Incremental update (NEW)
sync: export-exchanges-incremental export-debank-incremental stage-incremental dbt-incremental

# Export only new data
export-exchanges-incremental:
	@echo "Exporting only new exchange data..."
	. venv/bin/activate && python scripts/export_exchanges.py --incremental

export-debank-incremental:
	@echo "Exporting only new DeBank data..."
	. venv/bin/activate && python scripts/export_debank.py --incremental

# Stage with upsert
stage-incremental:
	@echo "Staging with upsert logic..."
	. venv/bin/activate && python scripts/stage_duckdb.py --incremental

# dbt incremental run
dbt-incremental:
	@echo "Running dbt incremental models..."
	. venv/bin/activate && cd dbt && dbt run --select state:modified+
```

## 🎯 Benefits

### Cost Savings
- **DeBank Units**: Only fetch new transactions (save 90%+ units)
- **Rate Limits**: Respect limits, avoid throttling
- **Time**: Faster syncs (seconds instead of minutes)

### Data Quality
- **Deduplication**: Unique keys prevent duplicates
- **Consistency**: Upsert handles updates (e.g., pending → confirmed)
- **Audit Trail**: Optional versioning for compliance

### Performance
- **Incremental Processing**: Only process new data
- **Efficient Storage**: Parquet partitioning by month
- **Fast Queries**: Indexed on timestamp and source

## 📋 Implementation Priority

### Phase 1 (High Priority - Cost Savings)
1. ✅ Add sync_log table to DuckDB
2. ✅ Implement incremental export for DeBank (biggest cost)
3. ✅ Add `--incremental` flag to export scripts
4. ✅ Update staging to use INSERT OR REPLACE

### Phase 2 (Medium Priority - Data Quality)
1. ✅ Add unique constraints to raw tables
2. ✅ Implement deduplication logic
3. ✅ Add data validation checks
4. ✅ Create audit/history tables

### Phase 3 (Lower Priority - Optimization)
1. ✅ Convert dbt models to incremental
2. ✅ Add partitioning strategy
3. ✅ Implement backfill logic
4. ✅ Add monitoring/alerting

## 🔄 Recommended Workflow

### Daily Sync (Automated)
```bash
# Cron job: Run every 6 hours
0 */6 * * * cd /path/to/project && make sync
```

### Weekly Full Refresh (Validation)
```bash
# Run on Sunday at 2 AM
0 2 * * 0 cd /path/to/project && make clean && make all
```

### Manual Backfill (One-time)
```bash
# Backfill specific date range
START_TS=2024-01-01T00:00:00Z END_TS=2024-06-30T23:59:59Z make all
```

## 📊 Monitoring

Track sync performance in DuckDB:

```sql
-- View sync history
SELECT 
    source,
    last_sync_ts,
    sync_count,
    sync_status,
    updated_at
FROM sync_log
ORDER BY updated_at DESC;

-- Calculate cost savings
SELECT 
    source,
    SUM(sync_count) as total_records,
    COUNT(*) as sync_runs,
    AVG(sync_count) as avg_per_sync
FROM sync_log
WHERE sync_status = 'success'
GROUP BY source;
```

## 🎓 Best Practices

1. **Always use incremental for DeBank** (costs money)
2. **Use full refresh weekly** for data validation
3. **Monitor sync_log table** for failures
4. **Set appropriate lookback windows** (e.g., 24 hours overlap)
5. **Handle API errors gracefully** (retry with backoff)
6. **Log all API calls** for debugging
7. **Version your data models** in dbt

## 🔗 Resources

- [dbt Incremental Models](https://docs.getdbt.com/docs/build/incremental-models)
- [DuckDB UPSERT](https://duckdb.org/docs/sql/statements/insert.html)
- [DeBank API Docs](https://docs.cloud.debank.com/)

---

**Next Steps**: Implement Phase 1 to start saving DeBank units immediately! 💰
