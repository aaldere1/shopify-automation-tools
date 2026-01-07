#!/usr/bin/env python3
"""
Estimate pallet requirements for Amplifier inventory
Based on actual item dimensions and on-hand quantities
"""

from amplifier_client import AmplifierClient
import math

AMPLIFIER_KEY = "YOUR_AMPLIFIER_API_KEY"
client = AmplifierClient(api_key=AMPLIFIER_KEY)

print("=" * 80)
print("AMPLIFIER PALLET REQUIREMENT ESTIMATION")
print("=" * 80)
print()

# Standard pallet specs
PALLET_LENGTH = 48  # inches
PALLET_WIDTH = 40   # inches
PALLET_HEIGHT_LIMIT = 60  # inches (typical warehouse max for stacking)
PALLET_FOOTPRINT = PALLET_LENGTH * PALLET_WIDTH  # 1,920 sq inches

print("STANDARD PALLET SPECIFICATIONS:")
print(f"  Dimensions: {PALLET_LENGTH}″ × {PALLET_WIDTH}″ × {PALLET_HEIGHT_LIMIT}″ (max height)")
print(f"  Footprint: {PALLET_FOOTPRINT:,} sq inches")
print()

# Fetch all items
print("Fetching Amplifier inventory...")
items = client.get_all_items()
print(f"✅ Loaded {len(items)} items\n")

print("=" * 80)
print("INVENTORY ANALYSIS")
print("=" * 80)
print()

total_items = 0
total_cubic_inches = 0
items_with_dimensions = 0

# Track by category
category_data = {}

for item in items:
    sku = item.get('sku', 'N/A')
    name = item.get('name', 'Unknown')
    inventory = item.get('inventory', {})
    on_hand = inventory.get('quantity_on_hand', 0)

    # Get dimensions
    length = item.get('length')
    width = item.get('width')
    height = item.get('height')
    weight = item.get('weight', 0)

    if on_hand > 0 and length and width and height:
        # Calculate volume per item
        volume_per_item = length * width * height  # cubic inches

        # Total volume for all units of this SKU
        total_volume = volume_per_item * on_hand

        total_items += on_hand
        total_cubic_inches += total_volume
        items_with_dimensions += 1

        # Determine category
        category = "Unknown"
        if 'shirt' in name.lower() or 't-shirt' in name.lower():
            category = "Apparel - T-Shirts"
        elif 'hoodie' in name.lower() or 'zip' in name.lower():
            category = "Apparel - Hoodies"
        elif 'scarf' in name.lower():
            category = "Accessories - Scarves"
        elif 'tie' in name.lower():
            category = "Accessories - Ties"
        elif 'program' in name.lower() or 'book' in name.lower():
            category = "Publications"
        elif 'wand' in name.lower():
            category = "Collectibles - Wands"
        elif 'cd' in name.lower() or 'soundtrack' in name.lower():
            category = "Media - CDs"
        elif 'tote' in name.lower() or 'bag' in name.lower():
            category = "Accessories - Bags"
        elif 'polar' in name.lower():
            category = "Polar Express Merch"
        else:
            category = "Other"

        if category not in category_data:
            category_data[category] = {
                'items': 0,
                'volume': 0,
                'count': 0,
                'weight': 0
            }

        category_data[category]['items'] += on_hand
        category_data[category]['volume'] += total_volume
        category_data[category]['count'] += 1
        category_data[category]['weight'] += (weight * on_hand)

print(f"Total Units in Warehouse: {total_items:,}")
print(f"Items with Dimension Data: {items_with_dimensions}/{len(items)}")
print(f"Total Cubic Volume: {total_cubic_inches:,.0f} cubic inches")
print()

# Convert to cubic feet for readability
total_cubic_feet = total_cubic_inches / 1728  # 1728 cubic inches = 1 cubic foot
print(f"Total Cubic Volume: {total_cubic_feet:,.1f} cubic feet")
print()

# Category breakdown
print("=" * 80)
print("INVENTORY BY CATEGORY")
print("=" * 80)
print()

for category in sorted(category_data.keys(), key=lambda x: category_data[x]['items'], reverse=True):
    data = category_data[category]
    pct = (data['items'] / total_items) * 100
    print(f"{category}:")
    print(f"  Units: {data['items']:,} ({pct:.1f}%)")
    print(f"  SKUs: {data['count']}")
    print(f"  Volume: {data['volume']/1728:.1f} cubic feet")
    print(f"  Weight: {data['weight']:.1f} oz ({data['weight']/16:.1f} lbs)")
    print()

# Pallet calculation methods
print("=" * 80)
print("PALLET ESTIMATION - METHOD 1: VOLUME-BASED")
print("=" * 80)
print()

# Calculate usable pallet volume
usable_pallet_volume = PALLET_FOOTPRINT * PALLET_HEIGHT_LIMIT  # cubic inches

# Apply efficiency factor (typically 60-70% for mixed SKUs, irregular shapes)
EFFICIENCY_FACTOR = 0.65  # 65% space utilization (conservative)

effective_volume_per_pallet = usable_pallet_volume * EFFICIENCY_FACTOR

print(f"Usable Volume per Pallet: {usable_pallet_volume:,} cubic inches")
print(f"Efficiency Factor: {EFFICIENCY_FACTOR*100:.0f}%")
print(f"Effective Volume per Pallet: {effective_volume_per_pallet:,.0f} cubic inches")
print()

