#!/usr/bin/env python3
"""
Check if products have metafields (which might contain dimensions)
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

# Fetch first few products
url = f"https://{STORE_URL}/admin/api/{API_VERSION}/products.json?limit=5"
response = requests.get(url, headers=headers)
data = response.json()

if data.get('products'):
    for product in data['products'][:3]:  # Check first 3 products
        product_id = product['id']
        print(f"\n{'=' * 70}")
        print(f"Product: {product['title']} (ID: {product_id})")
        print(f"{'=' * 70}")

        # Check product metafields
        meta_url = f"https://{STORE_URL}/admin/api/{API_VERSION}/products/{product_id}/metafields.json"
        meta_response = requests.get(meta_url, headers=headers)
        metafields = meta_response.json().get('metafields', [])

        if metafields:
            print(f"\nProduct Metafields ({len(metafields)} found):")
            for meta in metafields:
                print(f"  {meta['namespace']}.{meta['key']}: {meta['value']}")
        else:
            print("\nNo product metafields found")

        # Check variant metafields for first variant
        if product.get('variants'):
            variant = product['variants'][0]
            variant_id = variant['id']

            var_meta_url = f"https://{STORE_URL}/admin/api/{API_VERSION}/variants/{variant_id}/metafields.json"
            var_meta_response = requests.get(var_meta_url, headers=headers)
            var_metafields = var_meta_response.json().get('metafields', [])

            if var_metafields:
                print(f"\nVariant Metafields ({len(var_metafields)} found):")
                for meta in var_metafields:
                    print(f"  {meta['namespace']}.{meta['key']}: {meta['value']}")
            else:
                print("\nNo variant metafields found")

else:
    print("No products found")
