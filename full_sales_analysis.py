#!/usr/bin/env python3
"""
Full Sales Analysis - All Products

Comprehensive analysis of all Shopify sales for business presentations.
Generates detailed breakdowns by product, category, time period, and geography.

Usage:
  python3 full_sales_analysis.py --store $SHOPIFY_STORE --token $SHOPIFY_TOKEN

  Or with environment variables:
  export SHOPIFY_STORE=cineconcerts.myshopify.com
  export SHOPIFY_TOKEN=shpat_xxx
  python3 full_sales_analysis.py

Output:
  - Console summary with key metrics
  - CSV: full_sales_YYYYMMDD_detailed.csv (all line items)
  - CSV: full_sales_YYYYMMDD_by_product.csv (aggregated by product)
  - CSV: full_sales_YYYYMMDD_by_category.csv (aggregated by category)
  - CSV: full_sales_YYYYMMDD_trends.csv (monthly/quarterly trends)
"""

import argparse
import csv
import json
import os
import re
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import requests


class FullSalesAnalyzer:
    """Analyzes all sales from Shopify orders."""

    # Product categorization rules (order matters - first match wins)
    CATEGORY_RULES = [
        # Program Books
        (r'program\s*book|programme\s*book|souvenir\s*program', 'Program Books'),
        (r'BOOK$|SOUV$', 'Program Books', 'sku'),
        (r'^POLARBOOK', 'Program Books', 'sku'),

        # Apparel
        (r't-?shirt|tee\b|shirt', 'Apparel - T-Shirts'),
        (r'hoodie|sweatshirt|sweater|pullover', 'Apparel - Hoodies/Sweatshirts'),
        (r'jacket|coat|outerwear', 'Apparel - Outerwear'),
        (r'hat|cap|beanie', 'Apparel - Headwear'),
        (r'socks?|sock\b', 'Apparel - Socks'),

        # Accessories
        (r'poster|print|art\s*print', 'Posters & Prints'),
        (r'mug|cup|tumbler|drinkware', 'Drinkware'),
        (r'pin|enamel\s*pin|lapel', 'Pins & Badges'),
        (r'keychain|key\s*chain|lanyard', 'Keychains & Lanyards'),
        (r'bag|tote|backpack|pouch', 'Bags & Totes'),
        (r'sticker|decal', 'Stickers'),
        (r'magnet', 'Magnets'),
        (r'patch|iron.on', 'Patches'),

        # Collectibles
        (r'wand|replica', 'Collectibles & Replicas'),
        (r'ornament', 'Ornaments'),
        (r'figure|figurine|statue', 'Figures & Statues'),

        # Media
        (r'vinyl|record|lp\b|album', 'Vinyl & Music'),
        (r'cd\b|soundtrack', 'CDs & Soundtracks'),
        (r'dvd|blu-?ray|video', 'DVDs & Video'),

        # Tickets & Events
        (r'ticket|admission|vip|meet.*greet|photo\s*op', 'Tickets & Experiences'),

        # Bundles
        (r'bundle|pack|set|collection|combo', 'Bundles & Sets'),

        # Gift Cards
        (r'gift\s*card|e-?gift|voucher', 'Gift Cards'),
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

    def categorize_product(self, title: str, sku: str) -> str:
        """Categorize a product based on title and SKU."""
        title_lower = (title or '').lower()
        sku_upper = (sku or '').upper()

        for rule in self.CATEGORY_RULES:
            pattern = rule[0]
            category = rule[1]
            match_field = rule[2] if len(rule) > 2 else 'title'

            if match_field == 'sku':
                if re.search(pattern, sku_upper):
                    return category
            else:
                if re.search(pattern, title_lower):
                    return category

        return 'Other'

    def extract_show_name(self, title: str, sku: str) -> str:
        """Extract the show/film name from product title or SKU."""
        title_lower = (title or '').lower()
        sku_upper = (sku or '').upper()

        # Harry Potter detection
        if 'harry potter' in title_lower or sku_upper.startswith('HP'):
            film_names = {
                1: "Harry Potter 1 (Sorcerer's Stone)",
                2: "Harry Potter 2 (Chamber of Secrets)",
                3: "Harry Potter 3 (Prisoner of Azkaban)",
                4: "Harry Potter 4 (Goblet of Fire)",
                5: "Harry Potter 5 (Order of the Phoenix)",
                6: "Harry Potter 6 (Half-Blood Prince)",
                7: "Harry Potter 7 (Deathly Hallows Pt 1)",
                8: "Harry Potter 8 (Deathly Hallows Pt 2)",
            }
            sku_match = re.search(r'HP(\d+)', sku_upper)
            if sku_match:
                film_num = int(sku_match.group(1))
                if 1 <= film_num <= 8:
                    return film_names.get(film_num, f"Harry Potter {film_num}")
            return "Harry Potter (General)"

        # Other shows
        if re.search(r'\bpolar\s*express\b', title_lower) or sku_upper.startswith('POLAR'):
            return "The Polar Express"
        if re.search(r'\belf\b', title_lower) or sku_upper.startswith('ELF'):
            return "Elf"
        if re.search(r'\bhome\s*alone\b', title_lower) or sku_upper.startswith('HA'):
            return "Home Alone"
        if re.search(r'\bgodfather\b', title_lower) or sku_upper.startswith('GF'):
            return "The Godfather"
        if re.search(r'\bstar\s*trek\b', title_lower) or sku_upper.startswith('ST'):
            return "Star Trek"
        if re.search(r'\bjurassic\b', title_lower) or sku_upper.startswith('JP'):
            return "Jurassic Park"
        if re.search(r'\bback\s*to.*future\b', title_lower) or sku_upper.startswith('BTTF'):
            return "Back to the Future"
        if re.search(r'\bgladiator\b', title_lower) or sku_upper.startswith('GLAD'):
            return "Gladiator"
        if re.search(r'\btitanic\b', title_lower) or sku_upper.startswith('TIT'):
            return "Titanic"

        return "Other/General"

    def fetch_all_orders(self,
                         created_at_min: Optional[str] = None,
                         created_at_max: Optional[str] = None) -> Tuple[List[Dict[str, Any]], bool]:
        """Fetch all orders with line item details."""
        all_orders = []
        url = f'{self.base_url}/orders.json'
        fetch_error = False

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
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                orders = data.get('orders') or []

                if not orders:
                    break

                all_orders.extend(orders)
                print(f"   Page {page}: {len(orders)} orders (Total: {len(all_orders)})")

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
                print(f"❌ Network error: {str(e)}")
                fetch_error = True
                break
            except (json.JSONDecodeError, ValueError) as e:
                print(f"❌ Invalid API response: {str(e)}")
                fetch_error = True
                break

        if fetch_error:
            print(f"⚠️  WARNING: Fetch incomplete. Only {len(all_orders)} orders retrieved.\n")
        else:
            print(f"✅ Total orders fetched: {len(all_orders)}\n")

        return all_orders, not fetch_error

    def extract_all_sales(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract all line items from orders."""
        all_sales = []

        for order in orders:
            order_number = order.get('name') or ''
            order_id = order.get('id')
            order_date = order.get('created_at') or ''
            financial_status = order.get('financial_status') or ''
            fulfillment_status = order.get('fulfillment_status') or 'unfulfilled'
            currency = order.get('currency') or 'USD'

            # Skip cancelled/refunded orders
            if order.get('cancelled_at') is not None:
                continue
            if financial_status in ['refunded', 'voided']:
                continue
            if not order_date:
                continue

            # Customer info
            customer_email = order.get('email') or ''

            # Shipping address
            shipping = order.get('shipping_address') or {}
            country = (shipping.get('country') or shipping.get('country_code')) or ''
            state = (shipping.get('province') or shipping.get('province_code')) or ''
            city = shipping.get('city') or ''

            # Sales channel
            source_name = order.get('source_name') or 'web'

            # Discount info
            total_discounts = float(order.get('total_discounts') or 0)

            for item in (order.get('line_items') or []):
                title = item.get('title') or ''
                sku = item.get('sku') or ''
                variant_title = item.get('variant_title') or ''
                quantity = item.get('quantity') or 0
                price = float(item.get('price') or 0)
                vendor = item.get('vendor') or ''
                product_id = item.get('product_id')

                # Handle partial refunds
                refunded_qty = 0
                for refund in (order.get('refunds') or []):
                    for refund_item in (refund.get('refund_line_items') or []):
                        if refund_item.get('line_item_id') == item.get('id'):
                            refunded_qty += refund_item.get('quantity') or 0

                net_quantity = quantity - refunded_qty
                if net_quantity <= 0:
                    continue

                # Parse date
                dt = datetime.fromisoformat(order_date.replace('Z', '+00:00'))

                category = self.categorize_product(title, sku)
                show_name = self.extract_show_name(title, sku)

                all_sales.append({
                    'order_number': order_number,
                    'order_id': order_id,
                    'order_date': order_date,
                    'order_date_formatted': dt.strftime('%Y-%m-%d'),
                    'month': dt.strftime('%Y-%m'),
                    'quarter': f"{dt.year}-Q{(dt.month - 1) // 3 + 1}",
                    'year': str(dt.year),
                    'product_title': title,
                    'variant_title': variant_title,
                    'sku': sku,
                    'vendor': vendor,
                    'product_id': product_id,
                    'category': category,
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

        return all_sales

    def generate_summary(self, sales: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive summary statistics."""
        if not sales:
            return {'error': 'No sales found'}

        # Revenue by currency
        revenue_by_currency = defaultdict(float)
        for s in sales:
            revenue_by_currency[s['currency']] += s['line_total']

        primary_currency = max(revenue_by_currency.keys(), key=lambda c: revenue_by_currency[c])

        summary = {
            'total_units': sum(s['quantity'] for s in sales),
            'revenue_by_currency': dict(revenue_by_currency),
            'primary_currency': primary_currency,
            'total_orders': len(set(s['order_number'] for s in sales)),
            'unique_products': len(set(s['product_title'] for s in sales)),
            'unique_skus': len(set(s['sku'] for s in sales if s['sku'])),
            'date_range': {
                'first_sale': min(s['order_date_formatted'] for s in sales),
                'last_sale': max(s['order_date_formatted'] for s in sales),
            },
            'by_category': defaultdict(lambda: {'units': 0, 'revenue': defaultdict(float), 'orders': set()}),
            'by_show': defaultdict(lambda: {'units': 0, 'revenue': defaultdict(float), 'orders': set()}),
            'by_product': defaultdict(lambda: {'units': 0, 'revenue': defaultdict(float), 'orders': set(), 'sku': '', 'category': ''}),
            'by_month': defaultdict(lambda: {'units': 0, 'revenue': defaultdict(float), 'orders': set()}),
            'by_quarter': defaultdict(lambda: {'units': 0, 'revenue': defaultdict(float), 'orders': set()}),
            'by_year': defaultdict(lambda: {'units': 0, 'revenue': defaultdict(float), 'orders': set()}),
            'by_country': defaultdict(lambda: {'units': 0, 'revenue': defaultdict(float)}),
            'by_channel': defaultdict(lambda: {'units': 0, 'revenue': defaultdict(float)}),
        }

        for sale in sales:
            currency = sale['currency']

            # By category
            cat = sale['category']
            summary['by_category'][cat]['units'] += sale['quantity']
            summary['by_category'][cat]['revenue'][currency] += sale['line_total']
            summary['by_category'][cat]['orders'].add(sale['order_number'])

            # By show
            show = sale['show_name']
            summary['by_show'][show]['units'] += sale['quantity']
            summary['by_show'][show]['revenue'][currency] += sale['line_total']
            summary['by_show'][show]['orders'].add(sale['order_number'])

            # By product
            prod = sale['product_title']
            summary['by_product'][prod]['units'] += sale['quantity']
            summary['by_product'][prod]['revenue'][currency] += sale['line_total']
            summary['by_product'][prod]['orders'].add(sale['order_number'])
            summary['by_product'][prod]['sku'] = sale['sku']
            summary['by_product'][prod]['category'] = sale['category']

            # By time
            summary['by_month'][sale['month']]['units'] += sale['quantity']
            summary['by_month'][sale['month']]['revenue'][currency] += sale['line_total']
            summary['by_month'][sale['month']]['orders'].add(sale['order_number'])

            summary['by_quarter'][sale['quarter']]['units'] += sale['quantity']
            summary['by_quarter'][sale['quarter']]['revenue'][currency] += sale['line_total']
            summary['by_quarter'][sale['quarter']]['orders'].add(sale['order_number'])

            summary['by_year'][sale['year']]['units'] += sale['quantity']
            summary['by_year'][sale['year']]['revenue'][currency] += sale['line_total']
            summary['by_year'][sale['year']]['orders'].add(sale['order_number'])

            # By geography
            country = sale['country'] or 'Unknown'
            summary['by_country'][country]['units'] += sale['quantity']
            summary['by_country'][country]['revenue'][currency] += sale['line_total']

            # By channel
            channel = sale['sales_channel'] or 'web'
            summary['by_channel'][channel]['units'] += sale['quantity']
            summary['by_channel'][channel]['revenue'][currency] += sale['line_total']

        # Convert sets to counts
        for cat in summary['by_category']:
            summary['by_category'][cat]['orders'] = len(summary['by_category'][cat]['orders'])
            summary['by_category'][cat]['revenue'] = dict(summary['by_category'][cat]['revenue'])
        for show in summary['by_show']:
            summary['by_show'][show]['orders'] = len(summary['by_show'][show]['orders'])
            summary['by_show'][show]['revenue'] = dict(summary['by_show'][show]['revenue'])
        for prod in summary['by_product']:
            summary['by_product'][prod]['orders'] = len(summary['by_product'][prod]['orders'])
            summary['by_product'][prod]['revenue'] = dict(summary['by_product'][prod]['revenue'])
        for m in summary['by_month']:
            summary['by_month'][m]['orders'] = len(summary['by_month'][m]['orders'])
            summary['by_month'][m]['revenue'] = dict(summary['by_month'][m]['revenue'])
        for q in summary['by_quarter']:
            summary['by_quarter'][q]['orders'] = len(summary['by_quarter'][q]['orders'])
            summary['by_quarter'][q]['revenue'] = dict(summary['by_quarter'][q]['revenue'])
        for y in summary['by_year']:
            summary['by_year'][y]['orders'] = len(summary['by_year'][y]['orders'])
            summary['by_year'][y]['revenue'] = dict(summary['by_year'][y]['revenue'])
        for country in summary['by_country']:
            summary['by_country'][country]['revenue'] = dict(summary['by_country'][country]['revenue'])
        for channel in summary['by_channel']:
            summary['by_channel'][channel]['revenue'] = dict(summary['by_channel'][channel]['revenue'])

        return summary

    CURRENCY_SYMBOLS = {'USD': '$', 'EUR': '€', 'GBP': '£', 'CAD': 'C$', 'AUD': 'A$'}

    def _fmt_rev(self, rev: Dict[str, float]) -> str:
        """Format revenue dict."""
        parts = []
        for curr, amt in sorted(rev.items(), key=lambda x: -x[1]):
            sym = self.CURRENCY_SYMBOLS.get(curr, f'{curr} ')
            parts.append(f"{sym}{amt:,.2f}")
        return ' + '.join(parts) if parts else '$0.00'

    def _get_primary_rev(self, rev: Dict[str, float], primary: str) -> float:
        """Get primary currency revenue for sorting."""
        return rev.get(primary, 0)

    def print_report(self, summary: Dict[str, Any]):
        """Print formatted report."""
        print("=" * 80)
        print("FULL SALES ANALYSIS - EXECUTIVE SUMMARY")
        print("=" * 80)
        print()

        primary = summary.get('primary_currency', 'USD')
        total_rev = summary.get('revenue_by_currency', {})
        primary_total = total_rev.get(primary, 0)

        print("📊 OVERALL METRICS")
        print("-" * 40)
        print(f"  Total Units Sold:       {summary['total_units']:,}")
        print(f"  Total Revenue:          {self._fmt_rev(total_rev)}")
        print(f"  Total Orders:           {summary['total_orders']:,}")
        print(f"  Unique Products:        {summary['unique_products']:,}")
        print(f"  Unique SKUs:            {summary['unique_skus']:,}")
        print(f"  Date Range:             {summary['date_range']['first_sale']} to {summary['date_range']['last_sale']}")
        print()

        print("📦 SALES BY CATEGORY")
        print("-" * 40)
        by_cat_sorted = sorted(
            summary['by_category'].items(),
            key=lambda x: self._get_primary_rev(x[1]['revenue'], primary),
            reverse=True
        )
        for cat, data in by_cat_sorted:
            cat_rev = data['revenue'].get(primary, 0)
            pct = (cat_rev / primary_total * 100) if primary_total > 0 else 0
            print(f"  {cat}")
            print(f"    Units: {data['units']:,}  |  Revenue: {self._fmt_rev(data['revenue'])}  |  {pct:.1f}%")
        print()

        print("🎬 TOP 10 SHOWS/FRANCHISES")
        print("-" * 40)
        by_show_sorted = sorted(
            summary['by_show'].items(),
            key=lambda x: self._get_primary_rev(x[1]['revenue'], primary),
            reverse=True
        )[:10]
        for show, data in by_show_sorted:
            show_rev = data['revenue'].get(primary, 0)
            pct = (show_rev / primary_total * 100) if primary_total > 0 else 0
            print(f"  {show}: {data['units']:,} units  |  {self._fmt_rev(data['revenue'])}  |  {pct:.1f}%")
        print()

        print("📅 SALES BY YEAR")
        print("-" * 40)
        for year in sorted(summary['by_year'].keys()):
            data = summary['by_year'][year]
            print(f"  {year}: {data['units']:,} units  |  {self._fmt_rev(data['revenue'])}  |  {data['orders']} orders")
        print()

        print("📈 SALES BY QUARTER (Last 8)")
        print("-" * 40)
        quarters_sorted = sorted(summary['by_quarter'].keys(), reverse=True)[:8]
        for quarter in reversed(quarters_sorted):
            data = summary['by_quarter'][quarter]
            print(f"  {quarter}: {data['units']:,} units  |  {self._fmt_rev(data['revenue'])}  |  {data['orders']} orders")
        print()

        print("🌍 TOP 10 COUNTRIES")
        print("-" * 40)
        by_country_sorted = sorted(
            summary['by_country'].items(),
            key=lambda x: self._get_primary_rev(x[1]['revenue'], primary),
            reverse=True
        )[:10]
        for country, data in by_country_sorted:
            country_rev = data['revenue'].get(primary, 0)
            pct = (country_rev / primary_total * 100) if primary_total > 0 else 0
            print(f"  {country}: {data['units']:,} units  |  {self._fmt_rev(data['revenue'])}  |  {pct:.1f}%")
        print()

        print("🏪 SALES CHANNELS")
        print("-" * 40)
        by_channel_sorted = sorted(
            summary['by_channel'].items(),
            key=lambda x: self._get_primary_rev(x[1]['revenue'], primary),
            reverse=True
        )
        for channel, data in by_channel_sorted:
            ch_rev = data['revenue'].get(primary, 0)
            pct = (ch_rev / primary_total * 100) if primary_total > 0 else 0
            print(f"  {channel}: {data['units']:,} units  |  {self._fmt_rev(data['revenue'])}  |  {pct:.1f}%")
        print()

        print("🏆 TOP 15 PRODUCTS BY REVENUE")
        print("-" * 40)
        by_prod_sorted = sorted(
            summary['by_product'].items(),
            key=lambda x: self._get_primary_rev(x[1]['revenue'], primary),
            reverse=True
        )[:15]
        for prod, data in by_prod_sorted:
            print(f"  {prod[:50]}{'...' if len(prod) > 50 else ''}")
            print(f"    {data['units']:,} units  |  {self._fmt_rev(data['revenue'])}  |  [{data['category']}]")
        print()

        print("=" * 80)

    def export_detailed_csv(self, sales: List[Dict[str, Any]], filename: str):
        """Export all line items."""
        print(f"💾 Exporting detailed data to: {filename}")

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Order Number', 'Order Date', 'Month', 'Quarter', 'Year',
                'Category', 'Show/Franchise', 'Product Title', 'Variant', 'SKU', 'Vendor',
                'Quantity', 'Unit Price', 'Line Total', 'Currency',
                'Country', 'State', 'City', 'Sales Channel', 'Fulfillment Status'
            ])

            for sale in sorted(sales, key=lambda x: x['order_date']):
                writer.writerow([
                    sale['order_number'], sale['order_date_formatted'], sale['month'],
                    sale['quarter'], sale['year'], sale['category'], sale['show_name'],
                    sale['product_title'], sale['variant_title'], sale['sku'], sale['vendor'],
                    sale['quantity'], f"{sale['unit_price']:.2f}", f"{sale['line_total']:.2f}",
                    sale['currency'], sale['country'], sale['state'], sale['city'],
                    sale['sales_channel'], sale['fulfillment_status']
                ])

        print(f"✅ Exported {len(sales)} line items\n")

    def export_by_product_csv(self, summary: Dict[str, Any], filename: str):
        """Export product-level summary."""
        print(f"💾 Exporting product summary to: {filename}")

        primary = summary.get('primary_currency', 'USD')

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Product', 'SKU', 'Category', 'Units Sold', 'Revenue', 'Orders'])

            by_prod_sorted = sorted(
                summary['by_product'].items(),
                key=lambda x: self._get_primary_rev(x[1]['revenue'], primary),
                reverse=True
            )
            for prod, data in by_prod_sorted:
                writer.writerow([
                    prod, data['sku'], data['category'],
                    data['units'], self._fmt_rev(data['revenue']), data['orders']
                ])

        print(f"✅ Exported {len(summary['by_product'])} products\n")

    def export_by_category_csv(self, summary: Dict[str, Any], filename: str):
        """Export category-level summary."""
        print(f"💾 Exporting category summary to: {filename}")

        primary = summary.get('primary_currency', 'USD')
        total_rev = summary.get('revenue_by_currency', {})
        primary_total = total_rev.get(primary, 0)

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # By Category
            writer.writerow(['SALES BY CATEGORY'])
            writer.writerow(['Category', 'Units', 'Revenue', '% of Total', 'Orders'])
            by_cat_sorted = sorted(
                summary['by_category'].items(),
                key=lambda x: self._get_primary_rev(x[1]['revenue'], primary),
                reverse=True
            )
            for cat, data in by_cat_sorted:
                cat_rev = data['revenue'].get(primary, 0)
                pct = (cat_rev / primary_total * 100) if primary_total > 0 else 0
                writer.writerow([cat, data['units'], self._fmt_rev(data['revenue']), f"{pct:.1f}%", data['orders']])

            writer.writerow([])
            writer.writerow(['TOTALS', summary['total_units'], self._fmt_rev(total_rev), '100%', summary['total_orders']])

            # By Show
            writer.writerow([])
            writer.writerow(['SALES BY SHOW/FRANCHISE'])
            writer.writerow(['Show', 'Units', 'Revenue', '% of Total', 'Orders'])
            by_show_sorted = sorted(
                summary['by_show'].items(),
                key=lambda x: self._get_primary_rev(x[1]['revenue'], primary),
                reverse=True
            )
            for show, data in by_show_sorted:
                show_rev = data['revenue'].get(primary, 0)
                pct = (show_rev / primary_total * 100) if primary_total > 0 else 0
                writer.writerow([show, data['units'], self._fmt_rev(data['revenue']), f"{pct:.1f}%", data['orders']])

            # By Country
            writer.writerow([])
            writer.writerow(['SALES BY COUNTRY'])
            writer.writerow(['Country', 'Units', 'Revenue', '% of Total'])
            by_country_sorted = sorted(
                summary['by_country'].items(),
                key=lambda x: self._get_primary_rev(x[1]['revenue'], primary),
                reverse=True
            )
            for country, data in by_country_sorted:
                country_rev = data['revenue'].get(primary, 0)
                pct = (country_rev / primary_total * 100) if primary_total > 0 else 0
                writer.writerow([country, data['units'], self._fmt_rev(data['revenue']), f"{pct:.1f}%"])

            # By Channel
            writer.writerow([])
            writer.writerow(['SALES BY CHANNEL'])
            writer.writerow(['Channel', 'Units', 'Revenue', '% of Total'])
            for channel, data in sorted(summary['by_channel'].items(), key=lambda x: -self._get_primary_rev(x[1]['revenue'], primary)):
                ch_rev = data['revenue'].get(primary, 0)
                pct = (ch_rev / primary_total * 100) if primary_total > 0 else 0
                writer.writerow([channel, data['units'], self._fmt_rev(data['revenue']), f"{pct:.1f}%"])

        print("✅ Category summary exported\n")

    def export_trends_csv(self, summary: Dict[str, Any], filename: str):
        """Export time-based trends."""
        print(f"💾 Exporting trends to: {filename}")

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Yearly
            writer.writerow(['YEARLY SALES'])
            writer.writerow(['Year', 'Units', 'Revenue', 'Orders'])
            for year in sorted(summary['by_year'].keys()):
                data = summary['by_year'][year]
                writer.writerow([year, data['units'], self._fmt_rev(data['revenue']), data['orders']])

            # Quarterly
            writer.writerow([])
            writer.writerow(['QUARTERLY SALES'])
            writer.writerow(['Quarter', 'Units', 'Revenue', 'Orders'])
            for quarter in sorted(summary['by_quarter'].keys()):
                data = summary['by_quarter'][quarter]
                writer.writerow([quarter, data['units'], self._fmt_rev(data['revenue']), data['orders']])

            # Monthly
            writer.writerow([])
            writer.writerow(['MONTHLY SALES'])
            writer.writerow(['Month', 'Units', 'Revenue', 'Orders'])
            for month in sorted(summary['by_month'].keys()):
                data = summary['by_month'][month]
                writer.writerow([month, data['units'], self._fmt_rev(data['revenue']), data['orders']])

        print("✅ Trends exported\n")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze all sales from Shopify',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--store', default=os.environ.get('SHOPIFY_STORE'),
                        help='Shopify store URL (or set SHOPIFY_STORE env var)')
    parser.add_argument('--token', default=os.environ.get('SHOPIFY_TOKEN'),
                        help='Shopify Admin API token (or set SHOPIFY_TOKEN env var)')
    parser.add_argument('--from-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--to-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', '-o', help='Output filename prefix')
    parser.add_argument('--json', action='store_true', help='Also export raw JSON')

    args = parser.parse_args()

    if not args.store or not args.token:
        print("❌ Error: Store URL and token required.")
        print("   Use --store/--token or set SHOPIFY_STORE/SHOPIFY_TOKEN env vars.")
        sys.exit(1)

    analyzer = FullSalesAnalyzer(args.store, args.token)

    created_at_min = f"{args.from_date}T00:00:00Z" if args.from_date else None
    created_at_max = f"{args.to_date}T23:59:59Z" if args.to_date else None

    orders, fetch_complete = analyzer.fetch_all_orders(created_at_min, created_at_max)

    if not orders:
        print("❌ No orders found.")
        sys.exit(1)

    print("🔍 Analyzing all sales...")
    sales = analyzer.extract_all_sales(orders)

    if not sales:
        print("❌ No sales found.")
        sys.exit(1)

    print(f"✅ Found {len(sales)} line items across {len(set(s['order_number'] for s in sales))} orders\n")

    summary = analyzer.generate_summary(sales)
    analyzer.print_report(summary)

    # Export files
    timestamp = datetime.now().strftime('%Y%m%d')
    base = args.output or f'full_sales_{timestamp}'

    analyzer.export_detailed_csv(sales, f'{base}_detailed.csv')
    analyzer.export_by_product_csv(summary, f'{base}_by_product.csv')
    analyzer.export_by_category_csv(summary, f'{base}_by_category.csv')
    analyzer.export_trends_csv(summary, f'{base}_trends.csv')

    if args.json:
        json_file = f'{base}_raw.json'
        print(f"💾 Exporting JSON to: {json_file}")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(sales, f, indent=2, ensure_ascii=False)
        print("✅ JSON exported\n")

    print("=" * 80)
    print("ANALYSIS COMPLETE!")
    print("=" * 80)
    print(f"📄 Detailed line items:  {base}_detailed.csv")
    print(f"📦 By product:           {base}_by_product.csv")
    print(f"📊 By category/show:     {base}_by_category.csv")
    print(f"📈 Trends (time-based):  {base}_trends.csv")
    if args.json:
        print(f"📋 Raw JSON:             {base}_raw.json")
    print()

    if not fetch_complete:
        print("⚠️  WARNING: Data may be incomplete due to network error!")
        print()

    print("=" * 80)


if __name__ == '__main__':
    main()
