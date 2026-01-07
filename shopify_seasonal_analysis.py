#!/usr/bin/env python3
"""
Analyze seasonal demand patterns in Shopify orders
"""

import requests
from datetime import datetime
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
print("SHOPIFY SEASONAL DEMAND ANALYSIS")
print("=" * 80)
print()

# Fetch all orders
all_orders = []
url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/orders.json"
params = {
    'limit': 250,
    'status': 'any',
    'fields': 'id,created_at,total_price,line_items'
}

print("Fetching orders...")
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

print(f"\n✅ Total: {len(all_orders)} orders\n")

# Analyze by month and quarter
monthly_counts = defaultdict(int)
monthly_revenue = defaultdict(float)
monthly_items = defaultdict(int)

# Track by calendar month (Jan, Feb, etc.)
month_name_counts = defaultdict(list)  # Store all years for averaging
quarter_counts = defaultdict(list)

for order in all_orders:
    created_at = order.get('created_at')
    if created_at:
        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        # Full month key (YYYY-MM)
        month_key = dt.strftime('%Y-%m')
        monthly_counts[month_key] += 1
        monthly_revenue[month_key] += float(order.get('total_price', 0))

        # Count items
        line_items = order.get('line_items', [])
        monthly_items[month_key] += sum(item.get('quantity', 0) for item in line_items)

        # Calendar month (for seasonal averaging)
        month_name = dt.strftime('%m-%B')  # "01-January"
        month_name_counts[month_name].append(1)

        # Quarter
        quarter = f"Q{(dt.month-1)//3 + 1}"
        quarter_year = f"{dt.year}-{quarter}"
        quarter_counts[quarter_year].append(1)

# Calculate average by calendar month
print("=" * 80)
print("SEASONAL PATTERNS BY MONTH")
print("=" * 80)
print()

month_averages = {}
for month_name in sorted(month_name_counts.keys()):
    count = len(month_name_counts[month_name])
    month_averages[month_name] = count
    # Get years this month has data
    years_with_data = set()
    for month_key in monthly_counts.keys():
        if month_key[5:7] == month_name[:2]:  # Match month number
            years_with_data.add(month_key[:4])

    avg = count / len(years_with_data) if years_with_data else 0
    month_display = month_name[3:]  # Just the month name

    # Create visual bar
    bar_length = int(avg / 5)  # Scale for visualization
    bar = "█" * bar_length

    print(f"{month_display:10s}: {avg:6.1f} orders/month avg  {bar}")

# Identify peaks and troughs
sorted_avg = sorted(month_averages.items(), key=lambda x: x[1], reverse=True)
peaks = sorted_avg[:3]
troughs = sorted_avg[-3:]

print()
print("=" * 80)
print("PEAK MONTHS (Highest Average):")
for month, count in peaks:
    years = len([1 for k in monthly_counts.keys() if k[5:7] == month[:2]])
    print(f"  {month[3:]:10s}: {count/years:5.1f} orders/month")

print()
print("TROUGH MONTHS (Lowest Average):")
for month, count in troughs:
    years = len([1 for k in monthly_counts.keys() if k[5:7] == month[:2]])
    print(f"  {month[3:]:10s}: {count/years:5.1f} orders/month")

# Quarterly analysis
print()
print("=" * 80)
print("QUARTERLY PATTERNS")
print("=" * 80)
print()

# Aggregate by quarter across all years
quarter_totals = defaultdict(list)
for quarter_year, orders in quarter_counts.items():
    quarter = quarter_year.split('-')[1]  # Just Q1, Q2, etc.
    quarter_totals[quarter].extend(orders)

for quarter in ['Q1', 'Q2', 'Q3', 'Q4']:
    if quarter in quarter_totals:
        avg = len(quarter_totals[quarter]) / (len(quarter_totals[quarter]) / 100)  # Orders per quarter
        # Get actual quarters for this
        quarters_list = [k for k in quarter_counts.keys() if quarter in k]
        total = sum(len(quarter_counts[q]) for q in quarters_list)
        num_quarters = len(quarters_list)
        avg_per_quarter = total / num_quarters if num_quarters > 0 else 0

        # Map quarter to months
        quarter_months = {
            'Q1': 'Jan-Mar',
            'Q2': 'Apr-Jun',
            'Q3': 'Jul-Sep',
            'Q4': 'Oct-Dec'
        }

        bar_length = int(avg_per_quarter / 20)
        bar = "█" * bar_length

        print(f"{quarter} ({quarter_months[quarter]}): {avg_per_quarter:6.1f} orders/quarter avg  {bar}")

# Recent 24-month trend
print()
print("=" * 80)
print("RECENT 24-MONTH TREND (Seasonal Pattern)")
print("=" * 80)
print()

sorted_months = sorted(monthly_counts.keys())
recent_24 = sorted_months[-24:] if len(sorted_months) >= 24 else sorted_months

for month in recent_24:
    count = monthly_counts[month]
    revenue = monthly_revenue[month]
    items = monthly_items[month]

    # Visual indicator
    bar_length = int(count / 10)
    bar = "█" * bar_length

    print(f"{month}: {count:3d} orders  |  {items:4d} items  |  ${revenue:8,.0f}  {bar}")

# Calculate seasonality index
print()
print("=" * 80)
print("SEASONALITY INSIGHTS")
print("=" * 80)
print()

# Compare summer vs winter
summer_months = ['06', '07', '08']  # June, July, August
winter_months = ['11', '12', '01', '02']  # Nov, Dec, Jan, Feb

summer_orders = [monthly_counts[k] for k in monthly_counts.keys() if k[5:7] in summer_months]
winter_orders = [monthly_counts[k] for k in monthly_counts.keys() if k[5:7] in winter_months]

if summer_orders and winter_orders:
    summer_avg = statistics.mean(summer_orders)
    winter_avg = statistics.mean(winter_orders)

    print(f"Summer Average (Jun-Aug): {summer_avg:.1f} orders/month")
    print(f"Winter Average (Nov-Feb): {winter_avg:.1f} orders/month")
    print()

    if winter_avg > summer_avg:
        increase = ((winter_avg - summer_avg) / summer_avg) * 100
        print(f"📈 PEAK SEASON: Winter/Fall (Oct-Feb)")
        print(f"   Winter is {increase:.0f}% HIGHER than summer")
    else:
        increase = ((summer_avg - winter_avg) / winter_avg) * 100
        print(f"📈 PEAK SEASON: Summer (Jun-Aug)")
        print(f"   Summer is {increase:.0f}% HIGHER than winter")

    print()
    print(f"🔻 TROUGH SEASON: {'Summer' if winter_avg > summer_avg else 'Winter'}")

# Year-over-year comparison for same months
print()
print("YEAR-OVER-YEAR COMPARISON (Recent Years):")
print()

for month_num in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
    month_name = datetime.strptime(month_num, '%m').strftime('%B')
    print(f"{month_name}:")

    # Get data for this month across years
    for year in ['2023', '2024', '2025']:
        month_key = f"{year}-{month_num}"
        if month_key in monthly_counts:
            count = monthly_counts[month_key]
            revenue = monthly_revenue[month_key]
            print(f"  {year}: {count:3d} orders  ${revenue:8,.0f}")
    print()

print("=" * 80)
