#!/usr/bin/env python3
"""
Shopify Order Fetcher
A flexible tool to fetch and filter orders from Shopify Admin API

Usage:
  python3 shopify_order_fetcher.py --store your-store.myshopify.com --token shpat_xxx [OPTIONS]

Examples:
  # Get all $0.99 orders from a specific date
  python3 shopify_order_fetcher.py --store store.myshopify.com --token shpat_xxx --price 0.99 --from-date 2025-10-24

  # Get orders in a price range
  python3 shopify_order_fetcher.py --store store.myshopify.com --token shpat_xxx --min-price 10 --max-price 50

  # Get unfulfilled orders
  python3 shopify_order_fetcher.py --store store.myshopify.com --token shpat_xxx --fulfillment-status unfulfilled

  # Get orders with specific tag
  python3 shopify_order_fetcher.py --store store.myshopify.com --token shpat_xxx --tag DALB

  # Get orders from specific order number onwards
  python3 shopify_order_fetcher.py --store store.myshopify.com --token shpat_xxx --from-order CC5377
"""

import argparse
import csv
import json
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests


class ShopifyOrderFetcher:
    def __init__(self, shop_url: str, access_token: str):
        self.shop_url = shop_url.replace('https://', '').replace('http://', '')
        self.access_token = access_token
        self.api_version = '2025-10'
        self.base_url = f'https://{self.shop_url}/admin/api/{self.api_version}'
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }

    def get_order_by_name(self, order_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific order by name/number."""
        clean_order_name = order_name.strip().replace('#', '')
        url = f'{self.base_url}/orders.json'
        params = {'name': clean_order_name, 'status': 'any'}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            orders = response.json().get('orders', [])
            return orders[0] if orders else None
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching order {order_name}: {str(e)}")
            return None

    def fetch_orders(self,
                    created_at_min: Optional[str] = None,
                    created_at_max: Optional[str] = None,
                    status: str = 'any',
                    financial_status: Optional[str] = None,
                    fulfillment_status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch orders from Shopify with optional filters.

        Args:
            created_at_min: ISO 8601 date string for minimum creation date
            created_at_max: ISO 8601 date string for maximum creation date
            status: Order status (any, open, closed, cancelled)
            financial_status: Financial status filter
            fulfillment_status: Fulfillment status filter
        """
        all_orders = []
        url = f'{self.base_url}/orders.json'

        params = {
            'status': status,
            'limit': 250,
            'order': 'created_at asc'
        }

        if created_at_min:
            params['created_at_min'] = created_at_min
        if created_at_max:
            params['created_at_max'] = created_at_max
        if financial_status:
            params['financial_status'] = financial_status
        if fulfillment_status:
            params['fulfillment_status'] = fulfillment_status

        print(f"📥 Fetching orders from Shopify...")
        if created_at_min:
            print(f"   From: {created_at_min}")
        if created_at_max:
            print(f"   To: {created_at_max}")

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
                print(f"   Page {page}: Fetched {len(orders)} orders (Total: {len(all_orders)})")

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

    def filter_orders(self,
                     orders: List[Dict[str, Any]],
                     price: Optional[float] = None,
                     min_price: Optional[float] = None,
                     max_price: Optional[float] = None,
                     from_order: Optional[str] = None,
                     to_order: Optional[str] = None,
                     tag: Optional[str] = None,
                     email: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Filter orders based on various criteria.

        Args:
            price: Exact price match
            min_price: Minimum price
            max_price: Maximum price
            from_order: Starting order name
            to_order: Ending order name
            tag: Filter by tag
            email: Filter by customer email
        """
        print(f"🔍 Filtering orders...")
        filtered_orders = orders.copy()

        # Filter by order range
        if from_order:
            start_index = None
            for i, order in enumerate(filtered_orders):
                if order['name'] == from_order:
                    start_index = i
                    break
            if start_index is not None:
                filtered_orders = filtered_orders[start_index:]
                print(f"   From order: {from_order} (found at position {start_index + 1})")
            else:
                print(f"   ⚠️  Starting order {from_order} not found")

        if to_order:
            end_index = None
            for i, order in enumerate(filtered_orders):
                if order['name'] == to_order:
                    end_index = i
                    break
            if end_index is not None:
                filtered_orders = filtered_orders[:end_index + 1]
                print(f"   To order: {to_order} (found at position {end_index + 1})")

        # Filter by price
        if price is not None:
            filtered_orders = [o for o in filtered_orders if float(o.get('total_price', 0)) == price]
            print(f"   Exact price: ${price}")

        if min_price is not None:
            filtered_orders = [o for o in filtered_orders if float(o.get('total_price', 0)) >= min_price]
            print(f"   Min price: ${min_price}")

        if max_price is not None:
            filtered_orders = [o for o in filtered_orders if float(o.get('total_price', 0)) <= max_price]
            print(f"   Max price: ${max_price}")

        # Filter by tag
        if tag:
            filtered_orders = [o for o in filtered_orders if tag in o.get('tags', '').split(', ')]
            print(f"   Tag: {tag}")

        # Filter by email
        if email:
            filtered_orders = [o for o in filtered_orders if email.lower() in o.get('email', '').lower()]
            print(f"   Email contains: {email}")

        print(f"✅ Filtering complete: {len(filtered_orders)} orders match\n")
        return filtered_orders

    def save_to_csv(self, orders: List[Dict[str, Any]], filename: str):
        """Save orders to CSV file."""
        print(f"💾 Saving to CSV: {filename}")

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            writer.writerow([
                'Order Number',
                'Order Name',
                'Created At',
                'Total Price',
                'Currency',
                'Financial Status',
                'Fulfillment Status',
                'Customer Email',
                'Customer Name',
                'Items Count',
                'Tags',
                'Note'
            ])

            for order in orders:
                customer_name = ''
                if order.get('customer'):
                    first = order['customer'].get('first_name', '')
                    last = order['customer'].get('last_name', '')
                    customer_name = f"{first} {last}".strip()

                writer.writerow([
                    order.get('order_number', ''),
                    order.get('name', ''),
                    order.get('created_at', ''),
                    order.get('total_price', '0'),
                    order.get('currency', 'USD'),
                    order.get('financial_status', ''),
                    order.get('fulfillment_status', 'unfulfilled') or 'unfulfilled',
                    order.get('email', ''),
                    customer_name,
                    len(order.get('line_items', [])),
                    order.get('tags', ''),
                    order.get('note', '')
                ])

        print(f"✅ CSV saved successfully\n")

    def save_to_json(self, orders: List[Dict[str, Any]], filename: str):
        """Save orders to JSON file."""
        print(f"💾 Saving to JSON: {filename}")

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(orders, f, indent=2, ensure_ascii=False)

        print(f"✅ JSON saved successfully\n")

    def display_summary(self, orders: List[Dict[str, Any]]):
        """Display summary statistics."""
        if not orders:
            print("No orders to display")
            return

        print("=" * 70)
        print("ORDER SUMMARY")
        print("=" * 70)

        total_amount = sum(float(order.get('total_price', 0)) for order in orders)
        currencies = set(order.get('currency', 'USD') for order in orders)

        # Status breakdowns
        financial_statuses = {}
        fulfillment_statuses = {}
        for order in orders:
            fin_status = order.get('financial_status', 'unknown')
            ful_status = order.get('fulfillment_status', 'unfulfilled') or 'unfulfilled'
            financial_statuses[fin_status] = financial_statuses.get(fin_status, 0) + 1
            fulfillment_statuses[ful_status] = fulfillment_statuses.get(ful_status, 0) + 1

        print(f"Total Orders: {len(orders)}")
        print(f"Total Amount: {', '.join([f'{c} ${total_amount:.2f}' for c in currencies])}")

        print(f"\nFinancial Status:")
        for status, count in sorted(financial_statuses.items()):
            print(f"  {status}: {count}")

        print(f"\nFulfillment Status:")
        for status, count in sorted(fulfillment_statuses.items()):
            print(f"  {status}: {count}")

        print(f"\nOrder Range:")
        print(f"  First: {orders[0].get('name')} - {orders[0].get('created_at')}")
        print(f"  Last: {orders[-1].get('name')} - {orders[-1].get('created_at')}")

        print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='Fetch and filter orders from Shopify',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get all $0.99 orders
  %(prog)s --store store.myshopify.com --token shpat_xxx --price 0.99

  # Get orders in a price range
  %(prog)s --store store.myshopify.com --token shpat_xxx --min-price 10 --max-price 50

  # Get orders from specific date onwards
  %(prog)s --store store.myshopify.com --token shpat_xxx --from-date 2025-10-24

  # Get unfulfilled orders with a specific tag
  %(prog)s --store store.myshopify.com --token shpat_xxx --fulfillment-status unfulfilled --tag DALB

  # Get orders from specific order number onwards
  %(prog)s --store store.myshopify.com --token shpat_xxx --from-order CC5377
        """
    )

    # Required arguments
    parser.add_argument('--store', required=True, help='Shopify store URL (e.g., your-store.myshopify.com)')
    parser.add_argument('--token', required=True, help='Shopify Admin API access token (shpat_xxx)')

    # Date filters
    parser.add_argument('--from-date', help='Fetch orders from this date (YYYY-MM-DD or ISO 8601)')
    parser.add_argument('--to-date', help='Fetch orders up to this date (YYYY-MM-DD or ISO 8601)')

    # Price filters
    parser.add_argument('--price', type=float, help='Filter orders with exact price')
    parser.add_argument('--min-price', type=float, help='Filter orders with minimum price')
    parser.add_argument('--max-price', type=float, help='Filter orders with maximum price')

    # Order range filters
    parser.add_argument('--from-order', help='Start from specific order number (e.g., CC5377)')
    parser.add_argument('--to-order', help='End at specific order number (e.g., CC5400)')

    # Status filters
    parser.add_argument('--status', choices=['any', 'open', 'closed', 'cancelled'], default='any',
                       help='Order status (default: any)')
    parser.add_argument('--financial-status',
                       choices=['authorized', 'pending', 'paid', 'partially_paid', 'refunded',
                               'voided', 'partially_refunded', 'unpaid'],
                       help='Financial status filter')
    parser.add_argument('--fulfillment-status',
                       choices=['fulfilled', 'partial', 'unfulfilled'],
                       help='Fulfillment status filter')

    # Other filters
    parser.add_argument('--tag', help='Filter by order tag')
    parser.add_argument('--email', help='Filter by customer email (partial match)')

    # Output options
    parser.add_argument('--output', '-o', help='Output filename (without extension)')
    parser.add_argument('--format', choices=['csv', 'json', 'both'], default='csv',
                       help='Output format (default: csv)')
    parser.add_argument('--no-summary', action='store_true', help='Skip displaying summary')

    args = parser.parse_args()

    # Initialize fetcher
    fetcher = ShopifyOrderFetcher(args.store, args.token)

    # Determine date range
    created_at_min = None
    created_at_max = None

    if args.from_order:
        print(f"🔍 Looking up starting order: {args.from_order}")
        start_order = fetcher.get_order_by_name(args.from_order)
        if start_order:
            created_at_min = start_order['created_at']
            print(f"✅ Found order {args.from_order}")
            print(f"   Created at: {created_at_min}\n")
        else:
            print(f"❌ Could not find order {args.from_order}")
            sys.exit(1)
    elif args.from_date:
        created_at_min = args.from_date
        if 'T' not in created_at_min:
            created_at_min += 'T00:00:00Z'

    if args.to_date:
        created_at_max = args.to_date
        if 'T' not in created_at_max:
            created_at_max += 'T23:59:59Z'

    # Fetch orders
    orders = fetcher.fetch_orders(
        created_at_min=created_at_min,
        created_at_max=created_at_max,
        status=args.status,
        financial_status=args.financial_status,
        fulfillment_status=args.fulfillment_status
    )

    if not orders:
        print("❌ No orders found. Exiting.")
        sys.exit(1)

    # Apply additional filters
    filtered_orders = fetcher.filter_orders(
        orders,
        price=args.price,
        min_price=args.min_price,
        max_price=args.max_price,
        from_order=args.from_order,
        to_order=args.to_order,
        tag=args.tag,
        email=args.email
    )

    if not filtered_orders:
        print("❌ No orders match the filters. Exiting.")
        sys.exit(1)

    # Display summary
    if not args.no_summary:
        fetcher.display_summary(filtered_orders)

    # Generate output filename
    if args.output:
        base_filename = args.output
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f'shopify_orders_{timestamp}'

    # Save output
    if args.format in ['csv', 'both']:
        fetcher.save_to_csv(filtered_orders, f'{base_filename}.csv')

    if args.format in ['json', 'both']:
        fetcher.save_to_json(filtered_orders, f'{base_filename}.json')

    print("=" * 70)
    print("DONE!")
    print("=" * 70)
    print(f"✅ Exported {len(filtered_orders)} orders")
    if args.format in ['csv', 'both']:
        print(f"   CSV: {base_filename}.csv")
    if args.format in ['json', 'both']:
        print(f"   JSON: {base_filename}.json")
    print("=" * 70)


if __name__ == '__main__':
    main()
