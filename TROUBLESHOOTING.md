# CryptoBookKeeper - Troubleshooting Guide

## 🚨 Known Issues and Solutions

### 1. Database Path Configuration Issues

**Problem**: `Table with name raw_exchanges_trades does not exist!` errors.

**Root Cause**: Database not initialized or wrong database path in `.env`.

**Solution**:
```bash
# Check your .env file
grep DUCKDB_PATH .env

# Should be: DUCKDB_PATH=./data/cryptobookkeeper.duckdb
# If wrong, manually edit .env and fix the path

# Then rebuild:
make clean
make all
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

### 3. Database Conflicts

**Problem**: `infinite recursion detected` or `Existing object is of type View` errors.

**Root Cause**: Database schema conflicts or corrupted database.

**Solution**:
```bash
# Clean everything and run step by step
make clean
rm -f data/cryptobookkeeper.duckdb
make export-exchanges
make stage
```

### 4. Missing On-chain Data Errors

**Problem**: `Table with name raw_onchain_transfers does not exist!` errors.

**Root Cause**: On-chain data export failed (no DeBank API configured) but staging expects the tables.

**Solution**: 
- Configure `DEBANK_API_KEY` in `.env` for on-chain data, OR
- The staging script now handles missing on-chain data gracefully

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
# Increase DuckDB memory limit in .env
DUCKDB_MEMORY_LIMIT=8GB
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

### Check Database Schema
```bash
# Connect to DuckDB and inspect schema
. venv/bin/activate
python -c "
import duckdb
conn = duckdb.connect('data/cryptobookkeeper.duckdb')
print('Tables:', conn.execute('SHOW TABLES').fetchall())
print('Schema:', conn.execute('DESCRIBE transactions_unified').fetchall())
"
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
