# API Integration Guide
**Three-System Integration: Shopify + Amplifier + Printful**

---

## Overview

This toolkit integrates three major systems:
1. **Shopify** - E-commerce platform (CineConcerts store)
2. **Amplifier** - Fulfillment & inventory management
3. **Printful** - Print-on-demand & fulfillment

---

## Quick Reference

### Credentials

**Shopify:**
- Store: `cineconcerts.myshopify.com`
- Token: `YOUR_SHOPIFY_TOKEN`

**Amplifier:**
- API Key: `YOUR_AMPLIFIER_API_KEY`
- Base URL: `https://api.amplifier.com`
- Auth: HTTP Basic (API key as username, Base64 encoded)

**Printful:**
- Access Token: `YOUR_PRINTFUL_TOKEN`
- Base URL: `https://api.printful.com`
- Auth: Bearer token

---

## Current Inventory Stats

| System | Items | Details |
|--------|-------|---------|
| **Shopify** | 847 SKUs | 108 products, 7.3M total inventory |
| **Amplifier** | 66 items | 14K total inventory on hand |
| **Printful** | 418 catalog + 46 warehouse | 4,087 orders, 3 stores |

---

## File Structure

```
shopify-data-extractor/
├── shopify_sku_scanner.py          # Scan Shopify for SKUs/inventory
├── shopify_order_fetcher.py        # Fetch Shopify orders
├── amplifier_client.py             # Amplifier API client
├── amplifier_api_documentation.md  # Amplifier API reference
├── printful_client.py              # Printful API client
├── test_amplifier_connection.py    # Test Amplifier API
├── test_printful_connection.py     # Test Printful API
├── test_printful_warehouse.py      # Test Printful warehouse inventory
└── openapi_split/                  # Printful API specs
```

---

## Usage Examples

### Shopify Queries

```bash
# Get all SKUs and inventory
python3 shopify_sku_scanner.py \
  --store cineconcerts.myshopify.com \
  --token YOUR_SHOPIFY_TOKEN

# Export to CSV
python3 shopify_sku_scanner.py \
  --store cineconcerts.myshopify.com \
  --token YOUR_SHOPIFY_TOKEN \
  --output inventory.csv

# Fetch orders from specific date
python3 shopify_order_fetcher.py \
  --store cineconcerts.myshopify.com \
  --token YOUR_SHOPIFY_TOKEN \
  --from-date 2025-01-01
```

### Amplifier Queries

```python
from amplifier_client import AmplifierClient

# Initialize
client = AmplifierClient(api_key="YOUR_AMPLIFIER_API_KEY")

# Get all items
all_items = client.get_all_items()
print(f"Total items: {len(all_items)}")

# Search by SKU
items = client.get_items(sku="11013")

# Search by name
items = client.get_items(name="Scarf")

# Get specific item details
for item in all_items:
    print(f"SKU: {item['sku']}")
    print(f"Name: {item['name']}")
    print(f"Available: {item['inventory']['quantity_available']}")
    print(f"On Hand: {item['inventory']['quantity_on_hand']}")
```

### Printful Queries

```python
from printful_client import PrintfulClient

# Initialize
client = PrintfulClient(access_token="YOUR_PRINTFUL_TOKEN")

# Get stores
stores = client.get_stores()
for store in stores.get('data', []):
    print(f"Store: {store['name']} (ID: {store['id']})")

# Get catalog products (print-on-demand)
products_response = client.get_products(limit=10)
products = products_response.get('data', [])

# Get warehouse products (physical inventory)
warehouse_response = client.get_warehouse_products(store_id=7266986, limit=100)
warehouse_products = warehouse_response.get('data', [])

# Get all products (pagination handled automatically)
all_products = client.get_all_products()

# Get orders for a specific store
orders = client.get_orders(store_id=7266986, limit=10)

# Get all orders
all_orders = client.get_all_orders(store_id=7266986)

# Get specific product details
product = client.get_product(product_id=1)

# Get categories
categories = client.get_categories()
```

---

## Common Workflows

### 1. SKU Comparison Across Systems

```python
from amplifier_client import AmplifierClient
from printful_client import PrintfulClient
import requests

# Shopify SKUs
shopify_url = "https://cineconcerts.myshopify.com/admin/api/2025-10/products.json"
shopify_headers = {'X-Shopify-Access-Token': 'YOUR_SHOPIFY_TOKEN'}
response = requests.get(shopify_url, headers=shopify_headers, params={'limit': 250})
shopify_skus = set()
for product in response.json()['products']:
    for variant in product['variants']:
        if variant.get('sku'):
            shopify_skus.add(variant['sku'])

# Amplifier SKUs
amplifier = AmplifierClient(api_key="YOUR_AMPLIFIER_API_KEY")
amplifier_items = amplifier.get_all_items()
amplifier_skus = {item['sku'] for item in amplifier_items if item.get('sku')}

# Printful - no direct SKU mapping
printful = PrintfulClient(access_token="YOUR_PRINTFUL_TOKEN")
printful_products = printful.get_all_products()

# Compare
print(f"Shopify SKUs: {len(shopify_skus)}")
print(f"Amplifier SKUs: {len(amplifier_skus)}")
print(f"Printful Products: {len(printful_products)}")
print(f"Common (Shopify ∩ Amplifier): {len(shopify_skus & amplifier_skus)}")
```

### 2. Inventory Check

```python
from amplifier_client import AmplifierClient

client = AmplifierClient(api_key="YOUR_AMPLIFIER_API_KEY")

# Check specific SKU
sku_to_check = "11013"
items = client.get_items(sku=sku_to_check)

if items.get('data'):
    item = items['data'][0]
    inventory = item['inventory']
    print(f"SKU: {sku_to_check}")
    print(f"Available: {inventory['quantity_available']}")
    print(f"On Hand: {inventory['quantity_on_hand']}")
    print(f"Committed: {inventory['quantity_committed']}")
```

