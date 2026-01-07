#!/usr/bin/env python3
"""
Shopify SKU Scanner
Fetches all products and variants from Shopify to calculate unique SKUs

Usage:
  python3 shopify_sku_scanner.py --store your-store.myshopify.com --token shpat_xxx [OPTIONS]

Examples:
  # Get all unique SKUs
  python3 shopify_sku_scanner.py --store store.myshopify.com --token shpat_xxx

  # Export to CSV
  python3 shopify_sku_scanner.py --store store.myshopify.com --token shpat_xxx --output skus.csv

  # Only show summary (no export)
  python3 shopify_sku_scanner.py --store store.myshopify.com --token shpat_xxx --summary-only
"""

import argparse
import csv
import json
import sys
from typing import List, Dict, Any, Set
from datetime import datetime
import requests


class ShopifySKUScanner:
    def __init__(self, shop_url: str, access_token: str):
        self.shop_url = shop_url.replace('https://', '').replace('http://', '')
        self.access_token = access_token
        self.api_version = '2025-10'
        self.base_url = f'https://{self.shop_url}/admin/api/{self.api_version}'
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }

    def fetch_all_products(self) -> List[Dict[str, Any]]:
        """
        Fetch all products from Shopify using pagination.
        """
        all_products = []
        url = f'{self.base_url}/products.json'
        params = {
            'limit': 250,  # Maximum allowed by Shopify
            'status': 'active'
        }

        print(f"📥 Fetching products from Shopify...")

        page = 1
        while True:
            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()
                products = data.get('products', [])

                if not products:
                    break

                all_products.extend(products)
                print(f"   Page {page}: Fetched {len(products)} products (Total: {len(all_products)})")

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
                print(f"❌ Error fetching products: {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"   Response: {e.response.text}")
                break

        print(f"✅ Total products fetched: {len(all_products)}\n")
        return all_products

    def extract_skus(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract SKU information from products.

        Returns:
            Dictionary containing:
            - unique_skus: Set of unique SKUs
            - sku_details: List of dicts with detailed SKU info
            - stats: Statistics about SKUs
        """
        print(f"🔍 Extracting SKUs from {len(products)} products...")

        unique_skus = set()
        sku_details = []
        empty_skus = 0
        total_variants = 0

        for product in products:
            product_id = product.get('id')
            product_title = product.get('title', '')
            product_status = product.get('status', '')

            variants = product.get('variants', [])
            total_variants += len(variants)

            for variant in variants:
                variant_id = variant.get('id')
                sku = variant.get('sku', '').strip()
                variant_title = variant.get('title', '')
                price = variant.get('price', '0')
                inventory_quantity = variant.get('inventory_quantity', 0)

                if sku:
                    unique_skus.add(sku)
                else:
                    empty_skus += 1

                sku_details.append({
                    'sku': sku if sku else '[EMPTY]',
                    'product_id': product_id,
                    'product_title': product_title,
                    'product_status': product_status,
                    'variant_id': variant_id,
                    'variant_title': variant_title,
                    'price': price,
                    'inventory_quantity': inventory_quantity
                })

        stats = {
            'total_products': len(products),
            'total_variants': total_variants,
            'unique_skus': len(unique_skus),
            'empty_skus': empty_skus,
            'skus_with_values': len(unique_skus)
        }

        print(f"✅ SKU extraction complete\n")
        return {
            'unique_skus': unique_skus,
            'sku_details': sku_details,
            'stats': stats
        }

    def display_summary(self, sku_data: Dict[str, Any]):
        """Display summary statistics about SKUs."""
        stats = sku_data['stats']
        unique_skus = sku_data['unique_skus']

        print("=" * 70)
        print("SKU SUMMARY")
        print("=" * 70)
        print(f"Total Products: {stats['total_products']:,}")
        print(f"Total Variants: {stats['total_variants']:,}")
        print(f"Unique SKUs: {stats['unique_skus']:,}")
        print(f"Empty SKUs: {stats['empty_skus']:,}")
        print(f"SKUs with values: {stats['skus_with_values']:,}")

        if stats['total_variants'] > 0:
            fill_rate = (stats['skus_with_values'] / stats['total_variants']) * 100
            print(f"SKU Fill Rate: {fill_rate:.1f}%")

        print("\n" + "=" * 70)

    def save_to_csv(self, sku_data: Dict[str, Any], filename: str):
        """Save SKU details to CSV file."""
        print(f"💾 Saving to CSV: {filename}")

        sku_details = sku_data['sku_details']

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            writer.writerow([
                'SKU',
                'Product ID',
                'Product Title',
                'Product Status',
                'Variant ID',
                'Variant Title',
                'Price',
                'Inventory Quantity'
            ])

            for detail in sku_details:
                writer.writerow([
                    detail['sku'],
                    detail['product_id'],
                    detail['product_title'],
                    detail['product_status'],
                    detail['variant_id'],
                    detail['variant_title'],
                    detail['price'],
                    detail['inventory_quantity']
                ])

        print(f"✅ CSV saved successfully ({len(sku_details):,} rows)\n")

    def save_unique_skus(self, sku_data: Dict[str, Any], filename: str):
        """Save just the unique SKUs to a text file."""
        print(f"💾 Saving unique SKUs to: {filename}")

        unique_skus = sorted(sku_data['unique_skus'])

        with open(filename, 'w', encoding='utf-8') as f:
            for sku in unique_skus:
                f.write(f"{sku}\n")

        print(f"✅ Unique SKUs saved successfully ({len(unique_skus):,} SKUs)\n")

    def save_to_json(self, sku_data: Dict[str, Any], filename: str):
        """Save full SKU data to JSON file."""
        print(f"💾 Saving to JSON: {filename}")

        # Convert set to list for JSON serialization
        output_data = {
            'unique_skus': sorted(list(sku_data['unique_skus'])),
            'sku_details': sku_data['sku_details'],
            'stats': sku_data['stats']
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"✅ JSON saved successfully\n")


def main():
    parser = argparse.ArgumentParser(
        description='Scan Shopify store for unique SKUs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get all unique SKUs and display summary
  %(prog)s --store store.myshopify.com --token shpat_xxx

  # Export detailed SKU information to CSV
  %(prog)s --store store.myshopify.com --token shpat_xxx --output skus.csv

  # Export unique SKUs only to text file
  %(prog)s --store store.myshopify.com --token shpat_xxx --unique-only unique_skus.txt

  # Export to JSON
  %(prog)s --store store.myshopify.com --token shpat_xxx --format json
        """
    )

    # Required arguments
    parser.add_argument('--store', required=True,
                       help='Shopify store URL (e.g., your-store.myshopify.com)')
    parser.add_argument('--token', required=True,
                       help='Shopify Admin API access token (shpat_xxx)')

    # Output options
    parser.add_argument('--output', '-o',
                       help='Output filename for detailed CSV (includes all variants)')
    parser.add_argument('--unique-only',
                       help='Output filename for unique SKUs only (text file, one per line)')
    parser.add_argument('--format', choices=['csv', 'json', 'both'], default='csv',
                       help='Output format for detailed export (default: csv)')
    parser.add_argument('--summary-only', action='store_true',
                       help='Only display summary, do not save files')

    args = parser.parse_args()

    # Initialize scanner
    scanner = ShopifySKUScanner(args.store, args.token)

    # Fetch all products
    products = scanner.fetch_all_products()

    if not products:
        print("❌ No products found. Exiting.")
        sys.exit(1)

    # Extract SKUs
    sku_data = scanner.extract_skus(products)

    # Display summary
    scanner.display_summary(sku_data)

    # Save outputs if requested
    if not args.summary_only:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save detailed data
        if args.output:
            base_filename = args.output.replace('.csv', '').replace('.json', '')
        else:
            base_filename = f'shopify_skus_{timestamp}'

        if args.format in ['csv', 'both']:
            scanner.save_to_csv(sku_data, f'{base_filename}.csv')

        if args.format in ['json', 'both']:
            scanner.save_to_json(sku_data, f'{base_filename}.json')

        # Save unique SKUs if requested
        if args.unique_only:
            scanner.save_unique_skus(sku_data, args.unique_only)
        elif not args.output:
            # Auto-generate unique SKUs file
            unique_filename = f'unique_skus_{timestamp}.txt'
            scanner.save_unique_skus(sku_data, unique_filename)

        print("=" * 70)
        print("DONE!")
        print("=" * 70)
        print(f"✅ Found {sku_data['stats']['unique_skus']:,} unique SKUs")
        if args.format in ['csv', 'both']:
            print(f"   CSV: {base_filename}.csv")
        if args.format in ['json', 'both']:
            print(f"   JSON: {base_filename}.json")
        if args.unique_only:
            print(f"   Unique SKUs: {args.unique_only}")
        elif not args.output:
            print(f"   Unique SKUs: {unique_filename}")
        print("=" * 70)


if __name__ == '__main__':
    main()
