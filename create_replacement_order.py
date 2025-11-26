#!/usr/bin/env python3
"""
Create a replacement order for a customer who didn't receive their original order.
Duplicates the original order with $0 total and sends confirmation email.

Usage:
    python3 create_replacement_order.py CC5875
    python3 create_replacement_order.py CC5875 --no-email
    python3 create_replacement_order.py CC5875 --dry-run
"""

import argparse
import json
import os
import sys
import requests


def load_env():
    """Load environment variables from .env file."""
    env_vars = {}
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value.strip('"').strip("'")
    return env_vars


class ShopifyReplacementOrder:
    def __init__(self, store_domain, access_token):
        self.store_domain = store_domain
        self.access_token = access_token
        self.api_version = '2025-10'
        self.base_url = f'https://{store_domain}/admin/api/{self.api_version}'
        self.headers = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json'
        }

    def get_order_by_name(self, order_name):
        """Fetch an order by its order number (e.g., CC5875)."""
        # Normalize order name - remove # if present
        order_name = order_name.lstrip('#')

        response = requests.get(
            f'{self.base_url}/orders.json',
            headers=self.headers,
            params={'name': order_name, 'status': 'any'}
        )

        if response.status_code != 200:
            print(f"Error fetching order: {response.status_code}")
            print(response.text)
            return None

        orders = response.json().get('orders', [])
        if not orders:
            print(f"No order found with name: {order_name}")
            return None

        return orders[0]

    def create_replacement(self, original_order, send_email=True, dry_run=False):
        """Create a replacement order based on the original."""

        original_name = original_order['name']

        # Build line items with $0 price
        line_items = []
        for item in original_order['line_items']:
            line_items.append({
                'variant_id': item['variant_id'],
                'quantity': item['quantity'],
                'price': '0.00'
            })

        # Build shipping address
        shipping_address = None
        if original_order.get('shipping_address'):
            addr = original_order['shipping_address']
            shipping_address = {
                'first_name': addr.get('first_name'),
                'last_name': addr.get('last_name'),
                'address1': addr.get('address1'),
                'address2': addr.get('address2'),
                'city': addr.get('city'),
                'province': addr.get('province'),
                'country': addr.get('country'),
                'zip': addr.get('zip'),
                'phone': addr.get('phone')
            }

        # Build billing address
        billing_address = None
        if original_order.get('billing_address'):
            addr = original_order['billing_address']
            billing_address = {
                'first_name': addr.get('first_name'),
                'last_name': addr.get('last_name'),
                'address1': addr.get('address1'),
                'address2': addr.get('address2'),
                'city': addr.get('city'),
                'province': addr.get('province'),
                'country': addr.get('country'),
                'zip': addr.get('zip'),
                'phone': addr.get('phone')
            }

        # Build order payload
        order_payload = {
            'order': {
                'line_items': line_items,
                'financial_status': 'paid',
                'send_receipt': send_email,
                'send_fulfillment_receipt': send_email,
                'note': f'Replacement for order {original_name} - customer reported not received',
                'tags': f'replacement, original-{original_name.lstrip("#")}',
                'shipping_lines': [
                    {
                        'title': 'Standard International',
                        'price': '0.00'
                    }
                ]
            }
        }

        # Add customer if exists
        if original_order.get('customer'):
            order_payload['order']['customer'] = {
                'id': original_order['customer']['id']
            }

        # Add addresses if they exist
        if shipping_address:
            order_payload['order']['shipping_address'] = shipping_address
        if billing_address:
            order_payload['order']['billing_address'] = billing_address

        if dry_run:
            print("\n=== DRY RUN - No order will be created ===\n")
            print("Would create replacement order with:")
            print(json.dumps(order_payload, indent=2))
            return None

        # Create the order
        response = requests.post(
            f'{self.base_url}/orders.json',
            headers=self.headers,
            json=order_payload
        )

        if response.status_code != 201:
            print(f"Error creating order: {response.status_code}")
            print(response.text)
            return None

        return response.json()['order']


def main():
    parser = argparse.ArgumentParser(
        description='Create a replacement order for a customer who did not receive their original order.'
    )
    parser.add_argument(
        'order_number',
        help='Original order number to duplicate (e.g., CC5875)'
    )
    parser.add_argument(
        '--no-email',
        action='store_true',
        help='Do not send confirmation email to customer'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be created without actually creating the order'
    )

    args = parser.parse_args()

    # Load credentials
    env = load_env()
    store = env.get('SHOPIFY_STORE_DOMAIN')
    token = env.get('SHOPIFY_ADMIN_TOKEN')

    if not store or not token:
        print("Error: SHOPIFY_STORE_DOMAIN and SHOPIFY_ADMIN_TOKEN must be set in .env file")
        sys.exit(1)

    client = ShopifyReplacementOrder(store, token)

    # Fetch original order
    print(f"Fetching original order: {args.order_number}")
    original_order = client.get_order_by_name(args.order_number)

    if not original_order:
        sys.exit(1)

    print(f"Found order: {original_order['name']}")
    print(f"  Customer: {original_order.get('customer', {}).get('first_name', 'N/A')} {original_order.get('customer', {}).get('last_name', '')}")
    print(f"  Email: {original_order.get('email', 'N/A')}")
    print(f"  Items: {len(original_order['line_items'])}")
    for item in original_order['line_items']:
        print(f"    - {item['title']} (x{item['quantity']})")
    print(f"  Original Total: ${original_order['total_price']}")

    # Create replacement
    send_email = not args.no_email
    print(f"\nCreating replacement order (send email: {send_email})...")

    new_order = client.create_replacement(
        original_order,
        send_email=send_email,
        dry_run=args.dry_run
    )

    if new_order:
        print(f"\n{'='*50}")
        print(f"SUCCESS! Replacement order created:")
        print(f"  New Order #: {new_order['name']}")
        print(f"  Order ID: {new_order['id']}")
        print(f"  Financial Status: {new_order['financial_status']}")
        print(f"  Total: ${new_order['total_price']}")
        print(f"  Email Sent: {send_email}")
        print(f"  Order Status URL: {new_order.get('order_status_url', 'N/A')}")
        print(f"{'='*50}")


if __name__ == '__main__':
    main()
