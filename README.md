# Crypto Transaction Normalizer

A minimal project for normalizing cryptocurrency transaction data from exchanges and on-chain sources into a unified format using DuckDB and dbt.

## 🎯 Overview

This project exports exchange data via CCXT and EVM on-chain data via web3.py, then normalizes everything in DuckDB/Parquet and creates a unified transaction model using dbt.

## 🏗️ Architecture

```
Raw Data Sources → Export Scripts → DuckDB → dbt Models → Unified Schema
     ↓                ↓              ↓         ↓           ↓
- Exchanges      - CCXT API     - Staging   - Raw Models  - transactions_unified
- On-chain       - web3.py      - Parquet   - Curated     - Standardized format
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
# Run everything
make all

# Or run individual steps
make setup          # Setup environment
make export-exchanges  # Export exchange data
make export-eth     # Export Ethereum on-chain data
make stage          # Stage data in DuckDB
make dbt            # Run dbt transformations
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

# Ethereum RPC endpoint
ETH_RPC_URL=https://eth-mainnet.alchemyapi.io/v2/your_key

# Ethereum addresses to track
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
- **web3.py** - Ethereum blockchain access
- **DuckDB** - In-process OLAP database
- **Polars** - Fast DataFrame processing
- **dbt** - Data transformation
- **Parquet** - Columnar storage format

## 📈 Available Commands

```bash
make setup              # Setup virtual environment and dependencies
make export-exchanges   # Export data from exchanges
make export-eth         # Export Ethereum on-chain data
make stage              # Stage data in DuckDB
make dbt                # Run dbt transformations
make all                # Run complete pipeline
make clean              # Clean generated files
make test               # Run tests
```

## 🔍 Data Quality

The pipeline includes comprehensive data quality checks:
- Timestamp normalization to UTC
- Type casting and validation
- Duplicate detection
- Missing value handling
- Schema validation

## 📝 Known Limitations

- **Rate Limits**: Exchange APIs have rate limits
- **Historical Data**: Limited by exchange API availability
- **On-chain Costs**: Ethereum RPC calls may have costs
- **Data Volume**: Large datasets require significant storage

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

**Built with ❤️ for the crypto community**
