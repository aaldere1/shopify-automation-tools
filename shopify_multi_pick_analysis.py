#!/usr/bin/env python3
"""
Analyze multi-pick percentage in Shopify orders
(Orders with multiple items vs single items)
"""

import requests
from collections import defaultdict
import statistics

SHOPIFY_STORE = "cineconcerts.myshopify.com"
SHOPIFY_TOKEN = "YOUR_SHOPIFY_TOKEN"
API_VERSION = "2025-10"

headers = {
    'X-Shopify-Access-Token': SHOPIFY_TOKEN,
    'Content-Type': 'application/json'
}

print("=" * 80)
print("SHOPIFY MULTI-PICK ANALYSIS")
print("=" * 80)
print()

# Fetch all orders
all_orders = []
url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/orders.json"
params = {
    'limit': 250,
    'status': 'any',
    'fields': 'id,created_at,line_items,financial_status'
}

print("Fetching orders with line item details...")
page_count = 0

while url:
    page_count += 1
    response = requests.get(url, headers=headers, params=params if page_count == 1 else None)

    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        break

    data = response.json()
    orders = data.get('orders', [])
    all_orders.extend(orders)

    print(f"  Page {page_count}: {len(all_orders)} total orders")

    # Check for next page
    link_header = response.headers.get('Link', '')
    url = None
    if link_header:
        for link in link_header.split(','):
            parts = link.split(';')
            if len(parts) == 2 and 'rel="next"' in parts[1]:
                url = parts[0].strip()[1:-1]
                break

print(f"\n✅ Total orders fetched: {len(all_orders)}\n")

# Analyze multi-pick vs single-pick
single_item_orders = 0
multi_item_orders = 0

# Track distribution
items_per_order_distribution = defaultdict(int)
total_items = 0
total_line_items = 0

# Track by unique SKUs vs quantity
orders_with_multiple_skus = 0
orders_with_quantity_only = 0

for order in all_orders:
    line_items = order.get('line_items', [])

    if not line_items:
        continue

    # Count total line items (unique products)
    num_line_items = len(line_items)
    total_line_items += num_line_items

    # Count total quantity
    total_qty = sum(item.get('quantity', 0) for item in line_items)
    total_items += total_qty

    # Classify order
    if num_line_items == 1 and total_qty == 1:
        # Single SKU, single item
        single_item_orders += 1
        items_per_order_distribution[1] += 1
    elif num_line_items == 1 and total_qty > 1:
        # Multiple of same SKU
        multi_item_orders += 1
        items_per_order_distribution[total_qty] += 1
        orders_with_quantity_only += 1
    else:
        # Multiple different SKUs
        multi_item_orders += 1
        items_per_order_distribution[total_qty] += 1
        orders_with_multiple_skus += 1

total_orders = len(all_orders)

# Calculate percentages
single_pct = (single_item_orders / total_orders) * 100
multi_pct = (multi_item_orders / total_orders) * 100

print("=" * 80)
print("MULTI-PICK ANALYSIS")
print("=" * 80)
print()

print(f"Total Orders: {total_orders:,}")
print()
print(f"Single-Item Orders:  {single_item_orders:5,} ({single_pct:5.1f}%)")
print(f"Multi-Item Orders:   {multi_item_orders:5,} ({multi_pct:5.1f}%)")
print()

# More detailed breakdown
print("Multi-Item Order Breakdown:")
print(f"  Multiple different SKUs: {orders_with_multiple_skus:5,} orders")
print(f"  Multiple of same SKU:    {orders_with_quantity_only:5,} orders")

# Calculate averages
avg_items_per_order = total_items / total_orders if total_orders > 0 else 0
avg_line_items_per_order = total_line_items / total_orders if total_orders > 0 else 0

print()
print("=" * 80)
print("ORDER STATISTICS")
print("=" * 80)
print()

print(f"Total Items Shipped: {total_items:,}")
print(f"Total Unique Line Items: {total_line_items:,}")
print()
print(f"Average Items per Order: {avg_items_per_order:.2f}")
print(f"Average Unique SKUs per Order: {avg_line_items_per_order:.2f}")

# Distribution analysis
print()
print("=" * 80)
print("ORDER SIZE DISTRIBUTION")
print("=" * 80)
print()

# Sort by number of items
sorted_distribution = sorted(items_per_order_distribution.items())

print("Items per Order | Count | Percentage")
print("-" * 50)

for num_items, count in sorted_distribution[:20]:  # Show top 20
    pct = (count / total_orders) * 100
    bar = "█" * int(pct)
    print(f"{num_items:3d} items      | {count:5,} | {pct:5.1f}%  {bar}")

# Show larger orders if they exist
large_orders = [k for k in sorted_distribution if k[0] > 20]
if large_orders:
    print("...")
    for num_items, count in large_orders[-5:]:  # Show 5 largest
        pct = (count / total_orders) * 100
        print(f"{num_items:3d} items      | {count:5,} | {pct:5.1f}%")

# Calculate percentiles
print()
print("=" * 80)
print("INSIGHTS")
print("=" * 80)
print()

# What percentage of orders have 2+ items?
orders_2_plus = sum(count for items, count in items_per_order_distribution.items() if items >= 2)
pct_2_plus = (orders_2_plus / total_orders) * 100

# What percentage have 3+ items?
orders_3_plus = sum(count for items, count in items_per_order_distribution.items() if items >= 3)
pct_3_plus = (orders_3_plus / total_orders) * 100

# What percentage have 5+ items?
orders_5_plus = sum(count for items, count in items_per_order_distribution.items() if items >= 5)
pct_5_plus = (orders_5_plus / total_orders) * 100

print(f"Orders with 2+ items:  {pct_2_plus:5.1f}% ({orders_2_plus:,} orders)")
print(f"Orders with 3+ items:  {pct_3_plus:5.1f}% ({orders_3_plus:,} orders)")
print(f"Orders with 5+ items:  {pct_5_plus:5.1f}% ({orders_5_plus:,} orders)")

# Multi-pick definition for warehousing
print()
print("=" * 80)
print("WAREHOUSE MULTI-PICK DEFINITION")
print("=" * 80)
print()

print("In warehouse operations, 'multi-pick' typically means:")
print("  → Orders requiring picking from multiple SKU locations")
print()
print(f"Orders with Multiple SKUs: {orders_with_multiple_skus:,} ({(orders_with_multiple_skus/total_orders)*100:.1f}%)")
print(f"Orders with Single SKU:    {single_item_orders + orders_with_quantity_only:,} ({((single_item_orders + orders_with_quantity_only)/total_orders)*100:.1f}%)")
print()
print("Note: Orders with multiple quantities of the same SKU can often")
print("be picked in a single location, reducing pick complexity.")

# Calculate median
all_item_counts = []
for num_items, count in items_per_order_distribution.items():
    all_item_counts.extend([num_items] * count)

if all_item_counts:
    median_items = statistics.median(all_item_counts)
    mode_items = max(items_per_order_distribution.items(), key=lambda x: x[1])[0]

    print()
    print(f"Median items per order: {median_items:.0f}")
    print(f"Most common order size: {mode_items} item(s)")

print()
print("=" * 80)
print("RECOMMENDED ANSWER")
print("=" * 80)
print()

print(f"Multi-item orders (2+ items): {multi_pct:.0f}%")
print(f"Single-item orders: {single_pct:.0f}%")
print()
print(f"For warehouse multi-pick planning:")
print(f"  {(orders_with_multiple_skus/total_orders)*100:.0f}% of orders require picking multiple different SKUs")
print(f"  Average: {avg_items_per_order:.1f} items per order")

print()
print("=" * 80)
