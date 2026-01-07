#!/usr/bin/env python3
"""
Test Amplifier API connection and fetch items
"""

from amplifier_client import AmplifierClient, AmplifierAPIError
import json

# Initialize client with your API key
API_KEY = "YOUR_AMPLIFIER_API_KEY"
client = AmplifierClient(api_key=API_KEY)

print("=" * 70)
print("AMPLIFIER API CONNECTION TEST")
print("=" * 70)
print()

try:
    # Test 1: Get first page of items
    print("Test 1: Fetching first page of items...")
    response = client.get_items(per_page=10)

    print(f"✅ Success!")
    print(f"   Page: {response.get('page')}")
    print(f"   Per Page: {response.get('per_page')}")
    print(f"   Total Items: {response.get('total')}")
    print(f"   Total Pages: {response.get('total_pages')}")
    print()

    # Show first item
    items = response.get('data', [])
    if items:
        print(f"Sample Item (first of {len(items)}):")
        item = items[0]
        print(f"   ID: {item.get('id')}")
        print(f"   SKU: {item.get('sku')}")
        print(f"   Name: {item.get('name')}")
        print(f"   Category: {item.get('category')}")
        print(f"   Cost: ${item.get('cost')}")
        print(f"   Retail Price: ${item.get('retail_price')}")
        print(f"   Status: {item.get('status')}")
        print(f"   Inventory Available: {item.get('inventory', {}).get('quantity_available')}")
        print(f"   Inventory On Hand: {item.get('inventory', {}).get('quantity_on_hand')}")
        print()

    # Test 2: Search by query
    print("Test 2: Searching for items...")
    search_response = client.get_items(query="", per_page=5)
    search_items = search_response.get('data', [])
    print(f"✅ Found {len(search_items)} items in search")
    print()

    # Test 3: Get all items
    print("Test 3: Fetching ALL items (this may take a moment)...")
    all_items = client.get_all_items()
    print(f"✅ Total items in Amplifier: {len(all_items)}")
    print()

    # Extract unique SKUs
    skus = {item.get('sku') for item in all_items if item.get('sku')}
    print(f"Unique SKUs: {len(skus)}")
    print()

    # Category breakdown
    categories = {}
    for item in all_items:
        cat = item.get('category', 'Uncategorized')
        categories[cat] = categories.get(cat, 0) + 1

    print("Items by Category:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"   {cat}: {count}")
    print()

    # Inventory summary
    total_available = sum(item.get('inventory', {}).get('quantity_available', 0) for item in all_items)
    total_on_hand = sum(item.get('inventory', {}).get('quantity_on_hand', 0) for item in all_items)
    total_committed = sum(item.get('inventory', {}).get('quantity_committed', 0) for item in all_items)

    print("Inventory Summary:")
    print(f"   Total Available: {total_available:,}")
    print(f"   Total On Hand: {total_on_hand:,}")
    print(f"   Total Committed: {total_committed:,}")
    print()

    print("=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)

except AmplifierAPIError as e:
    print(f"❌ API Error: {e}")
    print()
    print("This might be because:")
    print("  1. The API key is invalid or expired")
    print("  2. The API endpoint structure is different")
    print("  3. Network connectivity issues")

except Exception as e:
    print(f"❌ Unexpected Error: {e}")
    import traceback
    traceback.print_exc()