pallets_needed_volume = math.ceil(total_cubic_inches / effective_volume_per_pallet)

print(f"📦 Pallets Required (Volume Method): {pallets_needed_volume} pallets")
print()

# Method 2: Category-based stacking
print("=" * 80)
print("PALLET ESTIMATION - METHOD 2: CATEGORY STACKING")
print("=" * 80)
print()

print("Practical stacking considerations:")
print()

# Estimate by category with realistic stacking
category_pallets = {}

# T-shirts: Can stack high, ~100-150 per pallet when boxed
tshirt_data = category_data.get("Apparel - T-Shirts", {})
if tshirt_data:
    tshirt_qty = tshirt_data['items']
    # Assume ~120 folded t-shirts per pallet (in boxes)
    category_pallets["T-Shirts"] = math.ceil(tshirt_qty / 120)
    print(f"T-Shirts: {tshirt_qty} units ÷ 120/pallet = {category_pallets['T-Shirts']} pallet(s)")

# Hoodies: Bulkier, ~50-70 per pallet
hoodie_data = category_data.get("Apparel - Hoodies", {})
if hoodie_data:
    hoodie_qty = hoodie_data['items']
    category_pallets["Hoodies"] = math.ceil(hoodie_qty / 60)
    print(f"Hoodies: {hoodie_qty} units ÷ 60/pallet = {category_pallets['Hoodies']} pallet(s)")

# Program Books: Flat, stackable, ~200-300 per pallet
pub_data = category_data.get("Publications", {})
if pub_data:
    pub_qty = pub_data['items']
    category_pallets["Program Books"] = math.ceil(pub_qty / 250)
    print(f"Program Books: {pub_qty} units ÷ 250/pallet = {category_pallets['Program Books']} pallet(s)")

# Scarves: Compact, ~200-300 per pallet
scarf_data = category_data.get("Accessories - Scarves", {})
if scarf_data:
    scarf_qty = scarf_data['items']
    category_pallets["Scarves"] = math.ceil(scarf_qty / 250)
    print(f"Scarves: {scarf_qty} units ÷ 250/pallet = {category_pallets['Scarves']} pallet(s)")

# Other accessories: Variable
other_items = 0
for cat in category_data:
    if cat not in ["Apparel - T-Shirts", "Apparel - Hoodies", "Publications", "Accessories - Scarves"]:
        other_items += category_data[cat]['items']

if other_items > 0:
    # Conservative estimate: ~100 mixed items per pallet
    category_pallets["Other/Mixed"] = math.ceil(other_items / 100)
    print(f"Other/Mixed: {other_items} units ÷ 100/pallet = {category_pallets['Other/Mixed']} pallet(s)")

print()
total_category_pallets = sum(category_pallets.values())
print(f"📦 Pallets Required (Category Method): {total_category_pallets} pallets")

# Method 3: Weight-based check
print()
print("=" * 80)
print("WEIGHT VERIFICATION")
print("=" * 80)
print()

total_weight_oz = sum(item.get('weight', 0) * item.get('inventory', {}).get('quantity_on_hand', 0)
                      for item in items)
total_weight_lbs = total_weight_oz / 16

print(f"Total Inventory Weight: {total_weight_lbs:,.1f} lbs ({total_weight_oz:,.0f} oz)")
print()

# Standard pallet weight limit: ~2,500 lbs (but varies)
PALLET_WEIGHT_LIMIT = 2500
pallets_by_weight = math.ceil(total_weight_lbs / PALLET_WEIGHT_LIMIT)

print(f"Standard Pallet Weight Limit: {PALLET_WEIGHT_LIMIT:,} lbs")
print(f"Weight-based Pallets: {pallets_by_weight} pallet(s)")
print()
print("Note: Weight is not the limiting factor here (volume is)")

# Final recommendation
print()
print("=" * 80)
print("FINAL RECOMMENDATION")
print("=" * 80)
print()

# Take the higher of the two methods for safety
recommended_pallets = max(pallets_needed_volume, total_category_pallets)

print(f"📦 RECOMMENDED PALLET COUNT: {recommended_pallets} pallets")
print()
print("Breakdown by method:")
print(f"  Volume-based calculation: {pallets_needed_volume} pallets")
print(f"  Category stacking method: {total_category_pallets} pallets")
print(f"  Weight check: {pallets_by_weight} pallet (not limiting)")
print()
print("ASSUMPTIONS:")
print("  • Standard 48″×40″ pallets")
print("  • 60″ maximum stacking height")
print("  • 65% space utilization efficiency (accounts for irregular shapes, boxing)")
print("  • Items stored in cartons/boxes as appropriate")
print("  • Some mixed SKU pallets for slow movers")
print()
print("PRACTICAL CONSIDERATIONS:")
print("  • Add 1-2 pallets for receiving/staging area")
print("  • Partial pallets may be combined for efficiency")
print("  • High-velocity items (top sellers) should be on separate pallets")
print("  • Consider rack storage for even better space utilization")
print()

# Calculate warehouse space
space_per_pallet = 8  # sq feet (48" × 40" = 13.3 sq ft, but need aisle space)
total_space = recommended_pallets * space_per_pallet

print(f"Estimated Warehouse Space: ~{total_space} sq feet")
print(f"  ({recommended_pallets} pallets × {space_per_pallet} sq ft per pallet position)")

print()
print("=" * 80)
