#!/usr/bin/env python3
"""
Analyze SKU dimensions and weights from Printful and Amplifier
"""

from printful_client import PrintfulClient, PrintfulAPIError
from amplifier_client import AmplifierClient, AmplifierAPIError
import statistics

# Initialize clients
PRINTFUL_TOKEN = "YOUR_PRINTFUL_TOKEN"
AMPLIFIER_KEY = "YOUR_AMPLIFIER_API_KEY"

printful = PrintfulClient(access_token=PRINTFUL_TOKEN)
amplifier = AmplifierClient(api_key=AMPLIFIER_KEY)

print("=" * 80)
print("SKU DIMENSION & WEIGHT ANALYSIS")
print("=" * 80)
print()

# ==================== PRINTFUL ANALYSIS ====================
print("PRINTFUL CATALOG PRODUCTS")
print("-" * 80)

try:
    # Get sample of catalog products
    products_response = printful.get_products(limit=50)
    products = products_response.get('data', [])

    print(f"Analyzing {len(products)} products...")
    print()

    # Examine first few products in detail
    for idx, product in enumerate(products[:5], 1):
        print(f"{idx}. {product.get('name', 'Unknown')}")
        print(f"   ID: {product.get('id')}")

        # Check for dimension/weight fields
        if 'dimensions' in product:
            print(f"   Dimensions: {product['dimensions']}")
        if 'weight' in product:
            print(f"   Weight: {product['weight']}")
        if 'size' in product:
            print(f"   Size: {product['size']}")

        # Show all available keys
        print(f"   Available fields: {', '.join(product.keys())}")
        print()

    # Get detailed variant information
    print("\nChecking product variants for dimension data...")
    print("-" * 80)

    variant_weights = []
    variant_dims = []

    # Check first 10 products for variant details
    for product in products[:10]:
        product_id = product.get('id')
        try:
            variants_response = printful.get_product_variants(product_id)
            variants = variants_response.get('data', [])

            for variant in variants[:3]:  # Check first 3 variants per product
                print(f"\nVariant: {variant.get('name', 'Unknown')}")
                print(f"  ID: {variant.get('id')}")

                # Check for dimension/weight data
                if 'dimensions' in variant:
                    dims = variant['dimensions']
                    print(f"  Dimensions: {dims}")
                    variant_dims.append(dims)

                if 'weight' in variant:
                    weight = variant['weight']
                    print(f"  Weight: {weight}")
                    variant_weights.append(weight)

                # Check all available fields
                print(f"  Fields: {', '.join(variant.keys())}")

        except Exception as e:
            print(f"  Could not get variants: {e}")
            continue

    print()
    print("=" * 80)

except PrintfulAPIError as e:
    print(f"❌ Printful Error: {e}")

# ==================== AMPLIFIER ANALYSIS ====================
print("\nAMPLIFIER ITEMS")
print("-" * 80)

try:
    items = amplifier.get_all_items()

    print(f"Analyzing {len(items)} items...")
    print()

    weights = []
    dimensions = []

    # Examine all items for dimension data
    for idx, item in enumerate(items[:10], 1):  # Show first 10 in detail
        print(f"{idx}. {item.get('name', 'Unknown')}")
        print(f"   SKU: {item.get('sku')}")

        # Check for weight
        if 'weight' in item:
            weight = item['weight']
            print(f"   Weight: {weight}")
            if weight:
                weights.append(weight)

        # Check for dimensions
        if 'dimensions' in item:
            dims = item['dimensions']
            print(f"   Dimensions: {dims}")
            if dims:
                dimensions.append(dims)

        if 'length' in item or 'width' in item or 'height' in item:
            l = item.get('length', 'N/A')
            w = item.get('width', 'N/A')
            h = item.get('height', 'N/A')
            print(f"   L×W×H: {l} × {w} × {h}")

        # Show available fields
        print(f"   Available fields: {', '.join(item.keys())}")
        print()

    # Calculate statistics if we have data
    print("=" * 80)
    print("AMPLIFIER SUMMARY")
    print("-" * 80)

    if weights:
        print(f"Weights found: {len(weights)}")
        print(f"  Average: {statistics.mean(weights):.2f}")
        print(f"  Median: {statistics.median(weights):.2f}")
        print(f"  Range: {min(weights):.2f} - {max(weights):.2f}")
    else:
        print("No weight data found in Amplifier")

    if dimensions:
        print(f"\nDimensions found: {len(dimensions)}")
        print(f"  Data: {dimensions[:5]}")
    else:
        print("\nNo dimension data found in Amplifier")

except AmplifierAPIError as e:
    print(f"❌ Amplifier Error: {e}")

print()
print("=" * 80)
