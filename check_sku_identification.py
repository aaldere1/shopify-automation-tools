#!/usr/bin/env python3
"""
Check how SKUs are identified, labeled, and coded across all three systems
"""

import requests
from amplifier_client import AmplifierClient
from printful_client import PrintfulClient

# Initialize clients
SHOPIFY_STORE = "cineconcerts.myshopify.com"
SHOPIFY_TOKEN = "YOUR_SHOPIFY_TOKEN"
AMPLIFIER_KEY = "YOUR_AMPLIFIER_API_KEY"
PRINTFUL_TOKEN = "YOUR_PRINTFUL_TOKEN"

amplifier = AmplifierClient(api_key=AMPLIFIER_KEY)
printful = PrintfulClient(access_token=PRINTFUL_TOKEN)

print("=" * 80)
print("SKU IDENTIFICATION & LABELING ANALYSIS")
print("=" * 80)
print()

# ==================== SHOPIFY ====================
print("SHOPIFY")
print("-" * 80)

shopify_headers = {'X-Shopify-Access-Token': SHOPIFY_TOKEN}
shopify_url = f"https://{SHOPIFY_STORE}/admin/api/2025-10/products.json"

response = requests.get(shopify_url, headers=shopify_headers, params={'limit': 5})
products = response.json()['products']

print(f"Checking {len(products)} products...")
print()

for product in products[:2]:
    print(f"Product: {product['title']}")
    print(f"  Product ID: {product['id']}")

    for variant in product['variants'][:3]:
        print(f"\n  Variant: {variant.get('title', 'Default')}")
        print(f"    Variant ID: {variant['id']}")
        print(f"    SKU: {variant.get('sku', 'N/A')}")
        print(f"    Barcode: {variant.get('barcode', 'N/A')}")
        print(f"    Inventory Item ID: {variant.get('inventory_item_id', 'N/A')}")

        # Check for other identification fields
        if variant.get('weight'):
            print(f"    Weight: {variant['weight']} {variant.get('weight_unit', 'N/A')}")
    print()

print("\nShopify Identification Methods:")
print("  ✓ SKU (alphanumeric code)")
print("  ✓ Barcode (UPC/EAN/ISBN)")
print("  ✓ Variant ID (Shopify internal)")
print("  ✓ Inventory Item ID (for inventory tracking)")

# ==================== AMPLIFIER ====================
print("\n" + "=" * 80)
print("AMPLIFIER")
print("-" * 80)

items = amplifier.get_all_items()
print(f"Checking {len(items[:5])} sample items...")
print()

for item in items[:5]:
    print(f"Item: {item.get('name', 'Unknown')}")
    print(f"  Item ID: {item.get('id')}")
    print(f"  SKU: {item.get('sku', 'N/A')}")
    print(f"  UPC/Barcode: {item.get('upc', 'N/A')}")
    print(f"  HTS Code: {item.get('htscode', 'N/A')}")

    if item.get('category'):
        print(f"  Category: {item['category']}")
    if item.get('style'):
        print(f"  Style: {item['style']}")
    print()

print("Amplifier Identification Methods:")
print("  ✓ SKU (primary identifier)")
print("  ✓ UPC (Universal Product Code / barcode)")
print("  ✓ Item ID (UUID)")
print("  ✓ HTS Code (Harmonized Tariff Schedule - for customs)")

# ==================== PRINTFUL ====================
print("\n" + "=" * 80)
print("PRINTFUL")
print("-" * 80)

# Check catalog products
products_response = printful.get_products(limit=3)
catalog_products = products_response.get('data', [])

print(f"Checking {len(catalog_products)} catalog products...")
print()

for product in catalog_products[:2]:
    print(f"Product: {product.get('name', 'Unknown')}")
    print(f"  Product ID: {product.get('id')}")
    print(f"  Type: {product.get('type', 'N/A')}")

    # Get variants
    try:
        variants_response = printful.get_product_variants(product['id'])
        variants = variants_response.get('data', [])

        for variant in variants[:3]:
            print(f"\n  Variant: {variant.get('name', 'Unknown')}")
            print(f"    Variant ID: {variant.get('id')}")
            print(f"    Size: {variant.get('size', 'N/A')}")
            print(f"    Color: {variant.get('color', 'N/A')}")
    except Exception as e:
        print(f"  Could not fetch variants: {e}")
    print()

# Check warehouse products (have SKUs)
print("\nChecking warehouse products...")
warehouse_response = printful.get_warehouse_products(store_id=7266986, limit=5)
warehouse_products = warehouse_response.get('data', [])

for product in warehouse_products[:3]:
    print(f"\nWarehouse Product: {product.get('name', 'Unknown')}")
    print(f"  Product ID: {product.get('id')}")

    for variant in product.get('warehouse_variants', [])[:2]:
        print(f"\n  Variant: {variant.get('name', 'Unknown')}")
        print(f"    Variant ID: {variant.get('id')}")
        print(f"    SKU: {variant.get('sku', 'N/A')}")
        print(f"    Retail Price: ${variant.get('retail_price', 'N/A')}")

print("\n\nPrintful Identification Methods:")
print("  Catalog Products (POD):")
print("    ✓ Product ID (numeric)")
print("    ✓ Variant ID (numeric)")
print("    ✓ Size/Color attributes (descriptive)")
print("  Warehouse Products:")
print("    ✓ SKU (custom alphanumeric)")
print("    ✓ Warehouse Variant ID (numeric)")

# ==================== SUMMARY ====================
print("\n" + "=" * 80)
print("CROSS-SYSTEM SUMMARY")
print("=" * 80)

print("""
PRIMARY IDENTIFICATION METHODS:

1. SKU (Stock Keeping Unit)
   - Shopify: Custom alphanumeric codes per variant
   - Amplifier: Primary identifier (e.g., "11013", "POLARBELL")
   - Printful: Used for warehouse products only

2. BARCODE/UPC
   - Shopify: Barcode field on variants (UPC/EAN/ISBN)
   - Amplifier: UPC field (e.g., "W:373569")
   - Printful: Not directly exposed via API

3. INTERNAL IDs
   - Shopify: Variant ID, Inventory Item ID
   - Amplifier: UUID (e.g., "9a92f832-b089-468e-b220-78cd7b116922")
   - Printful: Product ID, Variant ID (numeric)

4. ADDITIONAL CODES
   - Amplifier: HTS Code (Harmonized Tariff Schedule for customs/shipping)
   - All systems: Category/type classifications

RECOMMENDED ANSWER:
"SKUs are identified using a combination of custom alphanumeric SKU codes
and UPC barcodes. Each item has a unique SKU (e.g., '11013', 'POLARBELL')
and UPC barcode for scanning. We also track HTS codes for international
shipping compliance."
""")

print("=" * 80)
