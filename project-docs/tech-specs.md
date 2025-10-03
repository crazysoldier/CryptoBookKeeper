# Crypto Normalizer - Technische Spezifikationen

## System-Architektur

### Komponenten-Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                    Crypto Normalizer System                     │
├─────────────────────────────────────────────────────────────────┤
│  Data Sources Layer                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ Exchanges   │  │ Blockchain  │  │ Metadata    │           │
│  │ (CCXT)      │  │ (web3.py)   │  │ (JSON)      │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
├─────────────────────────────────────────────────────────────────┤
│  Data Processing Layer                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ Export      │  │ Staging     │  │ Transform   │           │
│  │ Scripts     │  │ (DuckDB)    │  │ (dbt)       │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
├─────────────────────────────────────────────────────────────────┤
│  Storage Layer                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ Raw Data    │  │ Staged Data │  │ Curated     │           │
│  │ (CSV)       │  │ (Parquet)   │  │ (Parquet)   │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Datenfluss

1. **Extract**: APIs → Raw CSV Files
2. **Load**: CSV → DuckDB Tables
3. **Transform**: Raw → Staged → Curated
4. **Store**: Parquet Files für Analytics

## Technologie-Details

### Python-Stack

#### Core Libraries
```python
# Data Processing
duckdb>=0.10.0,!=0.10.3    # OLAP Database
polars==0.20.31             # Fast DataFrame

# Exchange Integration
ccxt==4.3.74               # Exchange APIs

# Blockchain Integration
web3>=6.0,<7.0            # Ethereum/EVM
eth-typing>=3.0            # Type Definitions
hexbytes>=1.0              # Hex Utilities

# Data Modeling
dbt-core>=1.7,<1.9         # Data Modeling
dbt-duckdb>=1.7,<1.9      # DuckDB Adapter

# Utilities
python-dotenv==1.0.1       # Environment Variables
tqdm==4.66.4               # Progress Bars
requests==2.32.3           # HTTP Client
```

#### Development Tools
```python
ruff==0.5.0                # Linting
pre-commit==3.7.1          # Git Hooks
```

### Datenbank-Schema

#### Raw Exchange Data Schema
```sql
CREATE TABLE raw_exchanges_trades (
    source VARCHAR,           -- Exchange name
    exchange VARCHAR,         -- Exchange identifier
    account VARCHAR,          -- Account identifier
    txid VARCHAR,             -- Transaction ID
    orderid VARCHAR,          -- Order ID
    datetime TIMESTAMP,       -- UTC timestamp
    base VARCHAR,             -- Base asset
    quote VARCHAR,            -- Quote asset
    side VARCHAR,             -- buy/sell
    amount DECIMAL(38,18),    -- Amount
    price DECIMAL(38,18),     -- Price
    fee_currency VARCHAR,     -- Fee currency
    fee_amount DECIMAL(38,18), -- Fee amount
    address VARCHAR,          -- Address (if applicable)
    status VARCHAR,           -- Status
    raw_json JSON             -- Raw API response
);
```

#### Raw On-Chain Data Schema
```sql
CREATE TABLE raw_onchain_transfers (
    tx_hash VARCHAR,          -- Transaction hash
    log_index INTEGER,        -- Log index
    contract_address VARCHAR, -- Contract address
    from_address VARCHAR,     -- From address
    to_address VARCHAR,       -- To address
    value DECIMAL(38,18),     -- Transfer value
    token_symbol VARCHAR,     -- Token symbol
    token_decimal INTEGER,    -- Token decimals
    block_number BIGINT,      -- Block number
    block_timestamp TIMESTAMP, -- Block timestamp
    chain VARCHAR,            -- Chain name
    raw_json JSON             -- Raw data
);
```

#### Unified Transaction Schema
```sql
CREATE TABLE transactions_unified (
    domain VARCHAR,           -- 'exchange' or 'onchain'
    source VARCHAR,           -- Source identifier
    ts_utc TIMESTAMP,         -- UTC timestamp
    txid VARCHAR,             -- Unique transaction ID
    base VARCHAR,             -- Base asset
    quote VARCHAR,            -- Quote asset
    side VARCHAR,             -- Transaction side
    amount DECIMAL(38,18),    -- Amount
    price DECIMAL(38,18),     -- Price (if applicable)
    fee_ccy VARCHAR,         -- Fee currency
    fee_amt DECIMAL(38,18),   -- Fee amount
    addr_from VARCHAR,        -- From address
    addr_to VARCHAR,          -- To address
    chain VARCHAR,            -- Chain name
    token_symbol VARCHAR,     -- Token symbol
    token_decimal INTEGER,    -- Token decimals
    raw_json JSON             -- Raw data
);
```

### API-Integration

#### Exchange APIs (CCXT)
```python
# Supported Exchanges
SUPPORTED_EXCHANGES = [
    'binance', 'kraken', 'coinbase', 'bitfinex',
    'huobi', 'okx', 'bybit', 'kucoin', 'gate'
]

# Rate Limiting
RATE_LIMITS = {
    'binance': 1200,    # requests per minute
    'kraken': 60,       # requests per minute
    'coinbase': 100,    # requests per minute
}
```

