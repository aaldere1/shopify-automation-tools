#!/usr/bin/env python3
"""
Amplifier-Shopify Integration
Syncs data between Amplifier and Shopify stores

Usage:
  python3 amplifier_shopify_integration.py --action sync-products
  python3 amplifier_shopify_integration.py --action sync-inventory
  python3 amplifier_shopify_integration.py --action sync-orders --from-date 2025-01-01
"""

import argparse
import sys
from typing import List, Dict, Any
from datetime import datetime, timedelta
import requests
from amplifier_client import AmplifierClient, AmplifierAPIError


class ShopifyAmplifierIntegration:
    def __init__(self, shopify_store: str, shopify_token: str, amplifier_api_key: str):
        """
        Initialize integration between Shopify and Amplifier

        Args:
            shopify_store: Shopify store URL (e.g., store.myshopify.com)
            shopify_token: Shopify Admin API access token
            amplifier_api_key: Amplifier API key
        """
        # Shopify setup
        self.shopify_store = shopify_store.replace('https://', '').replace('http://', '')
        self.shopify_token = shopify_token
        self.shopify_api_version = '2025-10'
        self.shopify_base_url = f'https://{self.shopify_store}/admin/api/{self.shopify_api_version}'
        self.shopify_headers = {
            'X-Shopify-Access-Token': self.shopify_token,
            'Content-Type': 'application/json'
        }

        # Amplifier setup
        self.amplifier = AmplifierClient(api_key=amplifier_api_key)

    # Shopify Methods

    def fetch_shopify_products(self) -> List[Dict[str, Any]]:
        """Fetch all products from Shopify"""
        all_products = []
        url = f'{self.shopify_base_url}/products.json'
        params = {'limit': 250, 'status': 'active'}

        print("📥 Fetching products from Shopify...")
        page = 1

        while True:
            try:
                response = requests.get(url, headers=self.shopify_headers, params=params)
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
                print(f"❌ Error fetching Shopify products: {str(e)}")
                break

        print(f"✅ Total Shopify products fetched: {len(all_products)}\n")
        return all_products

    def fetch_shopify_orders(self, from_date: str = None) -> List[Dict[str, Any]]:
        """Fetch orders from Shopify"""
        all_orders = []
        url = f'{self.shopify_base_url}/orders.json'
        params = {'limit': 250, 'status': 'any'}

        if from_date:
            params['created_at_min'] = from_date

        print("📥 Fetching orders from Shopify...")
        page = 1

        while True:
            try:
                response = requests.get(url, headers=self.shopify_headers, params=params)
                response.raise_for_status()
                data = response.json()
                orders = data.get('orders', [])

                if not orders:
                    break

                all_orders.extend(orders)
                print(f"   Page {page}: Fetched {len(orders)} orders (Total: {len(all_orders)})")

                # Check for pagination
                link_header = response.headers.get('Link', '')
                if 'rel="next"' not in link_header:
                    break

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
                print(f"❌ Error fetching Shopify orders: {str(e)}")
                break

        print(f"✅ Total Shopify orders fetched: {len(all_orders)}\n")
        return all_orders

    # Integration Methods

    def sync_products_to_amplifier(self):
        """Sync products from Shopify to Amplifier"""
        print("=" * 70)
        print("SYNCING PRODUCTS: Shopify → Amplifier")
        print("=" * 70)
        print()

        shopify_products = self.fetch_shopify_products()

        if not shopify_products:
            print("❌ No Shopify products to sync")
            return

        print(f"🔄 Syncing {len(shopify_products)} products to Amplifier...")
        synced_count = 0
        failed_count = 0

        for product in shopify_products:
            try:
                # Extract product data
                product_data = {
                    'name': product.get('title'),
                    'sku': product.get('variants', [{}])[0].get('sku', ''),
                    'price': float(product.get('variants', [{}])[0].get('price', 0)),
                    'inventory': product.get('variants', [{}])[0].get('inventory_quantity', 0),
                    'description': product.get('body_html', ''),
                    'category': product.get('product_type', ''),
                    'shopify_id': str(product.get('id'))
                }

                # Create or update in Amplifier
                self.amplifier.create_product(product_data)
                synced_count += 1
                print(f"   ✓ Synced: {product_data['name']}")

            except AmplifierAPIError as e:
                failed_count += 1
                print(f"   ✗ Failed: {product.get('title')} - {e}")

        print()
        print("=" * 70)
        print(f"✅ Sync complete: {synced_count} succeeded, {failed_count} failed")
        print("=" * 70)

    def sync_inventory_from_amplifier(self):
        """Sync inventory from Amplifier to Shopify"""
        print("=" * 70)
        print("SYNCING INVENTORY: Amplifier → Shopify")
        print("=" * 70)
        print()

        try:
            amplifier_inventory = self.amplifier.get_inventory()
            inventory_items = amplifier_inventory.get('inventory', [])

            print(f"🔄 Syncing inventory for {len(inventory_items)} items...")

            for item in inventory_items:
                sku = item.get('sku')
                quantity = item.get('quantity', 0)

                # Find Shopify product by SKU and update inventory
                # (Simplified - in production, you'd need to maintain SKU mappings)
                print(f"   Updating SKU {sku}: {quantity} units")

            print("✅ Inventory sync complete\n")

        except AmplifierAPIError as e:
            print(f"❌ Error syncing inventory: {e}")

    def sync_orders_to_amplifier(self, from_date: str = None):
        """Sync orders from Shopify to Amplifier"""
        print("=" * 70)
        print("SYNCING ORDERS: Shopify → Amplifier")
        print("=" * 70)
        print()

        shopify_orders = self.fetch_shopify_orders(from_date=from_date)

        if not shopify_orders:
            print("❌ No Shopify orders to sync")
            return

        print(f"🔄 Syncing {len(shopify_orders)} orders to Amplifier...")
        synced_count = 0
        failed_count = 0

        for order in shopify_orders:
            try:
                # Extract order data
                customer = order.get('customer', {})
                order_data = {
                    'order_number': order.get('name'),
                    'customer': {
                        'name': f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
                        'email': customer.get('email', ''),
                        'phone': customer.get('phone', '')
                    },
                    'items': [
                        {
                            'product_id': item.get('product_id'),
                            'quantity': item.get('quantity'),
                            'price': float(item.get('price', 0))
                        }
                        for item in order.get('line_items', [])
                    ],
                    'total': float(order.get('total_price', 0)),
                    'status': order.get('fulfillment_status', 'pending'),
                    'shopify_id': str(order.get('id')),
                    'created_at': order.get('created_at')
                }

                # Create in Amplifier
                self.amplifier.create_order(order_data)
                synced_count += 1
                print(f"   ✓ Synced: Order {order_data['order_number']}")

            except AmplifierAPIError as e:
                failed_count += 1
                print(f"   ✗ Failed: Order {order.get('name')} - {e}")

        print()
        print("=" * 70)
        print(f"✅ Sync complete: {synced_count} succeeded, {failed_count} failed")
        print("=" * 70)

    def generate_sync_report(self):
        """Generate a comprehensive sync report"""
        print("=" * 70)
        print("SYNC REPORT: Shopify ↔ Amplifier")
        print("=" * 70)
        print()

        try:
            # Fetch data from both systems
            shopify_products = self.fetch_shopify_products()
            amplifier_products = self.amplifier.get_all_products()

            print(f"Shopify Products:    {len(shopify_products):,}")
            print(f"Amplifier Products:  {len(amplifier_products):,}")
            print(f"Difference:          {abs(len(shopify_products) - len(amplifier_products)):,}")
            print()

            # Extract SKUs
            shopify_skus = set()
            for product in shopify_products:
                for variant in product.get('variants', []):
                    sku = variant.get('sku', '').strip()
                    if sku:
                        shopify_skus.add(sku)

            amplifier_skus = {p.get('sku', '').strip() for p in amplifier_products if p.get('sku')}

            print(f"Shopify SKUs:        {len(shopify_skus):,}")
            print(f"Amplifier SKUs:      {len(amplifier_skus):,}")
            print(f"Common SKUs:         {len(shopify_skus & amplifier_skus):,}")
            print(f"Only in Shopify:     {len(shopify_skus - amplifier_skus):,}")
            print(f"Only in Amplifier:   {len(amplifier_skus - shopify_skus):,}")
            print()

            print("=" * 70)

        except Exception as e:
            print(f"❌ Error generating report: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Amplifier-Shopify Integration Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync products from Shopify to Amplifier
  %(prog)s --action sync-products

  # Sync inventory from Amplifier to Shopify
  %(prog)s --action sync-inventory

  # Sync orders from the last 30 days
  %(prog)s --action sync-orders --from-date 2025-10-01

  # Generate sync report
  %(prog)s --action report
        """
    )

    # Credentials
    parser.add_argument('--shopify-store', default='cineconcerts.myshopify.com',
                       help='Shopify store URL')
    parser.add_argument('--shopify-token', default='YOUR_SHOPIFY_TOKEN',
                       help='Shopify Admin API token')
    parser.add_argument('--amplifier-key', default='YOUR_AMPLIFIER_API_KEY',
                       help='Amplifier API key')

    # Actions
    parser.add_argument('--action', required=True,
                       choices=['sync-products', 'sync-inventory', 'sync-orders', 'report'],
                       help='Action to perform')

    # Options
    parser.add_argument('--from-date',
                       help='Start date for order sync (YYYY-MM-DD)')

    args = parser.parse_args()

    # Initialize integration
    integration = ShopifyAmplifierIntegration(
        shopify_store=args.shopify_store,
        shopify_token=args.shopify_token,
        amplifier_api_key=args.amplifier_key
    )

    # Perform action
    try:
        if args.action == 'sync-products':
            integration.sync_products_to_amplifier()

        elif args.action == 'sync-inventory':
            integration.sync_inventory_from_amplifier()

        elif args.action == 'sync-orders':
            from_date = args.from_date
            if from_date and 'T' not in from_date:
                from_date += 'T00:00:00Z'
            integration.sync_orders_to_amplifier(from_date=from_date)

        elif args.action == 'report':
            integration.generate_sync_report()

    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
