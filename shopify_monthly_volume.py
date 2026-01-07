#!/usr/bin/env python3
"""
Analyze Shopify monthly order volumes
"""

import requests
from datetime import datetime
from collections import defaultdict
import statistics
from urllib.parse import parse_qs, urlparse

SHOPIFY_STORE = "cineconcerts.myshopify.com"
SHOPIFY_TOKEN = "YOUR_SHOPIFY_TOKEN"
API_VERSION = "2025-10"

headers = {
    'X-Shopify-Access-Token': SHOPIFY_TOKEN,
    'Content-Type': 'application/json'
}

print("=" * 80)
print("SHOPIFY MONTHLY ORDER VOLUME ANALYSIS")
print("=" * 80)
print()

# Fetch all orders with pagination
all_orders = []
url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/orders.json"
params = {
    'limit': 250,
    'status': 'any',  # Include all orders
    'fields': 'id,created_at,financial_status,fulfillment_status,total_price'
}

print("Fetching orders from Shopify...")
page_count = 0

while url:
    page_count += 1
    response = requests.get(url, headers=headers, params=params if page_count == 1 else None)

    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        break

    data = response.json()
    orders = data.get('orders', [])
    all_orders.extend(orders)

    print(f"  Page {page_count}: Fetched {len(orders)} orders (Total: {len(all_orders)})")

    # Check for next page in Link header
    link_header = response.headers.get('Link', '')
    url = None

    if link_header:
        links = {}
        for link in link_header.split(','):
            parts = link.split(';')
            if len(parts) == 2:
                url_part = parts[0].strip()[1:-1]  # Remove < >
                rel_part = parts[1].strip()
                if 'rel="next"' in rel_part:
                    url = url_part
                    break

print(f"\n✅ Total orders fetched: {len(all_orders)}")
print()

# Group orders by month
monthly_counts = defaultdict(int)
monthly_revenue = defaultdict(float)
yearly_counts = defaultdict(int)

for order in all_orders:
    created_at = order.get('created_at')
    if created_at:
        # Parse datetime: "2024-01-15T10:30:00-05:00"
        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        month_key = dt.strftime('%Y-%m')
        year_key = dt.strftime('%Y')

        monthly_counts[month_key] += 1
        yearly_counts[year_key] += 1

        # Track revenue
        total_price = float(order.get('total_price', 0))
        monthly_revenue[month_key] += total_price

# Sort months
sorted_months = sorted(monthly_counts.keys())

print("=" * 80)
print("MONTHLY ORDER BREAKDOWN")
print("=" * 80)
print()

# Show last 24 months or all months if less
display_months = sorted_months[-24:] if len(sorted_months) > 24 else sorted_months

for month in display_months:
    count = monthly_counts[month]
    revenue = monthly_revenue[month]
    print(f"{month}: {count:4d} orders  |  ${revenue:,.2f} revenue")

# Calculate statistics
print()
print("=" * 80)
print("STATISTICS")
print("=" * 80)
print()

monthly_volumes = list(monthly_counts.values())

print(f"Total Orders (All Time): {len(all_orders):,}")
print(f"Date Range: {sorted_months[0]} to {sorted_months[-1]}")
print(f"Months Analyzed: {len(monthly_counts)}")
print()

print(f"Average Monthly Volume: {statistics.mean(monthly_volumes):.1f} orders/month")
print(f"Median Monthly Volume: {statistics.median(monthly_volumes):.1f} orders/month")
print(f"Highest Month: {max(monthly_volumes)} orders")
print(f"Lowest Month: {min(monthly_volumes)} orders")

# Calculate by year
print()
print("YEARLY BREAKDOWN:")
for year in sorted(yearly_counts.keys()):
    count = yearly_counts[year]
    # Get months for this year
    year_months = [m for m in sorted_months if m.startswith(year)]
    months_count = len(year_months)
    avg_per_month = count / months_count if months_count > 0 else 0

    print(f"  {year}: {count:5d} orders ({months_count} months) = {avg_per_month:.1f} orders/month avg")

# Last 12 months analysis
print()
print("LAST 12 MONTHS:")
last_12_months = sorted_months[-12:]
last_12_count = sum(monthly_counts[m] for m in last_12_months)
last_12_avg = last_12_count / len(last_12_months) if last_12_months else 0
print(f"  Total: {last_12_count:,} orders")
print(f"  Average: {last_12_avg:.1f} orders/month")

# Calculate revenue stats
print()
print("REVENUE ANALYSIS:")
total_revenue = sum(monthly_revenue.values())
avg_monthly_revenue = statistics.mean(list(monthly_revenue.values()))
print(f"  Total Revenue (All Time): ${total_revenue:,.2f}")
print(f"  Average Monthly Revenue: ${avg_monthly_revenue:,.2f}")

print()
print("=" * 80)