#### Blockchain APIs (web3.py)
```python
# Ethereum RPC Configuration
ETH_RPC_CONFIG = {
    'url': 'https://mainnet.infura.io/v3/YOUR_PROJECT_ID',
    'timeout': 30,
    'retries': 3
}

# Supported Chains
SUPPORTED_CHAINS = [
    'ethereum', 'polygon', 'arbitrum', 'optimism'
]
```

### Datenverarbeitung

#### Export-Pipeline
```python
# Exchange Export Flow
def export_exchanges():
    for exchange in EXCHANGES:
        # 1. Authenticate
        client = ccxt.exchange({'apiKey': key, 'secret': secret})
        
        # 2. Fetch data with pagination
        trades = fetch_my_trades(client, start_ts)
        deposits = fetch_deposits(client, start_ts)
        withdrawals = fetch_withdrawals(client, start_ts)
        
        # 3. Normalize timestamps
        normalize_timestamps(data)
        
        # 4. Save to CSV
        save_to_csv(data, f"data/raw/exchanges/{exchange}/")
```

#### Staging-Pipeline
```python
# DuckDB Staging Flow
def stage_duckdb():
    # 1. Connect to DuckDB
    conn = duckdb.connect(DB_PATH)
    
    # 2. Load raw CSVs
    raw_data = conn.execute("SELECT * FROM read_csv_auto('data/raw/**/*.csv')")
    
    # 3. Type casting and cleaning
    staged_data = clean_and_cast(raw_data)
    
    # 4. Save as Parquet
    staged_data.to_parquet("data/curated/", partition_by=['year', 'month'])
```

### dbt-Modellierung

#### Raw Models
```sql
-- models/raw/raw_exchanges_trades.sql
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
FROM {{ source('raw', 'exchanges_trades') }}
```

#### Curated Models
```sql
-- models/curated/tx_unified.sql
SELECT
    'exchange' as domain,
    source,
    datetime as ts_utc,
    txid,
    base,
    quote,
    side,
    amount,
    price,
    fee_currency as fee_ccy,
    fee_amount as fee_amt,
    NULL as addr_from,
    NULL as addr_to,
    NULL as chain,
    NULL as token_symbol,
    NULL as token_decimal,
    raw_json
FROM {{ ref('raw_exchanges_trades') }}

UNION ALL

SELECT
    'onchain' as domain,
    chain as source,
    block_timestamp as ts_utc,
    tx_hash as txid,
    NULL as base,
    NULL as quote,
    'transfer' as side,
    value as amount,
    NULL as price,
    NULL as fee_ccy,
    NULL as fee_amt,
    from_address as addr_from,
    to_address as addr_to,
    chain,
    token_symbol,
    token_decimal,
    raw_json
FROM {{ ref('raw_onchain_transfers') }}
```

### Performance-Optimierungen

#### DuckDB-Konfiguration
```sql
-- sql/duckdb_init.sql
PRAGMA memory_limit='4GB';
PRAGMA threads=4;
PRAGMA enable_progress_bar=true;
PRAGMA enable_verification=false;
```

#### Parquet-Optimierungen
```python
# Partitionierung nach Zeit
df.write_parquet(
    "data/curated/",
    partition_by=['year', 'month'],
    compression='snappy'
)
```

#### dbt-Optimierungen
```yaml
# dbt_project.yml
models:
  cryptobookkeeper:
    staging:
      materialized: table
    curated:
      materialized: table
      indexes:
        - ['ts_utc']
        - ['domain', 'source']
```

### Fehlerbehandlung

#### API-Fehler
```python
def handle_api_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except RateLimitError:
                time.sleep(60)  # Wait 1 minute
            except APIError as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
    return wrapper
```

#### Datenvalidierung
```python
def validate_transaction(row):
    required_fields = ['txid', 'ts_utc', 'amount']
    for field in required_fields:
        if not row.get(field):
            raise ValidationError(f"Missing required field: {field}")
    
    if row['amount'] <= 0:
        raise ValidationError("Amount must be positive")
```

### Monitoring und Logging

#### Logging-Konfiguration
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cryptobookkeeper.log'),
        logging.StreamHandler()
    ]
)
```

#### Metriken
```python
# Export-Metriken
metrics = {
    'total_transactions': 0,
    'api_calls': 0,
    'errors': 0,
    'processing_time': 0
}
```

### Sicherheit

#### API-Key-Management
```python
# Sichere Speicherung von Credentials
def load_credentials():
    return {
        'api_key': os.getenv('API_KEY'),
        'api_secret': os.getenv('API_SECRET')
    }
```

#### Datenverschlüsselung
```python
# Sensitive Daten verschlüsseln
def encrypt_sensitive_data(data):
    # Implementierung der Verschlüsselung
    pass
```

### Deployment

#### Docker-Support
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "scripts/export_exchanges.py"]
```

#### CI/CD-Pipeline
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: dbt test
```

### Skalierung

#### Horizontale Skalierung
- **Multi-Exchange**: Parallele Export-Prozesse
- **Multi-Chain**: Separate Blockchain-Exports
- **Distributed Processing**: Dask oder Ray für große Datenmengen

#### Vertikale Skalierung
- **Memory**: Erhöhung des RAM-Limits
- **CPU**: Multi-Threading für parallele Verarbeitung
- **Storage**: SSD für bessere I/O-Performance
