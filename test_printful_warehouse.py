#!/usr/bin/env python3
"""
Test Printful Warehouse Inventory
"""

from printful_client import PrintfulClient, PrintfulAPIError
import json

# Initialize client
ACCESS_TOKEN = "YOUR_PRINTFUL_TOKEN"
client = PrintfulClient(access_token=ACCESS_TOKEN)

print("=" * 70)
print("PRINTFUL WAREHOUSE INVENTORY TEST")
print("=" * 70)
print()

try:
    # First, get available stores to choose from
    print("Fetching available stores...")
    stores_response = client.get_stores()
    stores = stores_response.get('data', [])

    if stores:
        print(f"Found {len(stores)} store(s):")
        for store in stores:
            print(f"  - {store.get('name')} (ID: {store.get('id')})")
        print()

        # Use the CineConcerts store (ID: 7266986) or first available
        store_id = next((s.get('id') for s in stores if 'CineConcerts' in s.get('name', '')), stores[0].get('id'))
        print(f"Using store ID: {store_id}")
        print()
    else:
        print("⚠️  No stores found, attempting without store_id")
        store_id = None

    # Get warehouse products
    print("Fetching warehouse products...")
    warehouse_response = client.get_warehouse_products(store_id=store_id, limit=100)
    warehouse_products = warehouse_response.get('data', [])
    paging = warehouse_response.get('paging', {})

    print(f"✅ Found {len(warehouse_products)} warehouse products on this page")
    print(f"   Total warehouse products: {paging.get('total', 0)}")
    print()

    if warehouse_products:
        print("=" * 70)
        print("WAREHOUSE INVENTORY DETAILS")
        print("=" * 70)

        for idx, product in enumerate(warehouse_products[:10], 1):
            print(f"\n{idx}. Warehouse Product:")
            print(f"   ID: {product.get('id')}")
            print(f"   External ID: {product.get('external_id')}")
            print(f"   Variant ID: {product.get('variant_id')}")
            print(f"   Warehouse Product Variant ID: {product.get('warehouse_product_variant_id')}")

            # Inventory details
            quantity = product.get('quantity', 0)
            print(f"   Quantity: {quantity}")

            # Get variant details if available
            variant = product.get('variant', {})
            if variant:
                print(f"   Variant Name: {variant.get('name', 'N/A')}")
                print(f"   Variant SKU: {variant.get('sku', 'N/A')}")

            # Get product details if available
            prod_info = product.get('product', {})
            if prod_info:
                print(f"   Product Name: {prod_info.get('name', 'N/A')}")

            # Files/images
            files = product.get('files', [])
            if files:
                print(f"   Files: {len(files)} file(s)")

        # Summary statistics
        print()
        print("=" * 70)
        print("WAREHOUSE INVENTORY SUMMARY")
        print("=" * 70)

        total_quantity = sum(p.get('quantity', 0) for p in warehouse_products)
        print(f"Total Warehouse Products: {paging.get('total', len(warehouse_products))}")
        print(f"Total Units in Sample: {total_quantity}")

        # Group by variant if possible
        variants = {}
        for p in warehouse_products:
            variant_id = p.get('variant_id')
            if variant_id:
                if variant_id not in variants:
                    variants[variant_id] = {
                        'count': 0,
                        'quantity': 0,
                        'name': p.get('variant', {}).get('name', 'Unknown')
                    }
                variants[variant_id]['count'] += 1
                variants[variant_id]['quantity'] += p.get('quantity', 0)

        if variants:
            print(f"\nUnique Variants: {len(variants)}")
            print("\nTop Variants by Quantity:")
            sorted_variants = sorted(variants.items(), key=lambda x: x[1]['quantity'], reverse=True)
            for variant_id, info in sorted_variants[:10]:
                print(f"   {info['name']}: {info['quantity']} units ({info['count']} products)")

    else:
        print("ℹ️  No warehouse products found")
        print()
        print("This could mean:")
        print("  - No warehouse inventory is currently stored")
        print("  - All products are on-demand (catalog products)")
        print("  - Need different store_id or permissions")

    # Compare with catalog products
    print()
    print("=" * 70)
    print("CATALOG vs WAREHOUSE COMPARISON")
    print("=" * 70)

    catalog_response = client.get_products(limit=10)
    catalog_total = catalog_response.get('paging', {}).get('total', 0)
    warehouse_total = paging.get('total', 0)

    print(f"Catalog Products (On-Demand): {catalog_total}")
    print(f"Warehouse Products (Physical Inventory): {warehouse_total}")
    print()
    print("EXPLANATION:")
    print("  - Catalog products are print-on-demand items (POD)")
    print("    → Created when ordered, no physical inventory needed")
    print("  - Warehouse products are physical items in stock")
    print("    → Pre-existing inventory stored in Printful warehouses")
    print()
    if warehouse_total == 0:
        print("NOTE: No warehouse products means all fulfillment is print-on-demand.")

except PrintfulAPIError as e:
    print(f"❌ API Error: {e}")
    print()
    print("This might be because:")
    print("  1. No warehouse products exist")
    print("  2. Access token doesn't have warehouse permissions")
    print("  3. Need to specify a store_id")

except Exception as e:
    print(f"❌ Unexpected Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
