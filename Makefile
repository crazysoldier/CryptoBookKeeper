# CryptoBookKeeper v0.1.0 - Makefile
# Orchestrates the complete data pipeline

.PHONY: help setup export-exchanges export-debank export-debank-incremental stage dbt excel all sync clean test troubleshoot

# Default target
help:
	@echo "CryptoBookKeeper v0.1.0 - Available Commands:"
	@echo ""
	@echo "Setup:"
	@echo "  setup                      - Set up Python environment and install dependencies"
	@echo ""
	@echo "Data Export (Full Refresh):"
	@echo "  export-exchanges           - Export ALL data from exchanges (CCXT)"
	@echo "  export-debank              - Export ALL on-chain data via DeBank API"
	@echo ""
	@echo "Data Export (Incremental - RECOMMENDED):"
	@echo "  export-debank-incremental  - Export only NEW on-chain data (saves DeBank units!)"
	@echo ""
	@echo "Data Processing:"
	@echo "  stage                      - Stage raw data in DuckDB and export to Parquet"
	@echo "  dbt                        - Run dbt models and tests"
	@echo ""
	@echo "Complete Pipeline:"
	@echo "  all                        - Full refresh: export all + stage + dbt"
	@echo "  sync                       - Incremental sync: new data only (FAST & CHEAP)"
	@echo ""
	@echo "Reports & Export:"
	@echo "  excel                      - Export transactions to Excel (beautiful & formatted!)"
	@echo ""
	@echo "Utilities:"
	@echo "  test                       - Run all tests"
	@echo "  clean                      - Clean up generated files"
	@echo "  troubleshoot               - Run troubleshooting checks"
	@echo "  help                       - Show this help message"
	@echo ""
	@echo "💡 TIP: Use 'make sync' for daily updates (saves 90%+ DeBank units!)"

# Setup Python environment
setup:
	@echo "Setting up Python environment..."
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	@echo "Setup completed successfully!"

# Export exchange data
export-exchanges:
	@echo "Exporting exchange data..."
	. venv/bin/activate && python scripts/export_exchanges.py
	@echo "Exchange data export completed!"

# Export on-chain data via DeBank API (FULL REFRESH)
export-debank:
	@echo "Exporting ALL on-chain data via DeBank API..."
	@echo "⚠️  This will fetch all transactions since START_TS (may use many DeBank units)"
	. venv/bin/activate && python scripts/export_debank.py
	@echo "DeBank data export completed!"

# Export on-chain data via DeBank API (INCREMENTAL - RECOMMENDED)
export-debank-incremental:
	@echo "Exporting NEW on-chain data via DeBank API (incremental mode)..."
	@echo "💰 This saves DeBank units by only fetching new transactions!"
	. venv/bin/activate && python scripts/export_debank.py --incremental
	@echo "DeBank incremental export completed!"

# Stage data in DuckDB
stage:
	@echo "Staging data in DuckDB..."
	. venv/bin/activate && python scripts/stage_duckdb.py
	@echo "Data staging completed!"

# Run dbt models
dbt:
	@echo "Running dbt models..."
	. venv/bin/activate && cd dbt && dbt run
	@echo "dbt models completed!"

# Run dbt tests
dbt-test:
	@echo "Running dbt tests..."
	. venv/bin/activate && cd dbt && dbt test
	@echo "dbt tests completed!"

# Run dbt docs
dbt-docs:
	@echo "Generating dbt docs..."
	. venv/bin/activate && cd dbt && dbt docs generate
	@echo "dbt docs generated!"

# Export to Excel
excel:
	@echo "📊 Exporting transactions to Excel..."
	. venv/bin/activate && python scripts/export_excel.py
	@echo "✅ Excel export completed! Check data/exports/ folder"

# Complete pipeline (FULL REFRESH)
all: export-exchanges export-debank stage dbt
	@echo "Complete pipeline finished successfully!"
	@echo "⚠️  Full refresh completed. For daily updates, use 'make sync' instead!"

# Incremental sync (RECOMMENDED for daily use)
sync: export-debank-incremental stage dbt
	@echo "💰 Incremental sync completed! (saved DeBank units by only fetching new data)"
	@echo "💡 TIP: Run 'make all' weekly for full validation"

# Run all tests
test: dbt-test
	@echo "All tests completed!"

