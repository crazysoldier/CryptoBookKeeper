#!/usr/bin/env python3
"""
Crypto Normalizer - DuckDB Staging Script

Loads raw CSV data into DuckDB, performs type casting and cleaning,
and saves as optimized Parquet files for analytics.
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
import duckdb
from dotenv import load_dotenv
from tqdm import tqdm

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'logs/stage_duckdb.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DuckDBStager:
    """Main class for staging data in DuckDB."""
    
    def __init__(self):
        """Initialize the stager with configuration."""
        self.db_path = os.getenv('DUCKDB_PATH', './data/cryptobookkeeper.duckdb')
        self.raw_data_dir = Path('data/raw')
        self.curated_data_dir = Path('data/curated')
        
        # Create directories
        self.curated_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize DuckDB connection
        self.conn = None
        self._init_duckdb()
        
        logger.info(f"Initialized DuckDB stager with database: {self.db_path}")
    
    def _init_duckdb(self):
        """Initialize DuckDB connection and schema."""
        try:
            self.conn = duckdb.connect(self.db_path)
            
            # Execute initialization SQL (use simplified version)
            init_sql_path = Path('sql/duckdb_init_simple.sql')
            if init_sql_path.exists():
                with open(init_sql_path, 'r') as f:
                    init_sql = f.read()
                self.conn.execute(init_sql)
                logger.info("DuckDB schema initialized successfully")
            else:
                logger.warning("DuckDB init SQL not found, using basic schema")
                self._create_basic_schema()
                
        except Exception as e:
            logger.error(f"Failed to initialize DuckDB: {e}")
            raise
    
    def _create_basic_schema(self):
        """Create basic schema if init SQL is not available."""
        # This is a fallback if the SQL file is not found
        logger.info("Creating basic DuckDB schema")
        # Basic schema creation would go here
        pass
    
    def load_exchange_data(self) -> Dict[str, int]:
        """Load all exchange data from CSV files."""
        logger.info("Loading exchange data from CSV files")
        stats = {}
        
        # Find all exchange CSV files
        exchange_files = list(self.raw_data_dir.glob('exchanges/*/*/*.csv'))
        
        if not exchange_files:
            logger.warning("No exchange CSV files found")
            return stats
        
        for file_path in tqdm(exchange_files, desc="Loading exchange files"):
            try:
                # Parse file path to get exchange and entity type
                parts = file_path.parts
                exchange = parts[-3]  # exchanges/{exchange}/{entity}/
                entity = parts[-2]     # {entity}/
                
                # Load CSV with proper types
                df = pd.read_csv(file_path)
                
                if df.empty:
                    logger.debug(f"Empty file: {file_path}")
                    continue
                
                # Clean and type the data
                df_cleaned = self._clean_exchange_data(df)
                
                # Insert into appropriate table
                table_name = f"raw_exchanges_{entity}"
                self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                
                # Create table from DataFrame
                self.conn.register('temp_df', df_cleaned)
                self.conn.execute(f"""
                    CREATE TABLE {table_name} AS 
                    SELECT * FROM temp_df
                """)
                
                stats[f"{exchange}_{entity}"] = len(df_cleaned)
                logger.info(f"Loaded {len(df_cleaned)} records from {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
                continue
        
        return stats
    
    def load_onchain_data(self) -> Dict[str, int]:
        """Load all on-chain data from CSV files."""
        logger.info("Loading on-chain data from CSV files")
        stats = {}
        
        # Find all on-chain CSV files (DeBank format: onchain/ethereum/*.csv)
        onchain_files = list(self.raw_data_dir.glob('onchain/*/*.csv'))
        
        if not onchain_files:
            logger.warning("No on-chain CSV files found")
            return stats
        
        for file_path in tqdm(onchain_files, desc="Loading on-chain files"):
            try:
                # Parse file path to get chain
                # DeBank format: onchain/ethereum/transfers_YYYY-MM.csv
                parts = file_path.parts
                chain = parts[-2]  # onchain/{chain}/
                entity = "transfers"  # Default entity type for DeBank data
                
                # Load CSV with proper types
                df = pd.read_csv(file_path)
                
                if df.empty:
                    logger.debug(f"Empty file: {file_path}")
                    continue
                
                # Clean and type the data
                df_cleaned = self._clean_onchain_data(df)
                
                # Insert into appropriate table
                table_name = f"raw_onchain_{entity}"
                self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                
                # Create table from DataFrame
                self.conn.register('temp_df', df_cleaned)
                self.conn.execute(f"""
                    CREATE TABLE {table_name} AS 
                    SELECT * FROM temp_df
                """)
                
                stats[f"onchain_{entity}"] = len(df_cleaned)
                logger.info(f"Loaded {len(df_cleaned)} records from {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
                continue
        
        return stats
    
    def _clean_exchange_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and type exchange data."""
        # Ensure required columns exist
        required_columns = [
            'source', 'exchange', 'account', 'txid', 'orderid', 'datetime',
            'base', 'quote', 'side', 'amount', 'price', 'fee_currency',
            'fee_amount', 'address', 'status', 'raw_json'
        ]
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = None
        
        # Type conversions
        df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['fee_amount'] = pd.to_numeric(df['fee_amount'], errors='coerce').fillna(0)
        
        # Clean string columns
        string_columns = ['source', 'exchange', 'account', 'txid', 'orderid', 
                         'base', 'quote', 'side', 'fee_currency', 'address', 'status']
        for col in string_columns:
            df[col] = df[col].astype(str).fillna('')
        
        return df
    
    def _clean_onchain_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and type on-chain data."""
        # Ensure required columns exist
        if 'transfers' in str(df.columns):
            required_columns = [
                'tx_hash', 'log_index', 'contract_address', 'from_address',
                'to_address', 'value', 'token_symbol', 'token_decimal',
                'block_number', 'block_timestamp', 'chain', 'raw_json'
            ]
        else:  # receipts
            required_columns = [
                'tx_hash', 'block_number', 'block_timestamp', 'from_address',
                'to_address', 'value', 'gas_used', 'gas_price', 'status',
                'chain', 'raw_json'
            ]
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = None
        
        # Type conversions
        df['block_timestamp'] = pd.to_datetime(df['block_timestamp'], utc=True)
        df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)
        
        if 'gas_used' in df.columns:
            df['gas_used'] = pd.to_numeric(df['gas_used'], errors='coerce').fillna(0)
        if 'gas_price' in df.columns:
            df['gas_price'] = pd.to_numeric(df['gas_price'], errors='coerce').fillna(0)
        if 'status' in df.columns:
            df['status'] = pd.to_numeric(df['status'], errors='coerce').fillna(0)
        if 'token_decimal' in df.columns:
            df['token_decimal'] = pd.to_numeric(df['token_decimal'], errors='coerce').fillna(18)
        
        # Clean string columns
        string_columns = ['tx_hash', 'contract_address', 'from_address', 'to_address',
                         'token_symbol', 'chain']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna('')
        
        return df
    
    def create_staged_tables(self):
        """Create staged tables from raw data."""
        logger.info("Creating staged tables")
        
        # Create staged tables first
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS staged_exchanges (
                domain VARCHAR,
                source VARCHAR,
                ts_utc TIMESTAMP,
                txid VARCHAR,
                base VARCHAR,
                quote VARCHAR,
                side VARCHAR,
                amount DOUBLE,
                price DOUBLE,
                fee_ccy VARCHAR,
                fee_amt DOUBLE,
                addr_from VARCHAR,
                addr_to VARCHAR,
                chain VARCHAR,
                token_symbol VARCHAR,
                token_decimal INTEGER,
                raw_json VARCHAR,
                year INTEGER,
                month INTEGER
            )
        """)
        
        # Clear existing data
        self.conn.execute("DELETE FROM staged_exchanges")
        
        # Stage exchange data (only trades for now)
        self.conn.execute("""
            INSERT INTO staged_exchanges
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
                address as addr_from,
                '' as addr_to,
                '' as chain,
                '' as token_symbol,
                NULL as token_decimal,
                raw_json,
                EXTRACT(YEAR FROM datetime) as year,
                EXTRACT(MONTH FROM datetime) as month
            FROM raw_exchanges_trades
            WHERE txid IS NOT NULL AND txid != ''
        """)
        
        # Create staged on-chain table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS staged_onchain (
                domain VARCHAR,
                source VARCHAR,
                ts_utc TIMESTAMP,
                txid VARCHAR,
                base VARCHAR,
                quote VARCHAR,
                side VARCHAR,
                amount DOUBLE,
                price DOUBLE,
                fee_ccy VARCHAR,
                fee_amt DOUBLE,
                addr_from VARCHAR,
                addr_to VARCHAR,
                chain VARCHAR,
                token_symbol VARCHAR,
                token_decimal INTEGER,
                raw_json VARCHAR,
                year INTEGER,
                month INTEGER
            )
        """)
        
        # Clear existing data
        self.conn.execute("DELETE FROM staged_onchain")
        
        # Stage on-chain data from DeBank
        try:
            self.conn.execute("""
                INSERT INTO staged_onchain
                SELECT 
                    'onchain' as domain,
                    'debank_' || chain as source,
                    CAST(block_timestamp AS TIMESTAMP) as ts_utc,
                    tx_hash as txid,
                    token_symbol as base,
                    '' as quote,
                    COALESCE(side, 'unknown') as side,
                    COALESCE(value, 0.0) as amount,
                    0.0 as price,
                    '' as fee_ccy,
                    0.0 as fee_amt,
                    from_address as addr_from,
                    to_address as addr_to,
                    chain,
                    token_symbol,
                    COALESCE(token_decimal, 18) as token_decimal,
                    raw_json,
                    EXTRACT(YEAR FROM CAST(block_timestamp AS TIMESTAMP)) as year,
                    EXTRACT(MONTH FROM CAST(block_timestamp AS TIMESTAMP)) as month
                FROM raw_onchain_transfers
                WHERE tx_hash IS NOT NULL AND tx_hash != ''
            """)
            logger.info("On-chain data staged successfully")
        except Exception as e:
            logger.warning(f"No on-chain data to stage: {e}")
        
        logger.info("Staged tables created successfully")
    
    def create_unified_table(self):
        """Create unified transaction table."""
        logger.info("Creating unified transaction table")
        
        # Create unified table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions_unified (
                domain VARCHAR,
                source VARCHAR,
                ts_utc TIMESTAMP,
                txid VARCHAR,
                base VARCHAR,
                quote VARCHAR,
                side VARCHAR,
                amount DOUBLE,
                price DOUBLE,
                fee_ccy VARCHAR,
                fee_amt DOUBLE,
                addr_from VARCHAR,
                addr_to VARCHAR,
                chain VARCHAR,
                token_symbol VARCHAR,
                token_decimal INTEGER,
                raw_json VARCHAR,
                year INTEGER,
                month INTEGER
            )
        """)
        
        # Clear existing data
        self.conn.execute("DELETE FROM transactions_unified")
        
        self.conn.execute("""
            INSERT INTO transactions_unified
            SELECT * FROM staged_exchanges
            
            UNION ALL
            
            SELECT * FROM staged_onchain
        """)
        
        logger.info("Unified transaction table created successfully")
    
    def export_to_parquet(self):
        """Export staged data to Parquet files."""
        logger.info("Exporting data to Parquet files")
        
        # Export staged exchange data
        self.conn.execute("""
            COPY staged_exchanges 
            TO 'data/curated/staged_exchanges.parquet' 
            (FORMAT PARQUET, COMPRESSION SNAPPY)
        """)
        
        # Export staged on-chain data
        self.conn.execute("""
            COPY staged_onchain 
            TO 'data/curated/staged_onchain.parquet' 
            (FORMAT PARQUET, COMPRESSION SNAPPY)
        """)
        
        # Export unified transactions
        self.conn.execute("""
            COPY transactions_unified 
            TO 'data/curated/transactions_unified.parquet' 
            (FORMAT PARQUET, COMPRESSION SNAPPY)
        """)
        
        logger.info("Data exported to Parquet files successfully")
    
    def generate_summary_stats(self):
        """Generate summary statistics."""
        logger.info("Generating summary statistics")
        
        # Get data quality summary (if table exists)
        try:
            quality_stats = self.conn.execute("SELECT * FROM data_quality_checks").fetchall()
            logger.info("Data Quality Summary:")
            for row in quality_stats:
                logger.info(f"  {row[0]}: {row[1]} records, {row[2]} unique txids, {row[3]} duplicates")
        except Exception as e:
            logger.info("Data quality checks table not available, skipping quality summary")
        
        # Get transaction summary by source (if table exists)
        try:
            source_stats = self.conn.execute("SELECT * FROM transaction_summary_by_source").fetchall()
            logger.info("Transaction Summary by Source:")
            for row in source_stats:
                logger.info(f"  {row[0]}/{row[1]}: {row[2]} transactions, {row[3]:.2f} total amount")
        except Exception as e:
            logger.info("Transaction summary by source not available")
        
        # Get monthly volume
        monthly_stats = self.conn.execute("""
            SELECT year, month, domain, source, COUNT(*) as count, SUM(amount) as total
            FROM transactions_unified 
            GROUP BY year, month, domain, source 
            ORDER BY year, month, domain, source
        """).fetchall()
        
        logger.info("Monthly Transaction Volume:")
        for row in monthly_stats:
            logger.info(f"  {row[0]}-{row[1]:02d} {row[2]}/{row[3]}: {row[4]} transactions, {row[5]:.2f} total")
    
    def run(self):
        """Run the complete staging process."""
        logger.info("Starting DuckDB staging process")
        start_time = datetime.now()
        
        try:
            # Load raw data
            exchange_stats = self.load_exchange_data()
            onchain_stats = self.load_onchain_data()
            
            logger.info(f"Loaded exchange data: {exchange_stats}")
            logger.info(f"Loaded on-chain data: {onchain_stats}")
            
            # Create staged tables
            self.create_staged_tables()
            
            # Create unified table
            self.create_unified_table()
            
            # Export to Parquet
            self.export_to_parquet()
            
            # Generate summary statistics
            self.generate_summary_stats()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Staging completed successfully in {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Staging failed: {e}")
            raise
        finally:
            if self.conn:
                self.conn.close()

def main():
    """Main entry point."""
    try:
        stager = DuckDBStager()
        stager.run()
    except KeyboardInterrupt:
        logger.info("Staging interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Staging failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
