#!/usr/bin/env python3
"""
Test Printful API connection
"""

from printful_client import PrintfulClient, PrintfulAPIError
import json

# Initialize client with your access token
ACCESS_TOKEN = "YOUR_PRINTFUL_TOKEN"
client = PrintfulClient(access_token=ACCESS_TOKEN)

print("=" * 70)
print("PRINTFUL API CONNECTION TEST")
print("=" * 70)
print()

try:
    # Test 1: Get stores
    print("Test 1: Fetching stores...")
    stores_response = client.get_stores()
    stores = stores_response.get('data', [])

    print(f"✅ Success! Found {len(stores)} store(s)")
    for store in stores:
        print(f"   Store ID: {store.get('id')}")
        print(f"   Name: {store.get('name')}")
        print(f"   Type: {store.get('type')}")
        print()

    # Test 2: Get catalog products
    print("Test 2: Fetching catalog products (first 10)...")
    products_response = client.get_products(limit=10)
    products = products_response.get('data', [])
    paging = products_response.get('paging', {})

    print(f"✅ Success!")
    print(f"   Products in this page: {len(products)}")
    print(f"   Total products: {paging.get('total', 0)}")
    print(f"   Limit: {paging.get('limit', 0)}")
    print(f"   Offset: {paging.get('offset', 0)}")
    print()

    if products:
        print("Sample Product (first one):")
        product = products[0]
        print(f"   ID: {product.get('id')}")
        print(f"   Name: {product.get('name')}")
        print(f"   Brand: {product.get('brand')}")
        print(f"   Model: {product.get('model')}")
        print(f"   Description: {product.get('description', '')[:100]}...")
        print()

    # Test 3: Get categories
    print("Test 3: Fetching catalog categories...")
    categories_response = client.get_categories()
    categories = categories_response.get('data', [])

    print(f"✅ Found {len(categories)} categories")
    for cat in categories[:5]:
        print(f"   - {cat.get('title')} (ID: {cat.get('id')})")
    print()

    # Test 4: Get orders
    print("Test 4: Fetching orders...")
    try:
        orders_response = client.get_orders(limit=5)
        orders = orders_response.get('data', [])
        paging = orders_response.get('paging', {})

        print(f"✅ Success!")
        print(f"   Orders in this page: {len(orders)}")
        print(f"   Total orders: {paging.get('total', 0)}")
        print()

        if orders:
            print("Sample Order (first one):")
            order = orders[0]
            print(f"   ID: {order.get('id')}")
            print(f"   Status: {order.get('status')}")
            print(f"   Created: {order.get('created_at')}")
            print()
    except PrintfulAPIError as e:
        print(f"   ℹ️  No orders found or access restricted: {e}")
        print()

    # Test 5: Get countries
    print("Test 5: Fetching countries...")
    countries_response = client.get_countries()
    countries = countries_response.get('data', [])

    print(f"✅ Found {len(countries)} countries")
    print(f"   Sample: {', '.join([c.get('name') for c in countries[:5]])}")
    print()

    print("=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print()
    print("Printful API Summary:")
    print(f"   Stores: {len(stores)}")
    print(f"   Total Products: {paging.get('total', 0)}")
    print(f"   Categories: {len(categories)}")
    print(f"   Countries: {len(countries)}")
    print("=" * 70)

except PrintfulAPIError as e:
    print(f"❌ API Error: {e}")
    print()
    print("This might be because:")
    print("  1. The access token is invalid or expired")
    print("  2. The API endpoint structure has changed")
    print("  3. Network connectivity issues")
    print("  4. Insufficient permissions for the token")

except Exception as e:
    print(f"❌ Unexpected Error: {e}")
    import traceback
    traceback.print_exc()
