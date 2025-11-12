#!/usr/bin/env python3
"""
Shopify Batch Refund Tool
Process refunds for multiple orders from a CSV file

Usage:
  python3 shopify_batch_refund.py --store your-store.myshopify.com --token shpat_xxx --input orders.csv [OPTIONS]

Examples:
  # Full refund with confirmation
  python3 shopify_batch_refund.py --store store.myshopify.com --token shpat_xxx --input orders.csv

  # Full refund without confirmation (auto-approve)
  python3 shopify_batch_refund.py --store store.myshopify.com --token shpat_xxx --input orders.csv --yes

  # Dry run (preview only, no actual refunds)
  python3 shopify_batch_refund.py --store store.myshopify.com --token shpat_xxx --input orders.csv --dry-run

  # Partial refund with specific amount
  python3 shopify_batch_refund.py --store store.myshopify.com --token shpat_xxx --input orders.csv --amount 10.00

  # Send customer notification emails
  python3 shopify_batch_refund.py --store store.myshopify.com --token shpat_xxx --input orders.csv --notify

  # Restock inventory
  python3 shopify_batch_refund.py --store store.myshopify.com --token shpat_xxx --input orders.csv --restock
"""

import argparse
import csv
import json
import time
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests


class ShopifyRefundProcessor:
    def __init__(self, shop_url: str, access_token: str, rate_limit_delay: int = 12):
        self.shop_url = shop_url.replace('https://', '').replace('http://', '')
        self.access_token = access_token
        self.api_version = '2025-10'
        self.base_url = f'https://{self.shop_url}/admin/api/{self.api_version}'
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
        self.rate_limit_delay = rate_limit_delay

    def get_order_by_name(self, order_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve order details by order name/number."""
        clean_order_name = order_name.strip().replace('#', '')
        url = f'{self.base_url}/orders.json'
        params = {'name': clean_order_name, 'status': 'any'}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            orders = response.json().get('orders', [])
            return orders[0] if orders else None
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error fetching order {order_name}: {str(e)}")
            return None

    def get_payment_transaction(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Get the payment transaction for an order."""
        url = f'{self.base_url}/orders/{order_id}/transactions.json'

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            transactions = response.json().get('transactions', [])

            for trans in transactions:
                if trans['kind'] in ['capture', 'sale'] and trans['status'] == 'success':
                    return trans
            return None
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error fetching transactions: {str(e)}")
            return None

    def create_refund(self,
                     order: Dict[str, Any],
                     amount: Optional[float] = None,
                     notify: bool = False,
                     restock: bool = False,
                     note: str = "Batch refund processed",
                     dry_run: bool = False) -> bool:
        """
        Create a refund for an order.

        Args:
            order: Order dictionary
            amount: Optional specific refund amount (default: full refund)
            notify: Send customer notification
            restock: Restock inventory
            note: Refund note
            dry_run: Preview only, don't actually create refund
        """
        order_id = order['id']
        total_price = float(order['total_price'])
        refund_amount = amount if amount is not None else total_price

        if dry_run:
            print(f"  🔍 DRY RUN - Would refund ${refund_amount:.2f}")
            return True

        # Get payment transaction
        payment_trans = self.get_payment_transaction(order_id)
        if not payment_trans:
            print(f"  ❌ No payment transaction found")
            return False

        # Build refund line items
        refund_line_items = []
        restock_type = 'return' if restock else 'no_restock'

        for item in order.get('line_items', []):
            refund_line_items.append({
                'line_item_id': item['id'],
                'quantity': item['quantity'],
                'restock_type': restock_type
            })

        # Create refund
        url = f'{self.base_url}/orders/{order_id}/refunds.json'
        payload = {
            "refund": {
                "notify": notify,
                "note": note,
                "refund_line_items": refund_line_items,
                "transactions": [{
                    "parent_id": payment_trans['id'],
                    "amount": str(refund_amount),
                    "kind": "refund",
                    "gateway": payment_trans['gateway']
                }]
            }
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            print(f"  ✅ Refund created successfully (${refund_amount:.2f})")
            return True
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error creating refund: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"     Response: {e.response.text}")
            return False

    def process_refund(self,
                      order_name: str,
                      amount: Optional[float] = None,
                      notify: bool = False,
                      restock: bool = False,
                      note: str = "Batch refund processed",
                      dry_run: bool = False) -> bool:
        """Process a refund for an order."""
        print(f"\n📦 Processing order: {order_name}")

        # Get order details
        order = self.get_order_by_name(order_name)
        if not order:
            return False

        order_id = order['id']
        print(f"  📋 Order ID: {order_id}")
        print(f"     Total: {order.get('currency', 'USD')} ${order.get('total_price', '0')}")

        # Check if already fully refunded
        financial_status = order.get('financial_status')
        if financial_status == 'refunded' and amount is None:
            print(f"  ⚠️  Order is already fully refunded")
            return False

        # Create refund
        refund_label = "DRY RUN" if dry_run else "Creating refund"
        print(f"  💰 {refund_label}...")
        success = self.create_refund(order, amount, notify, restock, note, dry_run)

        return success


def read_orders_from_csv(csv_file: str) -> List[str]:
    """Read order numbers from a CSV file."""
    orders = []
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            # Find the order column
            order_column = None
            for col in reader.fieldnames:
                col_normalized = col.lower().replace(' ', '_')
                if col_normalized in ['order_number', 'order_name', 'order', 'name', 'number']:
                    order_column = col
                    break

            if not order_column:
                print(f"❌ Could not find order column in CSV. Available columns: {reader.fieldnames}")
                print("   Please ensure your CSV has a column named 'order_number', 'order_name', or 'order'")
                return []

            print(f"✅ Found order column: '{order_column}'")

            for row in reader:
                order_num = row[order_column].strip()
                if order_num:
                    orders.append(order_num)

        print(f"✅ Read {len(orders)} orders from CSV\n")
        return orders

    except FileNotFoundError:
        print(f"❌ CSV file not found: {csv_file}")
        return []
    except Exception as e:
        print(f"❌ Error reading CSV file: {str(e)}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description='Process batch refunds for Shopify orders',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full refund with confirmation
  %(prog)s --store store.myshopify.com --token shpat_xxx --input orders.csv

  # Auto-approve without confirmation
  %(prog)s --store store.myshopify.com --token shpat_xxx --input orders.csv --yes

  # Dry run (preview only)
  %(prog)s --store store.myshopify.com --token shpat_xxx --input orders.csv --dry-run

  # Partial refund with notifications
  %(prog)s --store store.myshopify.com --token shpat_xxx --input orders.csv --amount 10.00 --notify
        """
    )

    # Required arguments
    parser.add_argument('--store', required=True, help='Shopify store URL (e.g., your-store.myshopify.com)')
    parser.add_argument('--token', required=True, help='Shopify Admin API access token (shpat_xxx)')
    parser.add_argument('--input', '-i', required=True, help='Input CSV file with order numbers')

    # Refund options
    parser.add_argument('--amount', type=float, help='Specific refund amount (default: full refund)')
    parser.add_argument('--notify', action='store_true', help='Send customer notification emails')
    parser.add_argument('--restock', action='store_true', help='Restock inventory')
    parser.add_argument('--note', default='Batch refund processed', help='Refund note (default: "Batch refund processed")')

    # Execution options
    parser.add_argument('--yes', '-y', action='store_true', help='Auto-approve without confirmation')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, do not create actual refunds')
    parser.add_argument('--delay', type=int, default=12, help='Delay between refunds in seconds (default: 12)')

    # Output options
    parser.add_argument('--log', help='Custom log file name')
    parser.add_argument('--quiet', '-q', action='store_true', help='Minimal output')

    args = parser.parse_args()

    if not args.quiet:
        print("=" * 60)
        if args.dry_run:
            print("Shopify Batch Refund Tool - DRY RUN MODE")
        else:
            print("Shopify Batch Refund Tool")
        print("=" * 60)

    # Initialize processor
    processor = ShopifyRefundProcessor(args.store, args.token, args.delay)

    # Read orders from CSV
    orders = read_orders_from_csv(args.input)
    if not orders:
        sys.exit(1)

    # Determine refund settings
    refund_type = "Partial" if args.amount else "Full"
    notify_setting = "YES" if args.notify else "NO"
    restock_setting = "YES" if args.restock else "NO"

    # Confirm before processing
    if not args.quiet:
        print(f"⚠️  About to process {refund_type.upper()} REFUNDS for {len(orders)} orders")
        print(f"   - Refund amount: {f'${args.amount}' if args.amount else 'FULL (all items + shipping)'}")
        print(f"   - Customer notifications: {notify_setting}")
        print(f"   - Inventory restocking: {restock_setting}")
        if args.dry_run:
            print(f"   - Mode: DRY RUN (no actual refunds will be created)")

    if not args.yes and not args.dry_run:
        confirm = input("\n❓ Do you want to continue? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            print("❌ Cancelled by user")
            sys.exit(0)
    elif args.yes and not args.quiet:
        print("\n✅ Auto-confirmed (--yes flag)")

    # Process refunds
    if not args.quiet:
        print("\n" + "=" * 60)
        if args.dry_run:
            print("Starting dry run...")
        else:
            print("Starting batch refund processing...")
        print("=" * 60)

    successful = 0
    failed = 0
    start_time = time.time()

    for i, order_name in enumerate(orders, 1):
        if not args.quiet:
            print(f"\n[{i}/{len(orders)}]", end=" ")

        success = processor.process_refund(
            order_name,
            amount=args.amount,
            notify=args.notify,
            restock=args.restock,
            note=args.note,
            dry_run=args.dry_run
        )

        if success:
            successful += 1
        else:
            failed += 1

        # Rate limiting
        if i < len(orders) and not args.dry_run:
            if not args.quiet:
                print(f"  ⏳ Waiting {args.delay} seconds (rate limit)...")
            time.sleep(args.delay)

    elapsed_time = time.time() - start_time

    # Summary
    if not args.quiet:
        print("\n" + "=" * 60)
        if args.dry_run:
            print("Dry Run Complete")
        else:
            print("Batch Refund Processing Complete")
        print("=" * 60)
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total: {len(orders)}")
        print(f"⏱️  Time elapsed: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")

    # Save log
    if not args.dry_run:
        if args.log:
            log_file = args.log
        else:
            log_file = f"refund_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        with open(log_file, 'w') as f:
            f.write(f"Refund processing completed at {datetime.now()}\n")
            f.write(f"Mode: {'Dry Run' if args.dry_run else 'Live'}\n")
            f.write(f"Refund type: {refund_type}\n")
            if args.amount:
                f.write(f"Refund amount: ${args.amount}\n")
            f.write(f"Customer notifications: {notify_setting}\n")
            f.write(f"Inventory restocking: {restock_setting}\n")
            f.write(f"Successful: {successful}\n")
            f.write(f"Failed: {failed}\n")
            f.write(f"Total: {len(orders)}\n")
            f.write(f"Time elapsed: {elapsed_time:.1f} seconds\n")

        if not args.quiet:
            print(f"\n📝 Log saved to: {log_file}")


if __name__ == '__main__':
    main()
