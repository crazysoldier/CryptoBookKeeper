#!/usr/bin/env python3
"""
Crypto Normalizer - Exchange Data Export Script

Exports transaction data from supported exchanges using CCXT.
Supports trades, deposits, and withdrawals with rate limiting and error handling.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
from dotenv import load_dotenv
import ccxt
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
        logging.FileHandler(os.getenv('LOG_FILE', 'logs/export_exchanges.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ExchangeExporter:
    """Main class for exporting exchange data."""
    
    def __init__(self):
        """Initialize the exporter with configuration."""
        self.start_ts = os.getenv('START_TS', '2021-01-01T00:00:00Z')
        self.exchanges = os.getenv('EXCHANGES', 'binance,kraken').split(',')
        self.rate_limit = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
        self.batch_size = int(os.getenv('BATCH_SIZE', '100'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        
        # Create output directories
        self.output_dir = Path('data/raw/exchanges')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Rate limiting tracking
        self.last_request_time = {}
        
        logger.info(f"Initialized exporter for exchanges: {self.exchanges}")
        logger.info(f"Start timestamp: {self.start_ts}")
    
    def get_exchange_client(self, exchange_name: str) -> ccxt.Exchange:
        """Get authenticated exchange client."""
        try:
            # Get API credentials
            api_key = os.getenv(f'{exchange_name.upper()}_API_KEY')
            api_secret = os.getenv(f'{exchange_name.upper()}_API_SECRET')
            
            if not api_key or not api_secret:
                logger.warning(f"No API credentials found for {exchange_name}")
                return None
            
            # Create exchange instance
            exchange_class = getattr(ccxt, exchange_name)
            client = exchange_class({
                'apiKey': api_key,
                'secret': api_secret,
                'sandbox': False,  # Use production APIs
                'enableRateLimit': True,
                'timeout': 30000,
            })
            
            # Test connection
            client.load_markets()
            logger.info(f"Successfully connected to {exchange_name}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to connect to {exchange_name}: {e}")
            return None
    
    def rate_limit_wait(self, exchange_name: str):
        """Implement rate limiting for API calls."""
        if exchange_name in self.last_request_time:
            time_since_last = time.time() - self.last_request_time[exchange_name]
            min_interval = 60.0 / self.rate_limit  # seconds between requests
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s for {exchange_name}")
                time.sleep(sleep_time)
        
        self.last_request_time[exchange_name] = time.time()
    
    def normalize_timestamp(self, timestamp: Any) -> str:
        """Normalize timestamp to UTC ISO format."""
        try:
            if isinstance(timestamp, (int, float)):
                # Unix timestamp (handle both seconds and milliseconds)
                if timestamp > 1e10:  # Milliseconds
                    timestamp = timestamp / 1000
                dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            elif isinstance(timestamp, str):
                # Parse string timestamp
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                # Assume datetime object
                dt = timestamp
            
            # Ensure UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            
            return dt.isoformat().replace('+00:00', 'Z')
        except Exception as e:
            logger.warning(f"Failed to normalize timestamp {timestamp}: {e}")
            return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    def normalize_amount(self, amount: Any) -> float:
        """Normalize amount to float."""
        if amount is None:
            return 0.0
        try:
            return float(amount)
        except (ValueError, TypeError):
            return 0.0
    
    def export_trades(self, client: ccxt.Exchange, exchange_name: str) -> List[Dict]:
        """Export trade data from exchange."""
        logger.info(f"Exporting trades from {exchange_name}")
        trades = []
        
        try:
            # Parse start timestamp
            start_dt = datetime.fromisoformat(self.start_ts.replace('Z', '+00:00'))
            start_timestamp = int(start_dt.timestamp() * 1000)
            
            # Fetch trades with pagination
            since = start_timestamp
            while True:
                self.rate_limit_wait(exchange_name)
                
                try:
                    batch = client.fetch_my_trades(since=since, limit=self.batch_size)
                    if not batch:
                        break
                    
                    for trade in batch:
                        normalized_trade = {
                            'source': exchange_name,
                            'exchange': exchange_name,
                            'account': 'main',  # Default account
                            'txid': str(trade.get('id', '')),
                            'orderid': str(trade.get('order', '')),
                            'datetime': self.normalize_timestamp(trade.get('timestamp')),
                            'base': trade.get('symbol', '').split('/')[0] if trade.get('symbol') else '',
                            'quote': trade.get('symbol', '').split('/')[1] if trade.get('symbol') else '',
                            'side': trade.get('side', ''),
                            'amount': self.normalize_amount(trade.get('amount')),
                            'price': self.normalize_amount(trade.get('price')),
                            'fee_currency': trade.get('fee', {}).get('currency', '') if trade.get('fee') else '',
                            'fee_amount': self.normalize_amount(trade.get('fee', {}).get('cost', 0)) if trade.get('fee') else 0,
                            'address': '',  # Not applicable for trades
                            'status': trade.get('status', ''),
                            'raw_json': json.dumps(trade)
                        }
                        trades.append(normalized_trade)
                    
                    # Update since for next batch
                    since = batch[-1]['timestamp'] + 1
                    logger.debug(f"Fetched {len(batch)} trades from {exchange_name}")
                    
                except ccxt.RateLimitExceeded:
                    logger.warning(f"Rate limit exceeded for {exchange_name}, waiting...")
                    time.sleep(60)
                    continue
                except ccxt.NetworkError as e:
                    logger.error(f"Network error for {exchange_name}: {e}")
                    time.sleep(30)
                    continue
                except Exception as e:
                    logger.error(f"Error fetching trades from {exchange_name}: {e}")
                    break
            
            logger.info(f"Exported {len(trades)} trades from {exchange_name}")
            return trades
            
        except Exception as e:
            logger.error(f"Failed to export trades from {exchange_name}: {e}")
            return []
    
    def export_deposits(self, client: ccxt.Exchange, exchange_name: str) -> List[Dict]:
        """Export deposit data from exchange."""
        logger.info(f"Exporting deposits from {exchange_name}")
        deposits = []
        
        try:
            # Parse start timestamp
            start_dt = datetime.fromisoformat(self.start_ts.replace('Z', '+00:00'))
            start_timestamp = int(start_dt.timestamp() * 1000)
            
            # Coinbase requires currency code for deposits/withdrawals
            if exchange_name.lower() == 'coinbase':
                # Get list of currencies to fetch deposits for
                currencies = ['EUR', 'USD', 'USDC', 'EURC', 'BTC', 'ETH', 'LINK']
                for currency in currencies:
                    try:
                        self.rate_limit_wait(exchange_name)
                        batch = client.fetch_deposits(code=currency, since=start_timestamp, limit=100)
                        if batch:
                            for deposit in batch:
                                normalized_deposit = {
                                    'source': exchange_name,
                                    'exchange': exchange_name,
                                    'account': 'main',
                                    'txid': str(deposit.get('id', '')),
                                    'orderid': '',
                                    'datetime': self.normalize_timestamp(deposit.get('timestamp')),
                                    'base': deposit.get('currency', currency),
                                    'quote': '',
                                    'side': 'deposit',
                                    'amount': self.normalize_amount(deposit.get('amount')),
                                    'price': 0.0,
                                    'fee_currency': deposit.get('fee', {}).get('currency', '') if isinstance(deposit.get('fee'), dict) else '',
                                    'fee_amount': self.normalize_amount(deposit.get('fee', {}).get('cost', 0)) if isinstance(deposit.get('fee'), dict) else 0.0,
                                    'address': deposit.get('address', ''),
                                    'status': deposit.get('status', ''),
                                    'raw_json': str(deposit)
                                }
                                deposits.append(normalized_deposit)
                            logger.info(f"Fetched {len(batch)} {currency} deposits from {exchange_name}")
                    except Exception as e:
                        logger.debug(f"No {currency} deposits: {e}")
                        continue
                logger.info(f"Exported {len(deposits)} deposits from {exchange_name}")
                return deposits
            
            # Standard approach for other exchanges
            since = start_timestamp
            while True:
                self.rate_limit_wait(exchange_name)
                
                try:
                    batch = client.fetch_deposits(since=since, limit=self.batch_size)
                    if not batch:
                        break
                    
                    for deposit in batch:
                        normalized_deposit = {
                            'source': exchange_name,
                            'exchange': exchange_name,
                            'account': 'main',
                            'txid': str(deposit.get('id', '')),
                            'orderid': '',
                            'datetime': self.normalize_timestamp(deposit.get('timestamp')),
                            'base': deposit.get('currency', ''),
                            'quote': '',
                            'side': 'deposit',
                            'amount': self.normalize_amount(deposit.get('amount')),
                            'price': None,
                            'fee_currency': deposit.get('fee', {}).get('currency', '') if deposit.get('fee') else '',
                            'fee_amount': self.normalize_amount(deposit.get('fee', {}).get('cost', 0)) if deposit.get('fee') else 0,
                            'address': deposit.get('address', ''),
                            'status': deposit.get('status', ''),
                            'raw_json': json.dumps(deposit)
                        }
                        deposits.append(normalized_deposit)
                    
                    # Update since for next batch
                    since = batch[-1]['timestamp'] + 1
                    logger.debug(f"Fetched {len(batch)} deposits from {exchange_name}")
                    
                except ccxt.RateLimitExceeded:
                    logger.warning(f"Rate limit exceeded for {exchange_name}, waiting...")
                    time.sleep(60)
                    continue
                except ccxt.NetworkError as e:
                    logger.error(f"Network error for {exchange_name}: {e}")
                    time.sleep(30)
                    continue
                except Exception as e:
                    logger.error(f"Error fetching deposits from {exchange_name}: {e}")
                    break
            
            logger.info(f"Exported {len(deposits)} deposits from {exchange_name}")
            return deposits
            
        except Exception as e:
            logger.error(f"Failed to export deposits from {exchange_name}: {e}")
            return []
    
    def export_withdrawals(self, client: ccxt.Exchange, exchange_name: str) -> List[Dict]:
        """Export withdrawal data from exchange."""
        logger.info(f"Exporting withdrawals from {exchange_name}")
        withdrawals = []
        
        try:
            # Parse start timestamp
            start_dt = datetime.fromisoformat(self.start_ts.replace('Z', '+00:00'))
            start_timestamp = int(start_dt.timestamp() * 1000)
            
            # Coinbase requires currency code for deposits/withdrawals
            if exchange_name.lower() == 'coinbase':
                # Get list of currencies to fetch withdrawals for
                currencies = ['EUR', 'USD', 'USDC', 'EURC', 'BTC', 'ETH', 'LINK']
                for currency in currencies:
                    try:
                        self.rate_limit_wait(exchange_name)
                        batch = client.fetch_withdrawals(code=currency, since=start_timestamp, limit=100)
                        if batch:
                            for withdrawal in batch:
                                normalized_withdrawal = {
                                    'source': exchange_name,
                                    'exchange': exchange_name,
                                    'account': 'main',
                                    'txid': str(withdrawal.get('id', '')),
                                    'orderid': '',
                                    'datetime': self.normalize_timestamp(withdrawal.get('timestamp')),
                                    'base': withdrawal.get('currency', currency),
                                    'quote': '',
                                    'side': 'withdrawal',
                                    'amount': self.normalize_amount(withdrawal.get('amount')),
                                    'price': 0.0,
                                    'fee_currency': withdrawal.get('fee', {}).get('currency', '') if isinstance(withdrawal.get('fee'), dict) else '',
                                    'fee_amount': self.normalize_amount(withdrawal.get('fee', {}).get('cost', 0)) if isinstance(withdrawal.get('fee'), dict) else 0.0,
                                    'address': withdrawal.get('address', ''),
                                    'status': withdrawal.get('status', ''),
                                    'raw_json': str(withdrawal)
                                }
                                withdrawals.append(normalized_withdrawal)
                            logger.info(f"Fetched {len(batch)} {currency} withdrawals from {exchange_name}")
                    except Exception as e:
                        logger.debug(f"No {currency} withdrawals: {e}")
                        continue
                logger.info(f"Exported {len(withdrawals)} withdrawals from {exchange_name}")
                return withdrawals
            
            # Standard approach for other exchanges
            since = start_timestamp
            while True:
                self.rate_limit_wait(exchange_name)
                
                try:
                    batch = client.fetch_withdrawals(since=since, limit=self.batch_size)
                    if not batch:
                        break
                    
                    for withdrawal in batch:
                        normalized_withdrawal = {
                            'source': exchange_name,
                            'exchange': exchange_name,
                            'account': 'main',
                            'txid': str(withdrawal.get('id', '')),
                            'orderid': '',
                            'datetime': self.normalize_timestamp(withdrawal.get('timestamp')),
                            'base': withdrawal.get('currency', ''),
                            'quote': '',
                            'side': 'withdrawal',
                            'amount': self.normalize_amount(withdrawal.get('amount')),
                            'price': None,
                            'fee_currency': withdrawal.get('fee', {}).get('currency', '') if withdrawal.get('fee') else '',
                            'fee_amount': self.normalize_amount(withdrawal.get('fee', {}).get('cost', 0)) if withdrawal.get('fee') else 0,
                            'address': withdrawal.get('address', ''),
                            'status': withdrawal.get('status', ''),
                            'raw_json': json.dumps(withdrawal)
                        }
                        withdrawals.append(normalized_withdrawal)
                    
                    # Update since for next batch
                    since = batch[-1]['timestamp'] + 1
                    logger.debug(f"Fetched {len(batch)} withdrawals from {exchange_name}")
                    
                except ccxt.RateLimitExceeded:
                    logger.warning(f"Rate limit exceeded for {exchange_name}, waiting...")
                    time.sleep(60)
                    continue
                except ccxt.NetworkError as e:
                    logger.error(f"Network error for {exchange_name}: {e}")
                    time.sleep(30)
                    continue
                except Exception as e:
                    logger.error(f"Error fetching withdrawals from {exchange_name}: {e}")
                    break
            
            logger.info(f"Exported {len(withdrawals)} withdrawals from {exchange_name}")
            return withdrawals
            
        except Exception as e:
            logger.error(f"Failed to export withdrawals from {exchange_name}: {e}")
            return []
    
    def save_to_csv(self, data: List[Dict], exchange_name: str, entity_type: str):
        """Save data to CSV file with monthly partitioning."""
        if not data:
            logger.warning(f"No data to save for {exchange_name} {entity_type}")
            return
        
        # Create exchange directory
        exchange_dir = self.output_dir / exchange_name / entity_type
        exchange_dir.mkdir(parents=True, exist_ok=True)
        
        # Group data by month
        monthly_data = {}
        for record in data:
            dt = datetime.fromisoformat(record['datetime'].replace('Z', '+00:00'))
            month_key = dt.strftime('%Y-%m')
            
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            monthly_data[month_key].append(record)
        
        # Save each month to separate CSV
        for month, month_data in monthly_data.items():
            filename = exchange_dir / f"{month}.csv"
            df = pd.DataFrame(month_data)
            df.to_csv(filename, index=False)
            logger.info(f"Saved {len(month_data)} {entity_type} records to {filename}")
    
    def export_exchange(self, exchange_name: str):
        """Export all data from a single exchange."""
        logger.info(f"Starting export for {exchange_name}")
        
        # Get authenticated client
        client = self.get_exchange_client(exchange_name)
        if not client:
            logger.error(f"Cannot connect to {exchange_name}, skipping")
            return
        
        try:
            # Export trades
            trades = self.export_trades(client, exchange_name)
            self.save_to_csv(trades, exchange_name, 'trades')
            
            # Export deposits
            deposits = self.export_deposits(client, exchange_name)
            self.save_to_csv(deposits, exchange_name, 'deposits')
            
            # Export withdrawals
            withdrawals = self.export_withdrawals(client, exchange_name)
            self.save_to_csv(withdrawals, exchange_name, 'withdrawals')
            
            logger.info(f"Completed export for {exchange_name}")
            
        except Exception as e:
            logger.error(f"Failed to export from {exchange_name}: {e}")
        finally:
            if hasattr(client, 'close'):
                client.close()
    
    def run(self):
        """Run the complete export process."""
        logger.info("Starting exchange data export")
        start_time = time.time()
        
        total_records = 0
        
        for exchange_name in tqdm(self.exchanges, desc="Exporting exchanges"):
            try:
                self.export_exchange(exchange_name)
            except Exception as e:
                logger.error(f"Failed to export from {exchange_name}: {e}")
                continue
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"Export completed in {duration:.2f} seconds")
        logger.info(f"Total records exported: {total_records}")

def main():
    """Main entry point."""
    try:
        exporter = ExchangeExporter()
        exporter.run()
    except KeyboardInterrupt:
        logger.info("Export interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Export failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
