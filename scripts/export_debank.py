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
        
        # Scam filtering configuration
        self.filter_scams = os.getenv('DEBANK_FILTER_SCAMS', 'true').lower() == 'true'
        
        # Token cache to avoid repeated API calls
        self.token_cache = {}
        
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
        logger.info(f"Scam filtering: {'ENABLED' if self.filter_scams else 'DISABLED'}")
    
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
    
    def get_user_history(self, address: str, chain_id: str = 'eth', page_count: int = 100, 
                         start_time: Optional[int] = None, max_pages: int = 50) -> List[Dict]:
        """Get user transaction history from DeBank API with pagination.
        
        Args:
            address: User wallet address
            chain_id: Chain identifier (e.g., 'eth', 'matic')
            page_count: Number of transactions per page (max 100)
            start_time: Unix timestamp to start from (for pagination)
            max_pages: Maximum number of pages to fetch (safety limit)
        
        Returns:
            List of transaction dictionaries
        """
        if not self.debank_api_key:
            logger.error("DEBANK_API_KEY required for transaction history")
            return []
        
        all_transactions = []
        current_start_time = start_time
        pages_fetched = 0
        
        logger.info(f"Fetching history for {address} on {chain_id} (pagination enabled)")
        
        while pages_fetched < max_pages:
            try:
                url = f"{self.base_url}/user/history_list"
                params = {
                    'id': address,
                    'chain_id': chain_id,
                    'page_count': page_count
                }
                
                # Add start_time for pagination (if not first page)
                if current_start_time:
                    params['start_time'] = current_start_time
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract history list
                if isinstance(data, dict):
                    history_list = data.get('history_list', [])
                else:
                    history_list = []
                
                if not history_list:
                    logger.info(f"No more transactions found on {chain_id} (page {pages_fetched + 1})")
                    break
                
                all_transactions.extend(history_list)
                pages_fetched += 1
                
                logger.info(f"Retrieved {len(history_list)} transactions from {chain_id} (page {pages_fetched}, total: {len(all_transactions)})")
                
                # Check if we have more pages
                # DeBank API: use the timestamp of the last transaction as start_time for next page
                if len(history_list) < page_count:
                    # Less than page_count means this is the last page
                    logger.info(f"Reached last page for {chain_id}")
                    break
                
                # Get timestamp of last transaction for next page
                last_tx = history_list[-1]
                current_start_time = last_tx.get('time_at')
                
                if not current_start_time:
                    logger.warning(f"No timestamp found in last transaction, stopping pagination")
                    break
                
                # Small delay to avoid rate limiting
                time.sleep(0.3)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch history for {address} on {chain_id} (page {pages_fetched + 1}): {e}")
                break
            except Exception as e:
                logger.error(f"Error processing history for {address} on {chain_id}: {e}")
                break
        
        logger.info(f"Total transactions fetched from {chain_id}: {len(all_transactions)} ({pages_fetched} pages)")
        return all_transactions
    
    def get_token_info(self, token_id: str, chain: str) -> Dict[str, Any]:
        """Get token symbol and name from DeBank API with caching."""
        cache_key = f"{chain}:{token_id}"
        
        # Check cache first
        if cache_key in self.token_cache:
            return self.token_cache[cache_key]
        
        # Common token addresses we can resolve without API
        known_tokens = {
            '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48': {'symbol': 'USDC', 'name': 'USD Coin', 'decimals': 6},
            '0xaf88d065e77c8cc2239327c5edb3a432268e5831': {'symbol': 'USDC', 'name': 'USD Coin', 'decimals': 6},  # USDC on Arbitrum
            '0xdac17f958d2ee523a2206206994597c13d831ec7': {'symbol': 'USDT', 'name': 'Tether USD', 'decimals': 6},
            '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2': {'symbol': 'WETH', 'name': 'Wrapped Ether', 'decimals': 18},
            '0x82af49447d8a07e3bd95bd0d56f35241523fbab1': {'symbol': 'WETH', 'name': 'Wrapped Ether', 'decimals': 18},  # WETH on Arbitrum
        }
        
        token_id_lower = token_id.lower()
        if token_id_lower in known_tokens:
            token_info = known_tokens[token_id_lower]
            self.token_cache[cache_key] = token_info
            return token_info
        
        # Try to fetch from DeBank API
        try:
            if not self.debank_api_key:
                return {'symbol': token_id[:8], 'name': 'Unknown', 'decimals': 18}
            
            url = f"{self.base_url}/token"
            params = {
                'id': token_id,
                'chain_id': chain
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                token_info = {
                    'symbol': data.get('symbol', token_id[:8]),
                    'name': data.get('name', 'Unknown'),
                    'decimals': data.get('decimals', 18)
                }
                self.token_cache[cache_key] = token_info
                return token_info
            else:
                # Fallback
                token_info = {'symbol': token_id[:8], 'name': 'Unknown', 'decimals': 18}
                self.token_cache[cache_key] = token_info
                return token_info
                
        except Exception as e:
            logger.warning(f"Failed to fetch token info for {token_id}: {e}")
            token_info = {'symbol': token_id[:8], 'name': 'Unknown', 'decimals': 18}
            self.token_cache[cache_key] = token_info
            return token_info
    
    def normalize_transaction(self, tx: Dict, address: str) -> Dict:
        """Normalize transaction data to our schema with proper token resolution."""
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
            cate_id = tx.get('cate_id')
            chain = tx.get('chain', 'eth')
            project_id = tx.get('project_id', '')
            
            # Extract sends and receives
            sends = tx.get('sends', [])
            receives = tx.get('receives', [])
            token_approve = tx.get('token_approve')
            
            # Determine action and extract token info
            token_symbol = ''
            token_name = ''
            token_decimal = 18
            amount = 0.0
            contract_address = ''
            action = 'unknown'
            from_address = tx.get('tx', {}).get('from_addr', '')
            to_address = tx.get('tx', {}).get('to_addr', '')
            
            # Categorize transaction
            if cate_id == 'approve' or token_approve:
                action = 'approve'
                if token_approve:
                    token_id = token_approve.get('token_id', '')
                    contract_address = token_id
                    amount = token_approve.get('value', 0)
                    to_address = token_approve.get('spender', to_address)
                    # Get token info
                    if token_id:
                        token_info = self.get_token_info(token_id, chain)
                        token_symbol = token_info['symbol']
                        token_name = token_info['name']
                        token_decimal = token_info['decimals']
                        
            elif sends and receives:
                # Swap
                action = 'swap'
                # Use the first send as primary
                send = sends[0]
                token_id = send.get('token_id', '')
                contract_address = token_id
                amount = send.get('amount', 0)
                to_address = send.get('to_addr', to_address)
                if token_id:
                    token_info = self.get_token_info(token_id, chain)
                    token_symbol = token_info['symbol']
                    token_name = token_info['name']
                    token_decimal = token_info['decimals']
                    
            elif sends:
                # Send/Withdraw
                action = 'send' if cate_id != 'deposit' else 'deposit'
                send = sends[0]
                token_id = send.get('token_id', '')
                contract_address = token_id
                amount = send.get('amount', 0)
                to_address = send.get('to_addr', to_address)
                if token_id:
                    token_info = self.get_token_info(token_id, chain)
                    token_symbol = token_info['symbol']
                    token_name = token_info['name']
                    token_decimal = token_info['decimals']
                    
            elif receives:
                # Receive
                action = 'receive'
                receive = receives[0]
                token_id = receive.get('token_id', '')
                contract_address = token_id
                amount = receive.get('amount', 0)
                from_address = receive.get('from_addr', from_address)
                if token_id:
                    token_info = self.get_token_info(token_id, chain)
                    token_symbol = token_info['symbol']
                    token_name = token_info['name']
                    token_decimal = token_info['decimals']
            
            return {
                'tx_hash': tx_hash,
                'log_index': None,
                'contract_address': contract_address,
                'from_address': from_address,
                'to_address': to_address,
                'value': abs(amount) if amount else 0,
                'token_symbol': token_symbol,
                'token_decimal': token_decimal,
                'block_number': None,
                'block_timestamp': ts_utc,
                'chain': chain,
                'tx_type': action,
                'side': action,
                'raw_json': json.dumps(tx)
            }
            
        except Exception as e:
            logger.error(f"Error normalizing transaction: {e}")
            import traceback
            traceback.print_exc()
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
                    
                    # Fetch with pagination (will retrieve ALL transactions)
                    transactions = self.get_user_history(address, chain_id=chain)
                    
                    # Filter scam transactions if enabled
                    if self.filter_scams and transactions:
                        original_count = len(transactions)
                        transactions = [tx for tx in transactions if not tx.get('is_scam', False)]
                        scam_count = original_count - len(transactions)
                        if scam_count > 0:
                            logger.info(f"Filtered out {scam_count} scam transactions from {chain}")
                    
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
