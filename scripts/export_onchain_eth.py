#!/usr/bin/env python3
"""
Crypto Normalizer - On-Chain Data Export Script

Exports EVM blockchain transaction data using web3.py.
Supports token transfers and transaction receipts with address filtering.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import pandas as pd
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware
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
        logging.FileHandler(os.getenv('LOG_FILE', 'logs/export_onchain.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OnChainExporter:
    """Main class for exporting on-chain data."""
    
    def __init__(self):
        """Initialize the exporter with configuration."""
        self.start_ts = os.getenv('START_TS', '2021-01-01T00:00:00Z')
        self.eth_rpc_url = os.getenv('ETH_RPC_URL')
        self.evm_addresses = os.getenv('EVM_ADDRESSES', '').split(',')
        self.evm_addresses = [addr.strip().lower() for addr in self.evm_addresses if addr.strip()]
        
        # Create output directories
        self.output_dir = Path('data/raw/onchain/ethereum')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Web3
        self.w3 = None
        self._init_web3()
        
        logger.info(f"Initialized on-chain exporter")
        logger.info(f"Start timestamp: {self.start_ts}")
        logger.info(f"Monitoring addresses: {self.evm_addresses}")
    
    def _init_web3(self):
        """Initialize Web3 connection."""
        if not self.eth_rpc_url:
            logger.error("ETH_RPC_URL not configured")
            return
        
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.eth_rpc_url))
            
            # Add PoA middleware for chains like Polygon, BSC
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Test connection
            if self.w3.is_connected():
                latest_block = self.w3.eth.block_number
                logger.info(f"Connected to Ethereum RPC. Latest block: {latest_block}")
            else:
                logger.error("Failed to connect to Ethereum RPC")
                self.w3 = None
                
        except Exception as e:
            logger.error(f"Failed to initialize Web3: {e}")
            self.w3 = None
    
    def get_block_from_timestamp(self, timestamp: int) -> int:
        """Get block number from timestamp using binary search."""
        if not self.w3:
            return None
        
        try:
            # Get current block
            current_block = self.w3.eth.block_number
            current_block_info = self.w3.eth.get_block(current_block)
            current_timestamp = current_block_info.timestamp
            
            if timestamp > current_timestamp:
                logger.warning(f"Timestamp {timestamp} is in the future")
                return current_block
            
            # Binary search for block
            low = 0
            high = current_block
            
            while low <= high:
                mid = (low + high) // 2
                mid_block_info = self.w3.eth.get_block(mid)
                mid_timestamp = mid_block_info.timestamp
                
                if mid_timestamp < timestamp:
                    low = mid + 1
                elif mid_timestamp > timestamp:
                    high = mid - 1
                else:
                    return mid
            
            return high
            
        except Exception as e:
            logger.error(f"Failed to get block from timestamp: {e}")
            return None
    
    def normalize_timestamp(self, timestamp: int) -> str:
        """Normalize timestamp to UTC ISO format."""
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.isoformat().replace('+00:00', 'Z')
    
    def normalize_amount(self, amount: Any, decimals: int = 18) -> float:
        """Normalize amount from wei to token units."""
        if amount is None:
            return 0.0
        try:
            # Convert from wei to token units
            return float(amount) / (10 ** decimals)
        except (ValueError, TypeError, ZeroDivisionError):
            return 0.0
    
    def get_token_info(self, contract_address: str) -> Dict[str, Any]:
        """Get token symbol and decimals from contract."""
        if not self.w3 or not contract_address:
            return {'symbol': '', 'decimals': 18}
        
        try:
            # ERC20 ABI for symbol and decimals
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "symbol",
                    "outputs": [{"name": "", "type": "string"}],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "type": "function"
                }
            ]
            
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=erc20_abi
            )
            
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            
            return {'symbol': symbol, 'decimals': decimals}
            
        except Exception as e:
            logger.debug(f"Failed to get token info for {contract_address}: {e}")
            return {'symbol': '', 'decimals': 18}
    
    def export_token_transfers(self, start_block: int, end_block: int) -> List[Dict]:
        """Export token transfer events."""
        logger.info(f"Exporting token transfers from block {start_block} to {end_block}")
        transfers = []
        
        if not self.w3:
            logger.error("Web3 not initialized")
            return transfers
        
        try:
            # ERC20 Transfer event signature
            transfer_topic = self.w3.keccak(text="Transfer(address,address,uint256)").hex()
            
            # Get all transfer events in block range
            for block_num in tqdm(range(start_block, end_block + 1), desc="Scanning blocks"):
                try:
                    block = self.w3.eth.get_block(block_num, full_transactions=False)
                    
                    # Get logs for this block
                    logs = self.w3.eth.get_logs({
                        'fromBlock': block_num,
                        'toBlock': block_num,
                        'topics': [transfer_topic]
                    })
                    
                    for log in logs:
                        # Check if any of our addresses are involved
                        from_address = '0x' + log.topics[1].hex()[26:]  # Remove padding
                        to_address = '0x' + log.topics[2].hex()[26:]    # Remove padding
                        
                        if (from_address.lower() in self.evm_addresses or 
                            to_address.lower() in self.evm_addresses):
                            
                            # Get token info
                            token_info = self.get_token_info(log.address)
                            
                            # Decode transfer amount
                            transfer_amount = int(log.data, 16)
                            
                            transfer_record = {
                                'tx_hash': log.transactionHash.hex(),
                                'log_index': log.logIndex,
                                'contract_address': log.address,
                                'from_address': from_address,
                                'to_address': to_address,
                                'value': self.normalize_amount(transfer_amount, token_info['decimals']),
                                'token_symbol': token_info['symbol'],
                                'token_decimal': token_info['decimals'],
                                'block_number': block_num,
                                'block_timestamp': self.normalize_timestamp(block.timestamp),
                                'chain': 'ethereum',
                                'raw_json': json.dumps({
                                    'logIndex': log.logIndex,
                                    'transactionHash': log.transactionHash.hex(),
                                    'address': log.address,
                                    'topics': [t.hex() for t in log.topics],
                                    'data': log.data.hex()
                                })
                            }
                            transfers.append(transfer_record)
                
                except Exception as e:
                    logger.debug(f"Error processing block {block_num}: {e}")
                    continue
            
            logger.info(f"Exported {len(transfers)} token transfers")
            return transfers
            
        except Exception as e:
            logger.error(f"Failed to export token transfers: {e}")
            return transfers
    
    def export_transaction_receipts(self, start_block: int, end_block: int) -> List[Dict]:
        """Export transaction receipts for our addresses."""
        logger.info(f"Exporting transaction receipts from block {start_block} to {end_block}")
        receipts = []
        
        if not self.w3:
            logger.error("Web3 not initialized")
            return receipts
        
        try:
            for block_num in tqdm(range(start_block, end_block + 1), desc="Scanning blocks"):
                try:
                    block = self.w3.eth.get_block(block_num, full_transactions=True)
                    
                    for tx in block.transactions:
                        # Check if any of our addresses are involved
                        from_address = tx.get('from', '').lower()
                        to_address = tx.get('to', '').lower()
                        
                        if (from_address in self.evm_addresses or 
                            to_address in self.evm_addresses):
                            
                            # Get transaction receipt
                            try:
                                receipt = self.w3.eth.get_transaction_receipt(tx.hash)
                                
                                receipt_record = {
                                    'tx_hash': tx.hash.hex(),
                                    'block_number': block_num,
                                    'block_timestamp': self.normalize_timestamp(block.timestamp),
                                    'from_address': tx.get('from', ''),
                                    'to_address': tx.get('to', ''),
                                    'value': self.normalize_amount(tx.get('value', 0)),
                                    'gas_used': receipt.gasUsed,
                                    'gas_price': self.normalize_amount(tx.get('gasPrice', 0)),
                                    'status': receipt.status,
                                    'chain': 'ethereum',
                                    'raw_json': json.dumps({
                                        'hash': tx.hash.hex(),
                                        'from': tx.get('from', ''),
                                        'to': tx.get('to', ''),
                                        'value': str(tx.get('value', 0)),
                                        'gas': tx.get('gas', 0),
                                        'gasPrice': str(tx.get('gasPrice', 0)),
                                        'status': receipt.status
                                    })
                                }
                                receipts.append(receipt_record)
                                
                            except Exception as e:
                                logger.debug(f"Failed to get receipt for {tx.hash.hex()}: {e}")
                                continue
                
                except Exception as e:
                    logger.debug(f"Error processing block {block_num}: {e}")
                    continue
            
            logger.info(f"Exported {len(receipts)} transaction receipts")
            return receipts
            
        except Exception as e:
            logger.error(f"Failed to export transaction receipts: {e}")
            return receipts
    
    def save_to_csv(self, data: List[Dict], entity_type: str):
        """Save data to CSV file with monthly partitioning."""
        if not data:
            logger.warning(f"No data to save for {entity_type}")
            return
        
        # Create entity directory
        entity_dir = self.output_dir / entity_type
        entity_dir.mkdir(parents=True, exist_ok=True)
        
        # Group data by month
        monthly_data = {}
        for record in data:
            dt = datetime.fromisoformat(record['block_timestamp'].replace('Z', '+00:00'))
            month_key = dt.strftime('%Y-%m')
            
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            monthly_data[month_key].append(record)
        
        # Save each month to separate CSV
        for month, month_data in monthly_data.items():
            filename = entity_dir / f"{month}.csv"
            df = pd.DataFrame(month_data)
            df.to_csv(filename, index=False)
            logger.info(f"Saved {len(month_data)} {entity_type} records to {filename}")
    
    def run(self):
        """Run the complete on-chain export process."""
        if not self.w3:
            logger.error("Web3 not initialized, cannot proceed")
            return
        
        if not self.evm_addresses:
            logger.warning("No EVM addresses configured, nothing to export")
            return
        
        logger.info("Starting on-chain data export")
        start_time = time.time()
        
        try:
            # Parse start timestamp
            start_dt = datetime.fromisoformat(self.start_ts.replace('Z', '+00:00'))
            start_timestamp = int(start_dt.timestamp())
            
            # Get start block
            start_block = self.get_block_from_timestamp(start_timestamp)
            if start_block is None:
                logger.error("Failed to get start block")
                return
            
            # Get current block as end block
            end_block = self.w3.eth.block_number
            
            logger.info(f"Exporting data from block {start_block} to {end_block}")
            
            # Export token transfers
            transfers = self.export_token_transfers(start_block, end_block)
            self.save_to_csv(transfers, 'transfers')
            
            # Export transaction receipts
            receipts = self.export_transaction_receipts(start_block, end_block)
            self.save_to_csv(receipts, 'receipts')
            
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"On-chain export completed in {duration:.2f} seconds")
            logger.info(f"Total transfers: {len(transfers)}")
            logger.info(f"Total receipts: {len(receipts)}")
            
        except Exception as e:
            logger.error(f"On-chain export failed: {e}")
            raise

def main():
    """Main entry point."""
    try:
        exporter = OnChainExporter()
        exporter.run()
    except KeyboardInterrupt:
        logger.info("Export interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"On-chain export failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