# Clean up generated files
clean:
	@echo "Cleaning up generated files..."
	rm -rf data/raw/exchanges/*/trades/*.csv
	rm -rf data/raw/exchanges/*/deposits/*.csv
	rm -rf data/raw/exchanges/*/withdrawals/*.csv
	rm -rf data/raw/onchain/*/transfers/*.csv
	rm -rf data/raw/onchain/*/receipts/*.csv
	rm -rf data/curated/*.parquet
	rm -rf dbt/target/
	rm -rf dbt/dbt_packages/
	rm -rf logs/*.log
	rm -f data/cryptobookkeeper.duckdb
	@echo "Cleanup completed!"

# Run troubleshooting checks
troubleshoot:
	@echo "Running troubleshooting checks..."
	@echo "1. Checking Python version..."
	python3 --version
	@echo "2. Checking virtual environment..."
	@if [ -d "venv" ]; then echo "✅ Virtual environment exists"; else echo "❌ Virtual environment missing - run 'make setup'"; fi
	@echo "3. Checking .env file..."
	@if [ -f ".env" ]; then echo "✅ .env file exists"; else echo "❌ .env file missing - copy from .env.template"; fi
	@echo "4. Checking database path in .env..."
	@if grep -q "cryptobookkeeper.duckdb" .env 2>/dev/null; then echo "✅ Database path correct"; else echo "❌ Database path incorrect - should be cryptobookkeeper.duckdb"; fi
	@echo "5. Checking API configuration..."
	@if grep -q "COINBASE_API_KEY=" .env 2>/dev/null; then echo "✅ Coinbase API configured"; else echo "⚠️  Coinbase API not configured"; fi
	@echo "6. Checking data directories..."
	@mkdir -p data/raw data/curated logs
	@echo "✅ Data directories created"
	@echo "7. Checking dependencies..."
	@if [ -f "venv/bin/activate" ]; then . venv/bin/activate && python -c "import ccxt, duckdb, pandas" 2>/dev/null && echo "✅ Dependencies OK" || echo "❌ Dependencies missing - run 'make setup'"; fi
	@echo ""
	@echo "Troubleshooting complete! See TROUBLESHOOTING.md for detailed solutions."

# Development helpers
dev-setup: setup
	@echo "Development setup completed!"

dev-test: export-exchanges stage dbt-test
	@echo "Development test completed!"

# Production helpers
prod-setup: setup
	@echo "Production setup completed!"

prod-run: all
	@echo "Production run completed!"

# Monitoring helpers
status:
	@echo "Checking pipeline status..."
	@echo "Raw data files:"
	@find data/raw -name "*.csv" | wc -l | xargs echo "  CSV files:"
	@echo "Curated data files:"
	@find data/curated -name "*.parquet" | wc -l | xargs echo "  Parquet files:"
	@echo "Database size:"
	@du -h data/cryptobookkeeper.duckdb 2>/dev/null || echo "  Database not found"

# Backup helpers
backup:
	@echo "Creating backup..."
	@mkdir -p backups
	@tar -czf backups/cryptobookkeeper_$(shell date +%Y%m%d_%H%M%S).tar.gz data/ dbt/ scripts/ sql/ project-docs/ .env.template requirements.txt README.md
	@echo "Backup created in backups/"

# Restore helpers
restore:
	@echo "Available backups:"
	@ls -la backups/ 2>/dev/null || echo "No backups found"

# Environment helpers
env-check:
	@echo "Checking environment configuration..."
	@if [ -f .env ]; then \
		echo "✓ .env file exists"; \
	else \
		echo "✗ .env file missing - copy .env.template to .env and configure"; \
	fi
	@if [ -d venv ]; then \
		echo "✓ Python virtual environment exists"; \
	else \
		echo "✗ Python virtual environment missing - run 'make setup'"; \
	fi
	@if [ -f requirements.txt ]; then \
		echo "✓ requirements.txt exists"; \
	else \
		echo "✗ requirements.txt missing"; \
	fi

# Quick start for new users
quickstart: env-check setup
	@echo "Quick start completed!"
	@echo "Next steps:"
	@echo "1. Copy .env.template to .env and configure your API keys"
	@echo "2. Run 'make all' to execute the complete pipeline"
	@echo "3. Check the results in data/curated/"

# Documentation helpers
docs:
	@echo "Generating documentation..."
	@echo "Project documentation is available in project-docs/"
	@echo "dbt documentation: run 'make dbt-docs' then open dbt/target/index.html"

# Log helpers
logs:
	@echo "Recent logs:"
	@tail -n 20 logs/*.log 2>/dev/null || echo "No log files found"

# Database helpers
db-info:
	@echo "Database information:"
	@if [ -f data/cryptobookkeeper.duckdb ]; then \
		echo "✓ Database exists"; \
		du -h data/cryptobookkeeper.duckdb; \
	else \
		echo "✗ Database not found - run 'make stage' first"; \
	fi

# Performance helpers
perf-test:
	@echo "Running performance test..."
	@echo "This would run a performance test on the pipeline"
	@echo "Implementation pending"

# Security helpers
security-check:
	@echo "Running security checks..."
	@echo "Checking for exposed API keys..."
	@grep -r "api_key\|api_secret" . --exclude-dir=venv --exclude-dir=.git --exclude="*.log" || echo "No exposed API keys found"
	@echo "Security check completed!"
