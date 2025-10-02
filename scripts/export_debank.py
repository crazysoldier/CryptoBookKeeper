#!/usr/bin/env python3
"""
CryptoBookKeeper - DeBank API Export Script

Exports EVM blockchain transaction data using DeBank's Cloud API.
Supports multiple EVM chains with comprehensive transaction history.
Supports incremental loading to save API units.
"""

import os
import sys
import json
import time
import logging
import requests
import argparse
import duckdb
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
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
        logging.FileHandler(os.getenv('LOG_FILE', 'logs/export_debank.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DeBankExporter:
    """Main class for exporting on-chain data via DeBank API."""
    
    def __init__(self, incremental: bool = False):
        """Initialize the exporter with configuration."""
        self.start_ts = os.getenv('START_TS', '2024-01-01T00:00:00Z')
        self.debank_api_key = os.getenv('DEBANK_API_KEY')
        self.evm_addresses = os.getenv('EVM_ADDRESSES', '').split(',')
        self.evm_addresses = [addr.strip().lower() for addr in self.evm_addresses if addr.strip()]
        self.incremental = incremental
        
        # Create output directories
        self.output_dir = Path('data/raw/onchain/ethereum')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Database connection for sync tracking
        self.db_path = os.getenv('DUCKDB_PATH', './data/cryptobookkeeper.duckdb')
        self.conn = None
        if self.incremental:
            try:
                self.conn = duckdb.connect(self.db_path)
                logger.info(f"Connected to DuckDB for sync tracking: {self.db_path}")
            except Exception as e:
                logger.warning(f"Could not connect to DuckDB, falling back to full sync: {e}")
                self.incremental = False
        
        # DeBank API configuration
        # Important: Use pro-openapi.debank.com endpoint
        self.base_url = "https://pro-openapi.debank.com/v1"
        self.session = requests.Session()
        
        if self.debank_api_key:
            # DeBank uses AccessKey header (not Bearer token)
            self.session.headers.update({
                'AccessKey': self.debank_api_key,
                'accept': 'application/json'
            })
        else:
            logger.warning("DEBANK_API_KEY not configured")
        
        mode = "INCREMENTAL" if self.incremental else "FULL"
        logger.info(f"Initialized DeBank exporter in {mode} mode")
        logger.info(f"Start timestamp: {self.start_ts}")
        logger.info(f"Monitoring addresses: {self.evm_addresses}")
    
    def get_last_sync_timestamp(self, source: str) -> float:
        """Get last successful sync timestamp for a source."""
        if not self.conn or not self.incremental:
            # Return start_ts for full sync
            return datetime.fromisoformat(self.start_ts.replace('Z', '+00:00')).timestamp()
        
        try:
            result = self.conn.execute(
                "SELECT last_sync_ts FROM sync_log WHERE source = ?",
                [source]
            ).fetchone()
            
            if result and result[0]:
                # Add small overlap (1 hour) to catch any delayed transactions
                overlap_seconds = 3600
                return result[0].timestamp() - overlap_seconds
            else:
                # First run, use START_TS
                return datetime.fromisoformat(self.start_ts.replace('Z', '+00:00')).timestamp()
        except Exception as e:
            logger.warning(f"Error getting last sync for {source}: {e}")
            return datetime.fromisoformat(self.start_ts.replace('Z', '+00:00')).timestamp()
    
    def update_sync_log(self, source: str, sync_count: int, status: str = 'success', error: str = None):
        """Update sync log with results."""
        if not self.conn or not self.incremental:
            return
        
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO sync_log 
                (source, last_sync_ts, sync_count, sync_status, error_message, updated_at)
                VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, CURRENT_TIMESTAMP)
            """, [source, sync_count, status, error])
            logger.info(f"Updated sync log for {source}: {sync_count} records, status={status}")
        except Exception as e:
            logger.warning(f"Failed to update sync log for {source}: {e}")
    
    def get_user_history(self, address: str, chain_id: str = 'eth', page_count: int = 20) -> List[Dict]:
        """Get user transaction history from DeBank API."""
        if not self.debank_api_key:
            logger.error("DEBANK_API_KEY required for transaction history")
            return []
        
        try:
            url = f"{self.base_url}/user/history_list"
            params = {
                'id': address,
                'chain_id': chain_id,
                'page_count': page_count
            }
            
            logger.info(f"Fetching history for {address} on {chain_id}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract history list
            if isinstance(data, dict):
                history_list = data.get('history_list', [])
            else:
                history_list = []
            
            logger.info(f"Retrieved {len(history_list)} transactions from {chain_id}")
            return history_list
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch history for {address} on {chain_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error processing history for {address}: {e}")
            return []
    
    def normalize_transaction(self, tx: Dict, address: str) -> Dict:
        """Normalize transaction data to our schema."""
        try:
            # Extract basic transaction info
            tx_hash = tx.get('id', '')
            timestamp = tx.get('time_at', 0)
            
            # Convert timestamp to ISO format
            if timestamp:
                dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                ts_utc = dt.isoformat()
            else:
                ts_utc = None
            
            # Extract transaction details
            tx_type = tx.get('cate_id', 'unknown')
            chain = tx.get('chain', 'eth')
            
            # Extract sends and receives
            sends = tx.get('sends', [])
            receives = tx.get('receives', [])
            
            # Determine transaction side
            if sends:
                side = 'out'
            elif receives:
                side = 'in'
            else:
                side = 'unknown'
            
            return {
                'tx_hash': tx_hash,
                'log_index': None,
                'contract_address': '',
                'from_address': tx.get('tx', {}).get('from_addr', ''),
                'to_address': tx.get('tx', {}).get('to_addr', ''),
                'value': 0,  # Will be calculated from sends/receives
                'token_symbol': '',
                'token_decimal': 18,
                'block_number': None,
                'block_timestamp': ts_utc,
                'chain': chain,
                'tx_type': tx_type,
                'side': side,
                'raw_json': json.dumps(tx)
            }
            
        except Exception as e:
            logger.error(f"Error normalizing transaction: {e}")
            return {}
    
    def export_address_data(self, address: str, chains: List[str] = None) -> None:
        """Export all data for a specific address across multiple chains."""
        if chains is None:
            chains = ['eth']
        
        logger.info(f"Exporting data for address: {address}")
        logger.info(f"Chains: {', '.join(chains)}")
        
        all_transactions = []
        
        # Get transaction history from all chains
        if self.debank_api_key:
            for chain in chains:
                try:
                    source = f"debank_{chain}"
                    
                    # Get last sync timestamp for incremental mode
                    if self.incremental:
                        last_sync = self.get_last_sync_timestamp(source)
                        logger.info(f"Incremental sync for {source}: fetching transactions after {datetime.fromtimestamp(last_sync)}")
                    
                    transactions = self.get_user_history(address, chain_id=chain, page_count=100)
                    
                    # Filter transactions for incremental mode
                    if self.incremental and transactions:
                        last_sync = self.get_last_sync_timestamp(source)
                        original_count = len(transactions)
                        transactions = [tx for tx in transactions if tx.get('time_at', 0) > last_sync]
                        logger.info(f"Filtered {original_count} → {len(transactions)} new transactions for {source}")
                    
                    new_tx_count = 0
                    if transactions:
                        for tx in tqdm(transactions, desc=f"Processing {chain}"):
                            normalized = self.normalize_transaction(tx, address)
                            if normalized:
                                all_transactions.append(normalized)
                                new_tx_count += 1
                    
                    # Update sync log
                    self.update_sync_log(source, new_tx_count)
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Error processing chain {chain}: {e}")
                    self.update_sync_log(f"debank_{chain}", 0, 'failed', str(e))
                    continue
            
            # Save all transactions
            if all_transactions:
                df = pd.DataFrame(all_transactions)
                
                # Create monthly partitions
                df['timestamp'] = pd.to_datetime(df['block_timestamp'], errors='coerce')
                df = df.dropna(subset=['timestamp'])
                df['year'] = df['timestamp'].dt.year
                df['month'] = df['timestamp'].dt.month
                
                for (year, month), group in df.groupby(['year', 'month']):
                    filename = f"transfers_{year:04d}-{month:02d}.csv"
                    filepath = self.output_dir / filename
                    
                    # Append or create file
                    if filepath.exists():
                        existing_df = pd.read_csv(filepath)
                        combined_df = pd.concat([existing_df, group]).drop_duplicates(subset=['tx_hash'])
                        combined_df.to_csv(filepath, index=False)
                        logger.info(f"Updated {filepath} with {len(group)} transactions")
                    else:
                        group.to_csv(filepath, index=False)
                        logger.info(f"Saved {len(group)} transactions to {filepath}")
                
                logger.info(f"Total transactions exported: {len(all_transactions)}")
            else:
                logger.warning(f"No transactions found for {address}")
        else:
            logger.warning("No API key - skipping transaction history")
    
    def export_all(self) -> None:
        """Export data for all configured addresses."""
        if not self.evm_addresses:
            logger.warning("No EVM addresses configured")
            return
        
        # Get chains to export
        chains_str = os.getenv('DEBANK_CHAINS', 'eth')
        chains = [chain.strip() for chain in chains_str.split(',') if chain.strip()]
        
        logger.info(f"Starting DeBank export for {len(self.evm_addresses)} addresses")
        logger.info(f"Chains: {', '.join(chains)}")
        
        for address in self.evm_addresses:
            try:
                self.export_address_data(address, chains=chains)
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Error exporting data for {address}: {e}")
                continue
        
        logger.info("DeBank export completed!")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Export on-chain data via DeBank API')
    parser.add_argument('--incremental', action='store_true',
                       help='Only fetch new transactions since last sync (saves API units)')
    args = parser.parse_args()
    
    try:
        exporter = DeBankExporter(incremental=args.incremental)
        exporter.export_all()
    except Exception as e:
        logger.error(f"Export failed: {e}")
        sys.exit(1)
    finally:
        # Close DB connection if open
        if hasattr(exporter, 'conn') and exporter.conn:
            exporter.conn.close()

if __name__ == "__main__":
    main()
