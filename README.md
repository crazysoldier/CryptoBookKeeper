# CryptoBookKeeper

**Version 0.1.0** - Transaction Normalization Stage

A comprehensive cryptocurrency bookkeeping application that normalizes transaction data from exchanges and on-chain sources into a unified format using DuckDB and dbt. Currently focused on data normalization with plans for full bookkeeping features.

## 🎯 Overview

CryptoBookKeeper is designed to be a comprehensive cryptocurrency bookkeeping solution. Currently in its initial phase, it focuses on normalizing transaction data from exchanges and on-chain sources into a unified format using DuckDB and dbt.

**Current Stage (v0.1.0)**: Data normalization and unified transaction model
**Future Plans**: Full bookkeeping features, tax reporting, portfolio tracking, and more.

## 🏗️ Architecture

```
Raw Data Sources → Export Scripts → DuckDB → dbt Models → Unified Schema
     ↓                ↓              ↓         ↓           ↓
- Exchanges      - CCXT API     - Staging   - Raw Models  - transactions_unified
- On-chain       - DeBank API   - Parquet   - Curated     - Standardized format
                 - Scam Filter
```

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Clone and setup
git clone https://github.com/crazysoldier/CryptoBookKeeper.git
cd CryptoBookKeeper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy and edit environment template
cp .env.template .env

# Edit .env with your API keys and settings
nano .env
```

### 3. Run Pipeline
```bash
# Full refresh (first time or complete re-sync)
make all

# Incremental sync (recommended for daily updates - saves API costs!)
make sync

# Or run individual steps
make setup                    # Setup environment
make export-exchanges         # Export exchange data
make export-debank            # Export on-chain data (all transactions)
make export-debank-incremental # Export only new on-chain data
make stage                    # Stage data in DuckDB
make dbt                      # Run dbt transformations
```

## 📁 Project Structure

```
├── project-docs/           # Documentation
│   ├── overview.md
│   ├── requirements.md
│   ├── tech-specs.md
│   └── data-dictionary.md
├── scripts/               # Export scripts
│   ├── export_exchanges.py
│   ├── export_onchain_eth.py
│   └── stage_duckdb.py
├── sql/                   # Database initialization
│   └── duckdb_init_simple.sql
├── dbt/                   # dbt project
│   ├── models/
│   │   ├── raw/          # Raw data models
│   │   └── curated/     # Curated models
│   └── dbt_project.yml
├── data/                  # Data storage
│   ├── raw/              # Raw CSV exports
│   └── curated/          # Processed Parquet files
└── Makefile              # Orchestration
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Time range for data collection
START_TS=2024-01-01T00:00:00Z

# Exchanges to export (comma-separated)
EXCHANGES=coinbase,binance,kraken

# Exchange API credentials
COINBASE_API_KEY=your_key_here
COINBASE_SECRET=your_secret_here
COINBASE_PASSPHRASE=your_passphrase_here

# DeBank Cloud API (for on-chain data)
DEBANK_API_KEY=your_debank_api_key

# Chains to monitor (comma-separated)
# See DEBANK_CHAINS.md for all 123 supported chains
DEBANK_CHAINS=eth,bsc,matic,arb,op,base,avax

# Scam token filtering (recommended: true)
# Filters out spam/airdrop tokens marked by DeBank
DEBANK_FILTER_SCAMS=true