### 3. Order Summary

```python
from printful_client import PrintfulClient

client = PrintfulClient(access_token="YOUR_PRINTFUL_TOKEN")

# Get orders for CineConcerts store
store_id = 7266986
orders = client.get_orders(store_id=store_id, limit=100)

# Analyze order statuses
statuses = {}
for order in orders.get('data', []):
    status = order.get('status', 'unknown')
    statuses[status] = statuses.get(status, 0) + 1

print("Order Status Summary:")
for status, count in statuses.items():
    print(f"  {status}: {count}")
```

### 4. Printful: Catalog vs Warehouse Products

**Important:** Printful separates products into two types:

```python
from printful_client import PrintfulClient

client = PrintfulClient(access_token="YOUR_PRINTFUL_TOKEN")

# CATALOG PRODUCTS (Print-on-Demand)
# These are created when ordered - no inventory needed
catalog_response = client.get_products(limit=100)
catalog_products = catalog_response.get('data', [])
catalog_total = catalog_response.get('paging', {}).get('total', 0)
print(f"Catalog Products (POD): {catalog_total}")

# WAREHOUSE PRODUCTS (Physical Inventory)
# These are pre-existing items stored in Printful warehouses
warehouse_response = client.get_warehouse_products(store_id=7266986, limit=100)
warehouse_products = warehouse_response.get('data', [])
warehouse_total = warehouse_response.get('paging', {}).get('total', 0)
print(f"Warehouse Products: {warehouse_total}")

# Check warehouse inventory levels
for product in warehouse_products:
    quantity = product.get('quantity', 0)
    print(f"Warehouse Product {product['id']}: {quantity} units")
```

**Key Differences:**
- **Catalog Products**: No physical inventory, created on-demand when ordered
- **Warehouse Products**: Physical items in stock, tracked with quantities
- **Note**: `store_id` is required for warehouse products endpoint

---

## API Endpoints Reference

### Shopify

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/api/2025-10/products.json` | GET | List products |
| `/admin/api/2025-10/orders.json` | GET | List orders |
| `/admin/api/2025-10/inventory_levels.json` | GET | Get inventory |

### Amplifier

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/items/` | GET | List/search items |
| `/items/{id}` | GET | Get item details |
| `/orders` | GET | List orders |
| `/orders` | POST | Create order |
| `/reports/inventory/current` | GET | Current inventory report |

### Printful

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v2/stores` | GET | List stores |
| `/v2/catalog-products` | GET | List catalog products (POD) |
| `/v2/catalog-products/{id}` | GET | Get product details |
| `/v2/warehouse-products` | GET | List warehouse products (physical inventory) |
| `/v2/warehouse-products/{id}` | GET | Get warehouse product details |
| `/v2/orders` | GET | List orders |
| `/v2/orders` | POST | Create order |
| `/v2/catalog-categories` | GET | List categories |

---

## Error Handling

All clients include built-in error handling:

```python
from amplifier_client import AmplifierClient, AmplifierAPIError
from printful_client import PrintfulClient, PrintfulAPIError

try:
    amplifier = AmplifierClient(api_key="your-key")
    items = amplifier.get_all_items()
except AmplifierAPIError as e:
    print(f"Amplifier error: {e}")

try:
    printful = PrintfulClient(access_token="your-token")
    products = printful.get_all_products()
except PrintfulAPIError as e:
    print(f"Printful error: {e}")
```

---

## Rate Limits

| System | Rate Limit | Handling |
|--------|------------|----------|
| **Shopify** | 2 req/sec | Built into scripts (automatic pagination) |
| **Amplifier** | 120 req/min | Automatic retry with exponential backoff |
| **Printful** | Not specified | 0.5s delay between bulk requests |

---

## Testing

Test each API connection:

```bash
# Test Amplifier
python3 test_amplifier_connection.py

# Test Printful (catalog products)
python3 test_printful_connection.py

# Test Printful warehouse inventory
python3 test_printful_warehouse.py

# Test Shopify (via scanner)
python3 shopify_sku_scanner.py --store cineconcerts.myshopify.com \
  --token YOUR_SHOPIFY_TOKEN --summary-only
```

---

## Troubleshooting

**"401 Unauthorized"**
- Verify API keys/tokens are correct
- Check token hasn't expired
- Ensure proper authentication format

**"429 Too Many Requests"**
- Reduce request frequency
- Scripts automatically handle this with retries

**Empty results**
- Check store_id parameters for Printful
- Verify status filters for orders
- Ensure products are active/not discontinued

---

## System Integration Map

```
┌─────────────┐
│   Shopify   │  ← E-commerce Store
│  847 SKUs   │  ← Customer orders
└──────┬──────┘
       │
       ├──────────────┐
       │              │
┌──────▼──────┐  ┌───▼────────┐
│  Amplifier  │  │  Printful  │
│  66 items   │  │ 418 items  │
│ (Physical)  │  │   (POD)    │
└─────────────┘  └────────────┘
```

**Flow:**
1. Customer places order on **Shopify**
2. Order routed to **Amplifier** (physical inventory) or **Printful** (print-on-demand)
3. Both systems fulfill and ship
4. Inventory syncs back to **Shopify**

---

## Next Steps

1. **Set up webhooks** for real-time order notifications
2. **Automate inventory sync** between systems
3. **Create order routing logic** (Amplifier vs Printful)
4. **Build reporting dashboard** for cross-system analytics

---

*Last Updated: 2025-11-14*
*All three APIs tested and operational*
*Printful: Both catalog (POD) and warehouse inventory endpoints verified*
