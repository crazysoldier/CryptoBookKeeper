# CryptoBookKeeper - Troubleshooting Guide

## 🚨 Known Issues and Solutions

### 1. Database Path Configuration Issues

**Problem**: `Table with name raw_exchanges_trades does not exist!` errors in dbt.

**Root Cause**: The `.env` file contains the old database path `crypto_normalizer.duckdb` instead of `cryptobookkeeper.duckdb`.

**Solution**:
```bash
# Check your .env file
grep DUCKDB_PATH .env

# If it shows the old path, update it:
sed -i '' 's|DUCKDB_PATH=./data/crypto_normalizer.duckdb|DUCKDB_PATH=./data/cryptobookkeeper.duckdb|' .env

# Or manually edit .env and change:
# DUCKDB_PATH=./data/cryptobookkeeper.duckdb
```

### 2. Pandas/Numpy Compatibility Issues

**Problem**: `ValueError: numpy.dtype size changed, may indicate binary incompatibility` when running export scripts.

**Root Cause**: Incompatible versions of pandas and numpy.

**Solution**:
```bash
# Reinstall with compatible versions
. venv/bin/activate
pip uninstall pandas numpy
pip install pandas==2.3.3 numpy>=1.24.0,<2.0.0
```

### 3. dbt Model Conflicts

**Problem**: `infinite recursion detected` or `Existing object is of type View` errors.

**Root Cause**: dbt creates views that conflict with staging script's table creation.

**Solution**:
```bash
# Clean everything and run step by step
make clean
rm -f data/cryptobookkeeper.duckdb
make export-exchanges
make stage
make dbt
```

### 4. Missing On-chain Data Errors

**Problem**: `Table with name raw_onchain_transfers does not exist!` in dbt models.

**Root Cause**: On-chain data export failed (no RPC URL configured) but dbt models expect the tables.

**Solution**: 
- Configure `ETH_RPC_URL` in `.env` for on-chain data, OR
- The models are now fixed to handle missing on-chain data gracefully

### 5. Exchange API Configuration Issues

**Problem**: `COINBASE_API_KEY not configured properly` or similar API errors.

**Root Cause**: Missing or incorrect API credentials in `.env` file.

**Solution**:
```bash
# Copy template and configure
cp .env.template .env
# Edit .env with your actual API keys
nano .env
```

## 🔧 Setup Issues

### Virtual Environment Issues

**Problem**: `python3 -m venv venv` fails or packages don't install.

**Solution**:
```bash
# Ensure Python 3.11+ is installed
python3 --version

# Create fresh virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Permission Issues

**Problem**: Permission denied errors when creating directories or files.

**Solution**:
```bash
# Ensure proper permissions
chmod +x scripts/*.py
mkdir -p data/raw data/curated logs
```

## 📊 Data Quality Issues

### Empty Export Results

**Problem**: Export completes but shows "Total records exported: 0".

**Root Cause**: No data in the specified time range or API rate limits.

**Solution**:
- Check your `START_TS` in `.env` (try a wider date range)
- Verify your API keys have the right permissions
- Check exchange-specific rate limits

### Staging Failures

**Problem**: Staging fails with "Failed to load" errors.

**Root Cause**: CSV files are corrupted or have invalid data.

**Solution**:
```bash
# Check CSV files
ls -la data/raw/exchanges/*/trades/
head -5 data/raw/exchanges/coinbase/trades/2024-01.csv

# Clean and retry
make clean
make export-exchanges
make stage
```

## 🚀 Performance Issues

### Slow Export

**Problem**: Export takes a very long time.

**Root Cause**: Large date ranges or slow API responses.

**Solution**:
- Reduce date range in `START_TS`
- Check your internet connection
- Consider running during off-peak hours

### Memory Issues

**Problem**: Out of memory errors during staging.

**Root Cause**: Large datasets exceeding available memory.

**Solution**:
```bash
# Increase memory limit in dbt/profiles.yml
memory_limit: '8GB'  # or higher
```

## 🔍 Debugging Commands

### Check Database Contents
```bash
# Connect to DuckDB and inspect
. venv/bin/activate
python -c "
import duckdb
conn = duckdb.connect('data/cryptobookkeeper.duckdb')
print('Tables:', conn.execute('SHOW TABLES').fetchall())
print('Trades count:', conn.execute('SELECT COUNT(*) FROM raw_exchanges_trades').fetchone())
"
```

### Check dbt Models
```bash
cd dbt
dbt debug  # Check connection
dbt compile  # Check for syntax errors
dbt run --select raw_exchanges_trades  # Run specific model
```

### Check Logs
```bash
# View detailed logs
tail -f logs/export_exchanges.log
tail -f logs/stage_duckdb.log
```

## 📞 Getting Help

If you encounter issues not covered here:

1. Check the logs in `logs/` directory
2. Run `make clean` and try again
3. Verify your `.env` configuration
4. Check the GitHub issues page
5. Create a new issue with:
   - Your operating system
   - Python version
   - Full error message
   - Steps to reproduce

## ✅ Verification Checklist

Before reporting issues, verify:

- [ ] Python 3.11+ installed
- [ ] Virtual environment activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with correct paths
- [ ] API keys are valid and have proper permissions
- [ ] No conflicting processes using the same database
- [ ] Sufficient disk space available
- [ ] Internet connection stable

---

**Remember**: Always run `make clean` before troubleshooting to ensure a fresh start!