# Ethereum addresses to track (comma-separated, lowercase)
EVM_ADDRESSES=0x1234...,0x5678...
```

## 📊 Unified Transaction Schema

All transactions are normalized into a unified schema:

| Column | Type | Description |
|--------|------|-------------|
| `domain` | VARCHAR | Data source (exchanges, onchain) |
| `source` | VARCHAR | Specific source (coinbase, ethereum) |
| `ts_utc` | TIMESTAMP | UTC timestamp |
| `txid` | VARCHAR | Transaction ID |
| `base` | VARCHAR | Base currency |
| `quote` | VARCHAR | Quote currency |
| `side` | VARCHAR | buy/sell/transfer |
| `amount` | DECIMAL | Transaction amount |
| `price` | DECIMAL | Price per unit |
| `fee_ccy` | VARCHAR | Fee currency |
| `fee_amt` | DECIMAL | Fee amount |
| `addr_from` | VARCHAR | From address |
| `addr_to` | VARCHAR | To address |
| `chain` | VARCHAR | Blockchain |
| `token_symbol` | VARCHAR | Token symbol |
| `token_decimal` | INTEGER | Token decimals |
| `raw_json` | JSON | Original raw data |

## 🛠️ Technology Stack

- **Python 3.11+** - Core language
- **CCXT** - Exchange API integration
- **DeBank Cloud API** - On-chain data across 123 chains
- **DuckDB** - In-process OLAP database with upsert support
- **Polars** - Fast DataFrame processing
- **dbt** - Data transformation with incremental models
- **Parquet** - Columnar storage format

## 📈 Available Commands

```bash
make setup                    # Setup virtual environment and dependencies
make export-exchanges         # Export data from exchanges
make export-debank            # Export on-chain data (full refresh)
make export-debank-incremental # Export only new on-chain data (saves API costs)
make stage                    # Stage data in DuckDB with upsert
make dbt                      # Run dbt transformations
make all                      # Full pipeline (full refresh)
make sync                     # Incremental pipeline (recommended for daily use)
make clean                    # Clean generated files
make test                     # Run tests
```

## 🔍 Data Quality & Filtering

The pipeline includes comprehensive data quality checks:
- **Scam Token Filtering**: Automatically filters out spam/airdrop tokens marked by DeBank (60%+ of transactions on some chains!)
- **Timestamp normalization** to UTC
- **Type casting and validation**
- **Duplicate detection** via DuckDB upsert (INSERT OR REPLACE)
- **Missing value handling**
- **Schema validation**
- **Incremental loading** to save API costs and improve performance

## 📝 Known Limitations

- **Rate Limits**: Exchange APIs have rate limits
- **Historical Data**: Limited by exchange API availability
- **DeBank API Costs**: DeBank Cloud API charges per API unit (use incremental mode!)
- **Data Volume**: Large datasets require significant storage
- **Scam Filtering**: Only works for chains supported by DeBank (123 chains)

## ⚠️ Known Issues

- **Database Path**: Ensure `.env` uses `cryptobookkeeper.duckdb` (not `crypto_normalizer.duckdb`)
- **Pandas Compatibility**: May need `pip install pandas==2.3.3 numpy>=1.24.0,<2.0.0`
- **dbt Conflicts**: Run `make clean` before `make all` to avoid view/table conflicts
- **On-chain Models**: 2/7 dbt models fail without on-chain data (expected)

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions.

## 🔗 Blockchain Data Sources

### DeBank Cloud API (Recommended)

We use **DeBank Cloud API** for comprehensive on-chain data across multiple EVM chains.

**Setup:**
1. Sign up at: https://cloud.debank.com/
2. Purchase units (pay with USDC)
3. Copy your Access Key
4. Add to `.env`: `DEBANK_API_KEY=your_access_key`
5. Add chains: `DEBANK_CHAINS=eth,matic,arb,op,base,avax`
6. Enable scam filtering: `DEBANK_FILTER_SCAMS=true` (recommended)

**Scam Token Filtering:**

CryptoBookKeeper automatically filters out spam and scam tokens using DeBank's `is_scam` flag:

```bash
# Enable scam filtering (default: true)
DEBANK_FILTER_SCAMS=true

# Disable to keep all transactions (not recommended)
DEBANK_FILTER_SCAMS=false
```

**Why filter scams?**
- **60%+ of transactions** on some chains (esp. Polygon) are spam tokens
- **100% of Polygon transactions** in test data were scam airdrops
- **Cleaner data** = better insights and reports
- **Saves time** analyzing only legitimate transactions

**Example Results:**
```
Chain    Total Fetched  Scams Filtered  Clean Data
---------------------------------------------------
ETH              20           1 (5%)         19
MATIC            20          20 (100%)        0
ARB              20          10 (50%)        10
OP               20          17 (85%)         3
BASE             20          13 (65%)         7
AVAX              1           0 (0%)          1
---------------------------------------------------
TOTAL           101          61 (60%)        40
```

**Important:** 
- API endpoint: `https://pro-openapi.debank.com/v1`
- Authentication: Use `AccessKey` header (not `Bearer`)
- Rate limit: 100 requests/second

See [DEBANK_SETUP.md](DEBANK_SETUP.md) for detailed setup instructions.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is open source. See LICENSE file for details.

## 🆘 Support

For issues and questions:
- Check the documentation in `project-docs/`
- Review the Makefile for available commands
- Check logs in `logs/` directory

---

## 🗺️ Roadmap

### Version 0.1.0 (Current)
- ✅ Data normalization from exchanges and on-chain
- ✅ Unified transaction schema
- ✅ DuckDB + dbt pipeline
- ✅ Basic data quality checks

### Version 0.2.0 (Planned)
- 📊 Portfolio tracking and analytics
- 📈 Performance metrics and reporting
- 🔄 Automated data refresh
- 📱 Basic web interface

### Version 0.3.0 (Future)
- 📋 Tax reporting and compliance
- 🏦 Multi-exchange portfolio aggregation
- 📊 Advanced analytics and insights
- 🔐 Enhanced security features

### Version 1.0.0 (Vision)
- 🎯 Complete bookkeeping solution
- 📊 Professional reporting suite
- 🔄 Real-time data synchronization
- 📱 Mobile and web applications

---

**Built with ❤️ for the crypto community**
