#!/usr/bin/env python3
"""
Compare Shopify and Amplifier inventory
Shows which SKUs are in one system but not the other
"""

from amplifier_client import AmplifierClient
import requests
import json
import os

# Credentials
SHOPIFY_STORE = "cineconcerts.myshopify.com"
SHOPIFY_TOKEN = os.environ.get("SHOPIFY_TOKEN", "YOUR_SHOPIFY_TOKEN")
AMPLIFIER_KEY = os.environ.get("AMPLIFIER_KEY", "YOUR_AMPLIFIER_API_KEY")

print("=" * 70)
print("SHOPIFY ↔ AMPLIFIER COMPARISON")
print("=" * 70)
print()

# Fetch Shopify products
print("📥 Fetching Shopify products...")
shopify_url = f"https://{SHOPIFY_STORE}/admin/api/2025-10/products.json"
shopify_headers = {
    'X-Shopify-Access-Token': SHOPIFY_TOKEN,
    'Content-Type': 'application/json'
}

shopify_products = []
params = {'limit': 250, 'status': 'active'}
page = 1

while True:
    response = requests.get(shopify_url, headers=shopify_headers, params=params)
    data = response.json()
    products = data.get('products', [])

    if not products:
        break

    shopify_products.extend(products)
    print(f"   Page {page}: {len(products)} products (Total: {len(shopify_products)})")

    link_header = response.headers.get('Link', '')
    if 'rel="next"' not in link_header:
        break

    for link in link_header.split(','):
        if 'rel="next"' in link:
            shopify_url = link.split(';')[0].strip('<> ')
            params = {}
            page += 1
            break
    else:
        break

print(f"✅ Total Shopify products: {len(shopify_products)}\n")

# Extract Shopify SKUs
shopify_skus = set()
shopify_sku_details = {}
for product in shopify_products:
    for variant in product.get('variants', []):
        sku = variant.get('sku', '').strip()
        if sku:
            shopify_skus.add(sku)
            shopify_sku_details[sku] = {
                'product_name': product.get('title'),
                'variant_title': variant.get('title'),
                'price': variant.get('price'),
                'inventory': variant.get('inventory_quantity', 0)
            }

# Fetch Amplifier items
print("📥 Fetching Amplifier items...")
amplifier = AmplifierClient(api_key=AMPLIFIER_KEY)
amplifier_items = amplifier.get_all_items()

# Extract Amplifier SKUs
amplifier_skus = set()
amplifier_sku_details = {}
for item in amplifier_items:
    sku = item.get('sku', '').strip()
    if sku:
        amplifier_skus.add(sku)
        amplifier_sku_details[sku] = {
            'name': item.get('name'),
            'cost': item.get('cost'),
            'retail_price': item.get('retail_price'),
            'inventory_available': item.get('inventory', {}).get('quantity_available', 0),
            'inventory_on_hand': item.get('inventory', {}).get('quantity_on_hand', 0)
        }

# Compare
print()
print("=" * 70)
print("COMPARISON SUMMARY")
print("=" * 70)
print(f"Shopify SKUs:           {len(shopify_skus):,}")
print(f"Amplifier SKUs:         {len(amplifier_skus):,}")
print(f"SKUs in both systems:   {len(shopify_skus & amplifier_skus):,}")
print(f"Only in Shopify:        {len(shopify_skus - amplifier_skus):,}")
print(f"Only in Amplifier:      {len(amplifier_skus - shopify_skus):,}")
print()

# Shopify totals
shopify_total_inventory = sum(d['inventory'] for d in shopify_sku_details.values())
print(f"Shopify Total Inventory: {shopify_total_inventory:,} units")

# Amplifier totals
amplifier_total_inventory = sum(d['inventory_on_hand'] for d in amplifier_sku_details.values())
print(f"Amplifier Total Inventory: {amplifier_total_inventory:,} units")
print()

# Show SKUs only in Shopify (first 10)
only_shopify = shopify_skus - amplifier_skus
if only_shopify:
    print("=" * 70)
    print(f"SKUS ONLY IN SHOPIFY (showing first 10 of {len(only_shopify)})")
    print("=" * 70)
    for sku in sorted(list(only_shopify))[:10]:
        details = shopify_sku_details[sku]
        print(f"SKU: {sku}")
        print(f"   Product: {details['product_name']}")
        print(f"   Variant: {details['variant_title']}")
        print(f"   Price: ${details['price']}")
        print(f"   Inventory: {details['inventory']}")
        print()

# Show SKUs only in Amplifier (first 10)
only_amplifier = amplifier_skus - shopify_skus
if only_amplifier:
    print("=" * 70)
    print(f"SKUS ONLY IN AMPLIFIER (showing first 10 of {len(only_amplifier)})")
    print("=" * 70)
    for sku in sorted(list(only_amplifier))[:10]:
        details = amplifier_sku_details[sku]
        print(f"SKU: {sku}")
        print(f"   Name: {details['name']}")
        print(f"   Cost: ${details['cost']}")
        print(f"   Retail: ${details['retail_price']}")
        print(f"   Inventory: {details['inventory_on_hand']}")
        print()

# Show SKUs in both systems with different inventory
print("=" * 70)
print("INVENTORY DISCREPANCIES (in both systems)")
print("=" * 70)
common_skus = shopify_skus & amplifier_skus
discrepancies = []

for sku in common_skus:
    shopify_inv = shopify_sku_details[sku]['inventory']
    amplifier_inv = amplifier_sku_details[sku]['inventory_on_hand']

    if shopify_inv != amplifier_inv:
        diff = abs(shopify_inv - amplifier_inv)
        discrepancies.append({
            'sku': sku,
            'shopify': shopify_inv,
            'amplifier': amplifier_inv,
            'difference': diff
        })

if discrepancies:
    # Sort by largest difference
    discrepancies.sort(key=lambda x: x['difference'], reverse=True)

    print(f"Found {len(discrepancies)} SKUs with inventory differences")
    print()
    print("Top 10 largest discrepancies:")
    for item in discrepancies[:10]:
        print(f"SKU: {item['sku']}")
        print(f"   Shopify: {item['shopify']:,} units")
        print(f"   Amplifier: {item['amplifier']:,} units")
        print(f"   Difference: {item['difference']:,} units")
        print()
else:
    print("✅ All common SKUs have matching inventory!")
    print()

print("=" * 70)
print("DONE!")
print("=" * 70)
