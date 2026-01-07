#!/usr/bin/env python3
"""
Quick script to inspect all fields available in Shopify product data
"""

import requests
import json

# Shopify API credentials
API_KEY = "YOUR_SHOPIFY_TOKEN"
STORE_URL = "cineconcerts.myshopify.com"
API_VERSION = "2025-10"

headers = {
    "X-Shopify-Access-Token": API_KEY,
    "Content-Type": "application/json"
}

# Fetch first product
url = f"https://{STORE_URL}/admin/api/{API_VERSION}/products.json?limit=1"
response = requests.get(url, headers=headers)
data = response.json()

if data.get('products'):
    product = data['products'][0]

    print("=" * 70)
    print("PRODUCT LEVEL FIELDS")
    print("=" * 70)
    for key in sorted(product.keys()):
        if key != 'variants' and key != 'images' and key != 'options':
            print(f"  {key}")

    print("\n" + "=" * 70)
    print("VARIANT LEVEL FIELDS")
    print("=" * 70)
    if product.get('variants'):
        variant = product['variants'][0]
        for key in sorted(variant.keys()):
            value = variant[key]
            # Show the value for dimension-related fields
            if any(term in key.lower() for term in ['weight', 'dimension', 'length', 'width', 'height', 'grams']):
                print(f"  {key}: {value}")
            else:
                print(f"  {key}")

    print("\n" + "=" * 70)
    print("SAMPLE VARIANT DATA (first variant)")
    print("=" * 70)
    print(json.dumps(product['variants'][0], indent=2))

else:
    print("No products found")
