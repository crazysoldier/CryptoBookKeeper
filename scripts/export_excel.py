#!/usr/bin/env python3
"""
CryptoBookKeeper - Excel Export Script

Exports unified transaction data from DuckDB to a beautifully formatted Excel workbook.
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import duckdb
import xlsxwriter
from dotenv import load_dotenv

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ExcelExporter:
    """Main class for exporting data to Excel."""
    
    def __init__(self):
        """Initialize the exporter with configuration."""
        self.db_path = os.getenv('DUCKDB_PATH', './data/cryptobookkeeper.duckdb')
        self.output_dir = Path('data/exports')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_file = self.output_dir / f'CryptoBookKeeper_Transactions_{timestamp}.xlsx'
        
        # Connect to DuckDB
        self.conn = duckdb.connect(self.db_path, read_only=True)
        
        logger.info(f"Initialized Excel exporter")
        logger.info(f"Database: {self.db_path}")
        logger.info(f"Output: {self.output_file}")
    
    def create_workbook(self):
        """Create and populate the Excel workbook."""
        logger.info("Creating Excel workbook...")
        
        # Create workbook
        self.workbook = xlsxwriter.Workbook(str(self.output_file))
        
        # Define formats
        self._define_formats()
        
        # Create sheets
        logger.info("Creating Summary Dashboard...")
        self._create_summary_dashboard()
        
        logger.info("Creating All Transactions sheet...")
        self._create_all_transactions()
        
        logger.info("Creating Exchange Transactions sheet...")
        self._create_exchange_transactions()
        
        logger.info("Creating On-Chain Transactions sheet...")
        self._create_onchain_transactions()
        
        logger.info("Creating Yearly Summary sheet...")
        self._create_yearly_summary()
        
        # Close workbook
        self.workbook.close()
        logger.info(f"✅ Excel file created: {self.output_file}")
    
    def _define_formats(self):
        """Define cell formats for the workbook."""
        self.formats = {
            'title': self.workbook.add_format({
                'bold': True,
                'font_size': 16,
                'font_color': '#1F4E78',
                'align': 'left',
                'valign': 'vcenter'
            }),
            'header': self.workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            }),
            'metric_label': self.workbook.add_format({
                'bold': True,
                'font_size': 11,
                'align': 'right',
                'valign': 'vcenter'
            }),
            'metric_value': self.workbook.add_format({
                'font_size': 14,
                'bold': True,
                'font_color': '#0066CC',
                'align': 'left',
                'valign': 'vcenter'
            }),
            'currency': self.workbook.add_format({
                'num_format': '#,##0.00',
                'align': 'right'
            }),
            'currency_usd': self.workbook.add_format({
                'num_format': '$#,##0.00',
                'align': 'right'
            }),
            'integer': self.workbook.add_format({
                'num_format': '#,##0',
                'align': 'right'
            }),
            'date': self.workbook.add_format({
                'num_format': 'yyyy-mm-dd hh:mm:ss',
                'align': 'center'
            }),
            'percent': self.workbook.add_format({
                'num_format': '0.00%',
                'align': 'right'
            }),
            'buy': self.workbook.add_format({
                'bg_color': '#C6EFCE',
                'font_color': '#006100'
            }),
            'sell': self.workbook.add_format({
                'bg_color': '#FFC7CE',
                'font_color': '#9C0006'
            }),
            'transfer': self.workbook.add_format({
                'bg_color': '#FFEB9C',
                'font_color': '#9C6500'
            })
        }
    
    def _create_summary_dashboard(self):
        """Create the summary dashboard sheet."""
        sheet = self.workbook.add_worksheet('📈 Summary Dashboard')
        
        # Set column widths
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:E', 15)
        
        row = 0
        
        # Title
        sheet.write(row, 0, 'CryptoBookKeeper - Transaction Summary', self.formats['title'])
        row += 2
        
        # Get summary statistics
        stats = self._get_summary_stats()
        
        # Key Metrics
        sheet.write(row, 0, 'Total Transactions:', self.formats['metric_label'])
        sheet.write(row, 1, stats['total_transactions'], self.formats['metric_value'])
        row += 1
        
        sheet.write(row, 0, 'Exchange Transactions:', self.formats['metric_label'])
        sheet.write(row, 1, stats['exchange_count'], self.formats['metric_value'])
        row += 1
        
        sheet.write(row, 0, 'On-Chain Transactions:', self.formats['metric_label'])
        sheet.write(row, 1, stats['onchain_count'], self.formats['metric_value'])
        row += 1
        
        sheet.write(row, 0, 'Unique Tokens:', self.formats['metric_label'])
        sheet.write(row, 1, stats['unique_tokens'], self.formats['metric_value'])
        row += 1
        
        sheet.write(row, 0, 'Date Range:', self.formats['metric_label'])
        sheet.write(row, 1, stats['date_range'], self.formats['metric_value'])
        row += 3
        
        # Transactions by Source
        sheet.write(row, 0, 'Transactions by Source', self.formats['header'])
        sheet.write(row, 1, 'Count', self.formats['header'])
        sheet.write(row, 2, 'Percentage', self.formats['header'])
        row += 1
        
        for source_data in stats['by_source']:
            sheet.write(row, 0, source_data['source'])
            sheet.write(row, 1, source_data['count'], self.formats['integer'])
            sheet.write(row, 2, source_data['pct'], self.formats['percent'])
            row += 1
        
        row += 2
        
        # Transactions by Chain
        sheet.write(row, 0, 'On-Chain by Network', self.formats['header'])
        sheet.write(row, 1, 'Count', self.formats['header'])
        sheet.write(row, 2, 'Percentage', self.formats['header'])
        row += 1
        
        for chain_data in stats['by_chain']:
            sheet.write(row, 0, chain_data['chain'])
            sheet.write(row, 1, chain_data['count'], self.formats['integer'])
            sheet.write(row, 2, chain_data['pct'], self.formats['percent'])
            row += 1
    
    def _create_all_transactions(self):
        """Create the all transactions sheet."""
        sheet = self.workbook.add_worksheet('📋 All Transactions')
        
        # Set column widths
        sheet.set_column('A:A', 20)  # Date
        sheet.set_column('B:B', 15)  # Source
        sheet.set_column('C:C', 12)  # Type
        sheet.set_column('D:D', 10)  # Token
        sheet.set_column('E:E', 15)  # Amount
        sheet.set_column('F:F', 12)  # Price
        sheet.set_column('G:G', 15)  # Fee
        sheet.set_column('H:H', 12)  # Chain
        sheet.set_column('I:I', 45)  # From
        sheet.set_column('J:J', 45)  # To
        
        # Headers
        headers = ['Date', 'Source', 'Side', 'Token', 'Amount', 'Price', 'Fee', 'Chain', 'From Address', 'To Address']
        for col, header in enumerate(headers):
            sheet.write(0, col, header, self.formats['header'])
        
        # Freeze top row
        sheet.freeze_panes(1, 0)
        
        # Get data
        query = """
            SELECT 
                ts_utc,
                source,
                side,
                base,
                amount,
                price,
                fee_amt,
                COALESCE(chain, '') as chain,
                COALESCE(addr_from, '') as addr_from,
                COALESCE(addr_to, '') as addr_to
            FROM tx_unified
            ORDER BY ts_utc DESC
        """
        
        results = self.conn.execute(query).fetchall()
        
        for row_idx, row_data in enumerate(results, start=1):
            sheet.write_datetime(row_idx, 0, row_data[0], self.formats['date'])
            sheet.write(row_idx, 1, row_data[1])
            sheet.write(row_idx, 2, row_data[2])
            sheet.write(row_idx, 3, row_data[3])
            sheet.write(row_idx, 4, row_data[4] or 0, self.formats['currency'])
            sheet.write(row_idx, 5, row_data[5] or 0, self.formats['currency'])
            sheet.write(row_idx, 6, row_data[6] or 0, self.formats['currency'])
            sheet.write(row_idx, 7, row_data[7])
            sheet.write(row_idx, 8, row_data[8])
            sheet.write(row_idx, 9, row_data[9])
        
        # Add autofilter
        sheet.autofilter(0, 0, len(results), len(headers) - 1)
    
    def _create_exchange_transactions(self):
        """Create the exchange transactions sheet."""
        sheet = self.workbook.add_worksheet('💱 Exchange')
        
        # Set column widths
        sheet.set_column('A:A', 20)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 12)
        sheet.set_column('D:D', 10)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 12)
        sheet.set_column('G:G', 15)
        sheet.set_column('H:H', 12)
        
        # Headers
        headers = ['Date', 'Exchange', 'Type', 'Token', 'Amount', 'Price', 'Total Value', 'Fee']
        for col, header in enumerate(headers):
            sheet.write(0, col, header, self.formats['header'])
        
        sheet.freeze_panes(1, 0)
        
        # Get exchange data
        query = """
            SELECT 
                ts_utc,
                source,
                side,
                base,
                amount,
                price,
                COALESCE(amount * price, 0) as total_value,
                fee_amt
            FROM tx_unified
            WHERE domain = 'exchange'
            ORDER BY ts_utc DESC
        """
        
        results = self.conn.execute(query).fetchall()
        
        for row_idx, row_data in enumerate(results, start=1):
            sheet.write_datetime(row_idx, 0, row_data[0], self.formats['date'])
            sheet.write(row_idx, 1, row_data[1])
            sheet.write(row_idx, 2, row_data[2])
            sheet.write(row_idx, 3, row_data[3])
            sheet.write(row_idx, 4, row_data[4] or 0, self.formats['currency'])
            sheet.write(row_idx, 5, row_data[5] or 0, self.formats['currency'])
            sheet.write(row_idx, 6, row_data[6] or 0, self.formats['currency_usd'])
            sheet.write(row_idx, 7, row_data[7] or 0, self.formats['currency'])
        
        sheet.autofilter(0, 0, len(results), len(headers) - 1)
    
    def _create_onchain_transactions(self):
        """Create the on-chain transactions sheet."""
        sheet = self.workbook.add_worksheet('⛓️ On-Chain')
        
        # Set column widths
        sheet.set_column('A:A', 20)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 12)
        sheet.set_column('D:D', 10)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 45)
        sheet.set_column('G:G', 45)
        
        # Headers
        headers = ['Date', 'Chain', 'Type', 'Token', 'Amount', 'From Address', 'To Address']
        for col, header in enumerate(headers):
            sheet.write(0, col, header, self.formats['header'])
        
        sheet.freeze_panes(1, 0)
        
        # Get on-chain data
        query = """
            SELECT 
                ts_utc,
                COALESCE(chain, 'unknown') as chain,
                side,
                base,
                amount,
                COALESCE(addr_from, '') as addr_from,
                COALESCE(addr_to, '') as addr_to
            FROM tx_unified
            WHERE domain = 'onchain'
            ORDER BY ts_utc DESC
        """
        
        results = self.conn.execute(query).fetchall()
        
        for row_idx, row_data in enumerate(results, start=1):
            sheet.write_datetime(row_idx, 0, row_data[0], self.formats['date'])
            sheet.write(row_idx, 1, row_data[1])
            sheet.write(row_idx, 2, row_data[2])
            sheet.write(row_idx, 3, row_data[3])
            sheet.write(row_idx, 4, row_data[4] or 0, self.formats['currency'])
            sheet.write(row_idx, 5, row_data[5])
            sheet.write(row_idx, 6, row_data[6])
        
        sheet.autofilter(0, 0, len(results), len(headers) - 1)
    
    def _create_yearly_summary(self):
        """Create the yearly summary sheet."""
        sheet = self.workbook.add_worksheet('📅 Yearly Summary')
        
        # Set column widths
        sheet.set_column('A:A', 15)
        sheet.set_column('B:E', 18)
        
        # Headers
        headers = ['Year', 'Total Transactions', 'Exchange Transactions', 'On-Chain Transactions', 'Unique Tokens']
        for col, header in enumerate(headers):
            sheet.write(0, col, header, self.formats['header'])
        
        # Get yearly data
        query = """
            SELECT 
                year,
                COUNT(*) as total,
                SUM(CASE WHEN domain = 'exchange' THEN 1 ELSE 0 END) as exchange_count,
                SUM(CASE WHEN domain = 'onchain' THEN 1 ELSE 0 END) as onchain_count,
                COUNT(DISTINCT base) as unique_tokens
            FROM tx_unified
            GROUP BY year
            ORDER BY year DESC
        """
        
        results = self.conn.execute(query).fetchall()
        
        for row_idx, row_data in enumerate(results, start=1):
            sheet.write(row_idx, 0, row_data[0], self.formats['integer'])
            sheet.write(row_idx, 1, row_data[1], self.formats['integer'])
            sheet.write(row_idx, 2, row_data[2], self.formats['integer'])
            sheet.write(row_idx, 3, row_data[3], self.formats['integer'])
            sheet.write(row_idx, 4, row_data[4], self.formats['integer'])
    
    def _get_summary_stats(self) -> Dict:
        """Get summary statistics for the dashboard."""
        stats = {}
        
        # Total transactions
        result = self.conn.execute("SELECT COUNT(*) FROM tx_unified").fetchone()
        stats['total_transactions'] = result[0]
        
        # By domain
        result = self.conn.execute("""
            SELECT 
                SUM(CASE WHEN domain = 'exchange' THEN 1 ELSE 0 END) as exchange,
                SUM(CASE WHEN domain = 'onchain' THEN 1 ELSE 0 END) as onchain
            FROM tx_unified
        """).fetchone()
        stats['exchange_count'] = result[0]
        stats['onchain_count'] = result[1]
        
        # Unique tokens
        result = self.conn.execute("SELECT COUNT(DISTINCT base) FROM tx_unified WHERE base != ''").fetchone()
        stats['unique_tokens'] = result[0]
        
        # Date range
        result = self.conn.execute("""
            SELECT 
                MIN(ts_utc)::VARCHAR as min_date,
                MAX(ts_utc)::VARCHAR as max_date
            FROM tx_unified
        """).fetchone()
        stats['date_range'] = f"{result[0][:10]} to {result[1][:10]}"
        
        # By source
        results = self.conn.execute("""
            SELECT 
                source,
                COUNT(*) as count,
                COUNT(*) * 1.0 / (SELECT COUNT(*) FROM tx_unified) as pct
            FROM tx_unified
            GROUP BY source
            ORDER BY count DESC
        """).fetchall()
        stats['by_source'] = [{'source': r[0], 'count': r[1], 'pct': r[2]} for r in results]
        
        # By chain
        results = self.conn.execute("""
            SELECT 
                COALESCE(chain, 'N/A') as chain,
                COUNT(*) as count,
                COUNT(*) * 1.0 / (SELECT COUNT(*) FROM tx_unified WHERE domain = 'onchain') as pct
            FROM tx_unified
            WHERE domain = 'onchain'
            GROUP BY chain
            ORDER BY count DESC
        """).fetchall()
        stats['by_chain'] = [{'chain': r[0], 'count': r[1], 'pct': r[2]} for r in results]
        
        return stats
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point for the script."""
    try:
        exporter = ExcelExporter()
        exporter.create_workbook()
        exporter.close()
        
        logger.info("✅ Excel export completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

