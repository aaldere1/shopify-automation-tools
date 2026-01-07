#!/usr/bin/env python3
"""
Get typical SKU dimensions and weights from Printful and Amplifier
Focus on getting actual measurable data
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
print("TYPICAL SKU DIMENSIONS & WEIGHT ANALYSIS")
print("=" * 80)
print()

# ==================== AMPLIFIER ANALYSIS (More likely to have this data) ====================
print("CHECKING AMPLIFIER ITEMS FOR DIMENSION DATA")
print("-" * 80)

try:
    items = amplifier.get_all_items()
    print(f"Analyzing {len(items)} items...")
    print()

    # Look at first item in detail to see structure
    if items:
        sample_item = items[0]
        print("Sample item structure:")
        print(f"SKU: {sample_item.get('sku')}")
        print(f"Name: {sample_item.get('name')}")
        print("All fields:")
        for key, value in sample_item.items():
            print(f"  {key}: {value}")
        print()

    weights_lb = []
    weights_oz = []
    lengths = []
    widths = []
    heights = []

    print("-" * 80)
    print("Scanning all items for dimension/weight data...")
    print()

    for item in items:
        sku = item.get('sku', 'N/A')
        name = item.get('name', 'Unknown')

        # Check various possible weight fields
        weight = None
        if 'weight' in item and item['weight']:
            weight = item['weight']
        elif 'weight_oz' in item and item['weight_oz']:
            weights_oz.append(float(item['weight_oz']))
            weight = f"{item['weight_oz']} oz"
        elif 'weight_lb' in item and item['weight_lb']:
            weights_lb.append(float(item['weight_lb']))
            weight = f"{item['weight_lb']} lb"

        # Check for dimension fields
        length = item.get('length') or item.get('length_in')
        width = item.get('width') or item.get('width_in')
        height = item.get('height') or item.get('height_in')

        if length:
            try:
                lengths.append(float(length))
            except (ValueError, TypeError):
                pass

        if width:
            try:
                widths.append(float(width))
            except (ValueError, TypeError):
                pass

        if height:
            try:
                heights.append(float(height))
            except (ValueError, TypeError):
                pass

        # Show items that have dimension data
        if weight or length or width or height:
            print(f"SKU {sku}: {name}")
            if weight:
                print(f"  Weight: {weight}")
            if length or width or height:
                print(f"  Dimensions: {length or '?'} × {width or '?'} × {height or '?'} inches")

    print()
    print("=" * 80)
    print("AMPLIFIER STATISTICS")
    print("=" * 80)

    if weights_lb:
        print(f"\nWeights (lbs): {len(weights_lb)} items")
        print(f"  Average: {statistics.mean(weights_lb):.2f} lbs")
        print(f"  Median: {statistics.median(weights_lb):.2f} lbs")
        print(f"  Range: {min(weights_lb):.2f} - {max(weights_lb):.2f} lbs")

    if weights_oz:
        print(f"\nWeights (oz): {len(weights_oz)} items")
        print(f"  Average: {statistics.mean(weights_oz):.2f} oz ({statistics.mean(weights_oz)/16:.2f} lbs)")
        print(f"  Median: {statistics.median(weights_oz):.2f} oz ({statistics.median(weights_oz)/16:.2f} lbs)")
        print(f"  Range: {min(weights_oz):.2f} - {max(weights_oz):.2f} oz")

    if lengths and widths and heights:
        print(f"\nDimensions: {len(lengths)} items with full data")
        print(f"  Average: {statistics.mean(lengths):.1f} × {statistics.mean(widths):.1f} × {statistics.mean(heights):.1f} inches")
        print(f"  Median: {statistics.median(lengths):.1f} × {statistics.median(widths):.1f} × {statistics.median(heights):.1f} inches")

    if not (weights_lb or weights_oz or lengths):
        print("\n⚠️  No dimension or weight data found in Amplifier items")

except AmplifierAPIError as e:
    print(f"❌ Amplifier Error: {e}")

# ==================== PRINTFUL ANALYSIS ====================
print("\n" + "=" * 80)
print("CHECKING PRINTFUL WAREHOUSE PRODUCTS")
print("-" * 80)

try:
    # Check warehouse products (more likely to have physical dimensions)
    warehouse_response = printful.get_warehouse_products(store_id=7266986, limit=100)
    warehouse_products = warehouse_response.get('data', [])

    print(f"Analyzing {len(warehouse_products)} warehouse products...")
    print()

    if warehouse_products:
        sample = warehouse_products[0]
        print("Sample warehouse product structure:")
        for key, value in sample.items():
            if key != 'files':  # Skip files array for readability
                print(f"  {key}: {value}")
        print()

    print("Note: Warehouse products may not have standardized dimension data")
    print("Printful catalog products are sized by variant (e.g., 'S', 'M', 'L', '11oz', etc.)")

except PrintfulAPIError as e:
    print(f"❌ Printful Error: {e}")

print()
print("=" * 80)
print("RECOMMENDATION FOR FORM")
print("=" * 80)
print()

# Provide a recommendation based on what we found
if weights_lb or weights_oz or lengths:
    print("Based on available data from Amplifier inventory:")
    print()
    if weights_lb:
        avg_weight = statistics.mean(weights_lb)
        print(f"  Typical Weight: {avg_weight:.1f} lbs ({avg_weight*16:.0f} oz)")
    elif weights_oz:
        avg_weight_oz = statistics.mean(weights_oz)
        print(f"  Typical Weight: {avg_weight_oz:.0f} oz ({avg_weight_oz/16:.1f} lbs)")

    if lengths and widths and heights:
        print(f"  Typical Dimensions: {statistics.mean(lengths):.0f}″ × {statistics.mean(widths):.0f}″ × {statistics.mean(heights):.0f}″ (L×W×H)")
    else:
        print("  Typical Dimensions: Varies by product (see Amplifier data above)")
else:
    print("Dimension data not readily available in APIs.")
    print()
    print("For CineConcerts merchandise (typical concert merch):")
    print("  Apparel (T-shirts, hoodies): 8-12 oz, 12″×8″×1″ (folded)")
    print("  Posters: 2-4 oz, 24″×18″×0.5″ (rolled)")
    print("  Accessories (mugs, etc.): 10-16 oz, 6″×4″×4″")

print()
print("=" * 80)
