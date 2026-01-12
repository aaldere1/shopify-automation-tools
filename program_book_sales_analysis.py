#!/usr/bin/env python3
"""
Program Book Sales Analysis for MinaLima Partnership Discussion

This script fetches all orders from Shopify and analyzes program book sales,
generating detailed reports suitable for business presentations.

Usage:
  python3 program_book_sales_analysis.py --store $SHOPIFY_STORE --token $SHOPIFY_TOKEN

  Or with environment variables:
  export SHOPIFY_STORE=cineconcerts.myshopify.com
  export SHOPIFY_TOKEN=shpat_xxx
  python3 program_book_sales_analysis.py

Output:
  - Console summary with key metrics
  - CSV export: program_book_sales_YYYYMMDD.csv (detailed line items)
  - CSV export: program_book_summary_YYYYMMDD.csv (aggregated by title)
"""

import argparse
import csv
import json
import os
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import requests


class ProgramBookAnalyzer:
    """Analyzes program book sales from Shopify orders."""
    
    # Keywords that identify program books in product titles
    BOOK_KEYWORDS = [
        'program book',
        'programme book', 
        'souvenir program',
        'souvenir programme',
        'collector book',
        'commemorative book',
    ]
    
    # SKU patterns that identify program books
    BOOK_SKU_PATTERNS = [
        'BOOK',      # HP1USABOOK, HP2BOOK, etc.
        'SOUV',      # HP1USASOUV (souvenir programs)
        'POLARBOOK', # Polar Express book
    ]
    
    def __init__(self, shop_url: str, access_token: str):
        self.shop_url = shop_url.replace('https://', '').replace('http://', '')
        self.access_token = access_token
        self.api_version = '2025-10'
        self.base_url = f'https://{self.shop_url}/admin/api/{self.api_version}'
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
    
    def is_program_book(self, line_item: Dict[str, Any]) -> bool:
        """Determine if a line item is a program book."""
        title = (line_item.get('title', '') or '').lower()
        sku = (line_item.get('sku', '') or '').upper()
        variant_title = (line_item.get('variant_title', '') or '').lower()
        
        # Check title for book keywords
        for keyword in self.BOOK_KEYWORDS:
            if keyword in title or keyword in variant_title:
                return True
        
        # Check SKU patterns
        for pattern in self.BOOK_SKU_PATTERNS:
            if pattern in sku:
                return True
        
        # Additional check for "book" in title (case insensitive)
        if 'book' in title and ('program' in title or 'souvenir' in title or 'collector' in title):
            return True
            
        return False
    
    def extract_show_name(self, title: str, sku: str) -> str:
        """Extract the show/film name from product title or SKU."""
        title_lower = title.lower()
        sku_upper = sku.upper() if sku else ''
        
        # Harry Potter detection
        if 'harry potter' in title_lower or sku_upper.startswith('HP'):
            # Try to extract film number
            for i in range(1, 9):
                if f'hp{i}' in sku_upper.lower() or f'film {i}' in title_lower or f'#{i}' in title:
                    film_names = {
                        1: "Harry Potter and the Sorcerer's Stone",
                        2: "Harry Potter and the Chamber of Secrets",
                        3: "Harry Potter and the Prisoner of Azkaban",
                        4: "Harry Potter and the Goblet of Fire",
                        5: "Harry Potter and the Order of the Phoenix",
                        6: "Harry Potter and the Half-Blood Prince",
                        7: "Harry Potter and the Deathly Hallows Part 1",
                        8: "Harry Potter and the Deathly Hallows Part 2",
                    }
                    return film_names.get(i, f"Harry Potter Film {i}")
            return "Harry Potter (Unspecified)"
        
        # Polar Express
        if 'polar' in title_lower or 'POLAR' in sku_upper:
            return "The Polar Express"
        
        # Elf
        if 'elf' in title_lower or 'ELF' in sku_upper:
            return "Elf"
        
        # Generic extraction - remove common suffixes
        clean_title = title
        for suffix in ['- Program Book', '- Souvenir Program', 'Program Book', 'Souvenir Program', 
                       '- Collector Edition', 'Collector Book']:
            if suffix.lower() in clean_title.lower():
                idx = clean_title.lower().find(suffix.lower())
                clean_title = clean_title[:idx].strip()
                break
        
        return clean_title if clean_title else "Unknown Show"
    
    def fetch_all_orders(self, 
                         created_at_min: Optional[str] = None,
                         created_at_max: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all orders with line item details."""
        all_orders = []
        url = f'{self.base_url}/orders.json'
        
        params = {
            'status': 'any',
            'limit': 250,
            'order': 'created_at asc'
        }
        
        if created_at_min:
            params['created_at_min'] = created_at_min
        if created_at_max:
            params['created_at_max'] = created_at_max
        
        print("📥 Fetching all orders from Shopify...")
        page = 1
        
        while True:
            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()
                orders = data.get('orders', [])
                
                if not orders:
                    break
                
                all_orders.extend(orders)
                print(f"   Page {page}: {len(orders)} orders (Total: {len(all_orders)})")
                
                # Check for pagination
                link_header = response.headers.get('Link', '')
                if 'rel="next"' not in link_header:
                    break
                
                # Extract next page URL
                next_link = None
                for link in link_header.split(','):
                    if 'rel="next"' in link:
                        next_link = link.split(';')[0].strip('<> ')
                        break
                
                if next_link:
                    url = next_link
                    params = {}
                    page += 1
                else:
                    break
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching orders: {str(e)}")
                break
        
        print(f"✅ Total orders fetched: {len(all_orders)}\n")
        return all_orders
    
    def extract_program_book_sales(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract all program book line items from orders."""
        book_sales = []
        
        for order in orders:
            order_number = order.get('name', '')
            order_date = order.get('created_at', '')
            financial_status = order.get('financial_status', '')
            fulfillment_status = order.get('fulfillment_status', '') or 'unfulfilled'
            currency = order.get('currency', 'USD')
            
            # Skip cancelled/refunded orders
            if financial_status in ['refunded', 'voided']:
                continue
            
            # Customer info
            customer = order.get('customer', {}) or {}
            customer_email = order.get('email', '')
            
            # Shipping address for geographic analysis
            shipping = order.get('shipping_address', {}) or {}
            country = shipping.get('country', '') or shipping.get('country_code', '')
            state = shipping.get('province', '') or shipping.get('province_code', '')
            city = shipping.get('city', '')
            
            # Sales channel
            source_name = order.get('source_name', 'web')
            
            # Check each line item
            for item in order.get('line_items', []):
                if self.is_program_book(item):
                    title = item.get('title', '')
                    sku = item.get('sku', '')
                    quantity = item.get('quantity', 0)
                    price = float(item.get('price', 0))
                    
                    # Handle partial refunds
                    refunded_qty = 0
                    for refund in order.get('refunds', []):
                        for refund_item in refund.get('refund_line_items', []):
                            if refund_item.get('line_item_id') == item.get('id'):
                                refunded_qty += refund_item.get('quantity', 0)
                    
                    net_quantity = quantity - refunded_qty
                    if net_quantity <= 0:
                        continue
                    
                    show_name = self.extract_show_name(title, sku)
                    
                    book_sales.append({
                        'order_number': order_number,
                        'order_date': order_date,
                        'order_date_formatted': datetime.fromisoformat(order_date.replace('Z', '+00:00')).strftime('%Y-%m-%d'),
                        'month': datetime.fromisoformat(order_date.replace('Z', '+00:00')).strftime('%Y-%m'),
                        'quarter': self._get_quarter(order_date),
                        'year': datetime.fromisoformat(order_date.replace('Z', '+00:00')).strftime('%Y'),
                        'product_title': title,
                        'variant_title': item.get('variant_title', ''),
                        'sku': sku,
                        'show_name': show_name,
                        'quantity': net_quantity,
                        'unit_price': price,
                        'line_total': price * net_quantity,
                        'currency': currency,
                        'financial_status': financial_status,
                        'fulfillment_status': fulfillment_status,
                        'country': country,
                        'state': state,
                        'city': city,
                        'sales_channel': source_name,
                        'customer_email': customer_email,
                    })
        
        return book_sales
    
    def _get_quarter(self, date_str: str) -> str:
        """Get quarter string from date."""
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        quarter = (dt.month - 1) // 3 + 1
        return f"{dt.year}-Q{quarter}"
    
    def generate_summary(self, book_sales: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive summary statistics."""
        if not book_sales:
            return {'error': 'No program book sales found'}
        
        summary = {
            'total_units': sum(s['quantity'] for s in book_sales),
            'total_revenue': sum(s['line_total'] for s in book_sales),
            'total_orders': len(set(s['order_number'] for s in book_sales)),
            'unique_products': len(set(s['product_title'] for s in book_sales)),
            'avg_unit_price': 0,
            'avg_units_per_order': 0,
            'date_range': {
                'first_sale': min(s['order_date_formatted'] for s in book_sales),
                'last_sale': max(s['order_date_formatted'] for s in book_sales),
            },
            'by_show': defaultdict(lambda: {'units': 0, 'revenue': 0, 'orders': set()}),
            'by_month': defaultdict(lambda: {'units': 0, 'revenue': 0, 'orders': set()}),
            'by_quarter': defaultdict(lambda: {'units': 0, 'revenue': 0, 'orders': set()}),
            'by_year': defaultdict(lambda: {'units': 0, 'revenue': 0, 'orders': set()}),
            'by_country': defaultdict(lambda: {'units': 0, 'revenue': 0}),
            'by_channel': defaultdict(lambda: {'units': 0, 'revenue': 0}),
        }
        
        for sale in book_sales:
            # By show
            show = sale['show_name']
            summary['by_show'][show]['units'] += sale['quantity']
            summary['by_show'][show]['revenue'] += sale['line_total']
            summary['by_show'][show]['orders'].add(sale['order_number'])
            
            # By month
            month = sale['month']
            summary['by_month'][month]['units'] += sale['quantity']
            summary['by_month'][month]['revenue'] += sale['line_total']
            summary['by_month'][month]['orders'].add(sale['order_number'])
            
            # By quarter
            quarter = sale['quarter']
            summary['by_quarter'][quarter]['units'] += sale['quantity']
            summary['by_quarter'][quarter]['revenue'] += sale['line_total']
            summary['by_quarter'][quarter]['orders'].add(sale['order_number'])
            
            # By year
            year = sale['year']
            summary['by_year'][year]['units'] += sale['quantity']
            summary['by_year'][year]['revenue'] += sale['line_total']
            summary['by_year'][year]['orders'].add(sale['order_number'])
            
            # By country
            country = sale['country'] or 'Unknown'
            summary['by_country'][country]['units'] += sale['quantity']
            summary['by_country'][country]['revenue'] += sale['line_total']
            
            # By channel
            channel = sale['sales_channel'] or 'web'
            summary['by_channel'][channel]['units'] += sale['quantity']
            summary['by_channel'][channel]['revenue'] += sale['line_total']
        
        # Calculate averages
        if summary['total_units'] > 0:
            summary['avg_unit_price'] = summary['total_revenue'] / summary['total_units']
        if summary['total_orders'] > 0:
            summary['avg_units_per_order'] = summary['total_units'] / summary['total_orders']
        
        # Convert sets to counts
        for show in summary['by_show']:
            summary['by_show'][show]['orders'] = len(summary['by_show'][show]['orders'])
        for month in summary['by_month']:
            summary['by_month'][month]['orders'] = len(summary['by_month'][month]['orders'])
        for quarter in summary['by_quarter']:
            summary['by_quarter'][quarter]['orders'] = len(summary['by_quarter'][quarter]['orders'])
        for year in summary['by_year']:
            summary['by_year'][year]['orders'] = len(summary['by_year'][year]['orders'])
        
        return summary
    
    def print_report(self, summary: Dict[str, Any]):
        """Print formatted report to console."""
        print("=" * 80)
        print("PROGRAM BOOK SALES ANALYSIS - EXECUTIVE SUMMARY")
        print("=" * 80)
        print()
        
        print("📊 OVERALL METRICS")
        print("-" * 40)
        print(f"  Total Units Sold:       {summary['total_units']:,}")
        print(f"  Total Revenue:          ${summary['total_revenue']:,.2f}")
        print(f"  Total Orders:           {summary['total_orders']:,}")
        print(f"  Unique Products:        {summary['unique_products']}")
        print(f"  Avg Price per Unit:     ${summary['avg_unit_price']:.2f}")
        print(f"  Avg Units per Order:    {summary['avg_units_per_order']:.2f}")
        print(f"  Date Range:             {summary['date_range']['first_sale']} to {summary['date_range']['last_sale']}")
        print()
        
        print("🎬 SALES BY SHOW/FILM")
        print("-" * 40)
        by_show_sorted = sorted(summary['by_show'].items(), key=lambda x: x[1]['revenue'], reverse=True)
        for show, data in by_show_sorted:
            pct = (data['revenue'] / summary['total_revenue'] * 100) if summary['total_revenue'] > 0 else 0
            print(f"  {show}")
            print(f"    Units: {data['units']:,}  |  Revenue: ${data['revenue']:,.2f}  |  {pct:.1f}% of total")
        print()
        
        print("📅 SALES BY YEAR")
        print("-" * 40)
        for year in sorted(summary['by_year'].keys()):
            data = summary['by_year'][year]
            print(f"  {year}: {data['units']:,} units  |  ${data['revenue']:,.2f}  |  {data['orders']} orders")
        print()
        
        print("📈 SALES BY QUARTER (Last 8 Quarters)")
        print("-" * 40)
        quarters_sorted = sorted(summary['by_quarter'].keys(), reverse=True)[:8]
        for quarter in reversed(quarters_sorted):
            data = summary['by_quarter'][quarter]
            print(f"  {quarter}: {data['units']:,} units  |  ${data['revenue']:,.2f}  |  {data['orders']} orders")
        print()
        
        print("🌍 TOP COUNTRIES")
        print("-" * 40)
        by_country_sorted = sorted(summary['by_country'].items(), key=lambda x: x[1]['revenue'], reverse=True)[:10]
        for country, data in by_country_sorted:
            pct = (data['revenue'] / summary['total_revenue'] * 100) if summary['total_revenue'] > 0 else 0
            print(f"  {country}: {data['units']:,} units  |  ${data['revenue']:,.2f}  |  {pct:.1f}%")
        print()
        
        print("=" * 80)
    
    def export_detailed_csv(self, book_sales: List[Dict[str, Any]], filename: str):
        """Export detailed line-item data to CSV."""
        print(f"💾 Exporting detailed data to: {filename}")
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Order Number',
                'Order Date',
                'Month',
                'Quarter',
                'Year',
                'Show/Film',
                'Product Title',
                'Variant',
                'SKU',
                'Quantity',
                'Unit Price',
                'Line Total',
                'Currency',
                'Country',
                'State/Province',
                'City',
                'Sales Channel',
                'Fulfillment Status'
            ])
            
            for sale in sorted(book_sales, key=lambda x: x['order_date']):
                writer.writerow([
                    sale['order_number'],
                    sale['order_date_formatted'],
                    sale['month'],
                    sale['quarter'],
                    sale['year'],
                    sale['show_name'],
                    sale['product_title'],
                    sale['variant_title'],
                    sale['sku'],
                    sale['quantity'],
                    f"{sale['unit_price']:.2f}",
                    f"{sale['line_total']:.2f}",
                    sale['currency'],
                    sale['country'],
                    sale['state'],
                    sale['city'],
                    sale['sales_channel'],
                    sale['fulfillment_status']
                ])
        
        print(f"✅ Exported {len(book_sales)} line items\n")
    
    def export_summary_csv(self, summary: Dict[str, Any], filename: str):
        """Export summary by show to CSV."""
        print(f"💾 Exporting summary to: {filename}")
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Summary by Show
            writer.writerow(['SALES BY SHOW/FILM'])
            writer.writerow(['Show', 'Units Sold', 'Revenue', '% of Total', 'Orders'])
            
            by_show_sorted = sorted(summary['by_show'].items(), key=lambda x: x[1]['revenue'], reverse=True)
            for show, data in by_show_sorted:
                pct = (data['revenue'] / summary['total_revenue'] * 100) if summary['total_revenue'] > 0 else 0
                writer.writerow([show, data['units'], f"${data['revenue']:.2f}", f"{pct:.1f}%", data['orders']])
            
            writer.writerow([])
            writer.writerow(['TOTALS', summary['total_units'], f"${summary['total_revenue']:.2f}", '100%', summary['total_orders']])
            
            # Monthly trends
            writer.writerow([])
            writer.writerow(['MONTHLY SALES TREND'])
            writer.writerow(['Month', 'Units Sold', 'Revenue', 'Orders'])
            
            for month in sorted(summary['by_month'].keys()):
                data = summary['by_month'][month]
                writer.writerow([month, data['units'], f"${data['revenue']:.2f}", data['orders']])
            
            # Quarterly trends
            writer.writerow([])
            writer.writerow(['QUARTERLY SALES TREND'])
            writer.writerow(['Quarter', 'Units Sold', 'Revenue', 'Orders'])
            
            for quarter in sorted(summary['by_quarter'].keys()):
                data = summary['by_quarter'][quarter]
                writer.writerow([quarter, data['units'], f"${data['revenue']:.2f}", data['orders']])
            
            # Geographic breakdown
            writer.writerow([])
            writer.writerow(['SALES BY COUNTRY'])
            writer.writerow(['Country', 'Units Sold', 'Revenue', '% of Total'])
            
            by_country_sorted = sorted(summary['by_country'].items(), key=lambda x: x[1]['revenue'], reverse=True)
            for country, data in by_country_sorted:
                pct = (data['revenue'] / summary['total_revenue'] * 100) if summary['total_revenue'] > 0 else 0
                writer.writerow([country, data['units'], f"${data['revenue']:.2f}", f"{pct:.1f}%"])
        
        print(f"✅ Summary exported\n")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze program book sales from Shopify',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with command line args
  %(prog)s --store cineconcerts.myshopify.com --token shpat_xxx

  # Use environment variables
  export SHOPIFY_STORE=cineconcerts.myshopify.com
  export SHOPIFY_TOKEN=shpat_xxx
  %(prog)s

  # Analyze specific date range
  %(prog)s --store store.myshopify.com --token shpat_xxx --from-date 2024-01-01 --to-date 2024-12-31
        """
    )
    
    parser.add_argument('--store', 
                        default=os.environ.get('SHOPIFY_STORE'),
                        help='Shopify store URL (or set SHOPIFY_STORE env var)')
    parser.add_argument('--token',
                        default=os.environ.get('SHOPIFY_TOKEN'),
                        help='Shopify Admin API token (or set SHOPIFY_TOKEN env var)')
    parser.add_argument('--from-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--to-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', '-o', help='Output filename prefix (default: program_book_sales_YYYYMMDD)')
    parser.add_argument('--json', action='store_true', help='Also export raw data as JSON')
    
    args = parser.parse_args()
    
    if not args.store or not args.token:
        print("❌ Error: Store URL and token are required.")
        print("   Provide via --store/--token flags or SHOPIFY_STORE/SHOPIFY_TOKEN environment variables.")
        sys.exit(1)
    
    # Initialize analyzer
    analyzer = ProgramBookAnalyzer(args.store, args.token)
    
    # Build date params
    created_at_min = None
    created_at_max = None
    
    if args.from_date:
        created_at_min = f"{args.from_date}T00:00:00Z"
    if args.to_date:
        created_at_max = f"{args.to_date}T23:59:59Z"
    
    # Fetch all orders
    orders = analyzer.fetch_all_orders(created_at_min, created_at_max)
    
    if not orders:
        print("❌ No orders found. Check your credentials and date range.")
        sys.exit(1)
    
    # Extract program book sales
    print("🔍 Analyzing orders for program book sales...")
    book_sales = analyzer.extract_program_book_sales(orders)
    
    if not book_sales:
        print("❌ No program book sales found in the orders.")
        print("   This might mean:")
        print("   - No products match the program book keywords/SKUs")
        print("   - The date range has no program book orders")
        sys.exit(1)
    
    print(f"✅ Found {len(book_sales)} program book line items\n")
    
    # Generate summary
    summary = analyzer.generate_summary(book_sales)
    
    # Print report
    analyzer.print_report(summary)
    
    # Generate output filenames
    timestamp = datetime.now().strftime('%Y%m%d')
    base_filename = args.output or f'program_book_sales_{timestamp}'
    
    # Export CSVs
    analyzer.export_detailed_csv(book_sales, f'{base_filename}_detailed.csv')
    analyzer.export_summary_csv(summary, f'{base_filename}_summary.csv')
    
    # Optionally export JSON
    if args.json:
        json_filename = f'{base_filename}_raw.json'
        print(f"💾 Exporting raw data to: {json_filename}")
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(book_sales, f, indent=2, ensure_ascii=False)
        print("✅ JSON exported\n")
    
    print("=" * 80)
    print("ANALYSIS COMPLETE!")
    print("=" * 80)
    print(f"📄 Detailed data:  {base_filename}_detailed.csv")
    print(f"📊 Summary report: {base_filename}_summary.csv")
    if args.json:
        print(f"📋 Raw JSON:       {base_filename}_raw.json")
    print()
    print("These files can be opened in Excel/Google Sheets for the MinaLima presentation.")
    print("=" * 80)


if __name__ == '__main__':
    main()
