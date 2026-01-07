# Amplifier API Integration

This directory contains tools for integrating Amplifier and Shopify APIs.

## Files

### Documentation
- **amplifier_api_documentation.md** - Complete API reference for Amplifier
  - All endpoints, parameters, and response formats
  - Authentication methods
  - Best practices and rate limiting info

### Scripts

#### amplifier_client.py
Python client library for the Amplifier API.

**Features:**
- Complete CRUD operations for products, orders, inventory, customers
- Automatic rate limiting and retry logic
- Bulk operations (fetch all products/orders across pages)
- Error handling with custom exceptions

**Usage:**
```python
from amplifier_client import AmplifierClient

client = AmplifierClient(api_key="your-api-key")

# Get all products
products = client.get_all_products()

# Get specific product
product = client.get_product("product_id")

# Create product
new_product = client.create_product({
    "name": "Product Name",
    "sku": "SKU123",
    "price": 29.99
})

# Update inventory
client.update_inventory("product_id", quantity=100)
```

#### amplifier_shopify_integration.py
Integration tool that syncs data between Shopify and Amplifier.

**Features:**
- Sync products from Shopify → Amplifier
- Sync inventory from Amplifier → Shopify
- Sync orders from Shopify → Amplifier
- Generate sync reports

**Usage:**
```bash
# Sync products from Shopify to Amplifier
python3 amplifier_shopify_integration.py --action sync-products

# Sync inventory
python3 amplifier_shopify_integration.py --action sync-inventory

# Sync orders from specific date
python3 amplifier_shopify_integration.py --action sync-orders --from-date 2025-01-01

# Generate comparison report
python3 amplifier_shopify_integration.py --action report
```

#### shopify_sku_scanner.py
Scan Shopify for unique SKUs.

**Usage:**
```bash
# Get SKU summary
python3 shopify_sku_scanner.py --store cineconcerts.myshopify.com --token shpat_xxx

# Export to CSV
python3 shopify_sku_scanner.py --store cineconcerts.myshopify.com --token shpat_xxx --output skus.csv
```

## Credentials

**Shopify:**
- Store: `cineconcerts.myshopify.com`
- Token: `YOUR_SHOPIFY_TOKEN`

**Amplifier:**
- API Key: `YOUR_AMPLIFIER_API_KEY`
- Base URL: `https://api.amplifier.com`
- Docs: https://amplifier.docs.apiary.io/

### Retrieve from 1Password (CineConcerts Team)

API credentials are stored securely in 1Password:

| Field | Description |
|-------|-------------|
| **Account** | `alderete-family.1password.com` |
| **Vault** | Private |
| **Item** | "CineConcerts - API Keys" |

```bash
# View all credentials
op item get "CineConcerts - API Keys" \
  --vault="Private" \
  --account="alderete-family.1password.com" \
  --reveal

# Export to .env.local
op item get "CineConcerts - API Keys" \
  --vault="Private" \
  --account="alderete-family.1password.com" \
  --format=json | \
  jq -r '.fields[] | select(.value != null and .label != "notesPlain" and .id != "validFrom" and .id != "expires") | "\(.label)=\"\(.value)\""' > .env.local
```

**Available credentials:** `SHOPIFY_STORE`, `SHOPIFY_TOKEN`, `AMPLIFIER_API_KEY`, `PRINTFUL_TOKEN`

## Common Workflows

### 1. Product Sync Workflow

```bash
# Step 1: Check current state
python3 amplifier_shopify_integration.py --action report

# Step 2: Sync products from Shopify to Amplifier
python3 amplifier_shopify_integration.py --action sync-products

# Step 3: Verify sync
python3 amplifier_shopify_integration.py --action report
```

### 2. SKU Analysis Workflow

```bash
# Step 1: Get Shopify SKUs
python3 shopify_sku_scanner.py --store cineconcerts.myshopify.com \\
  --token YOUR_SHOPIFY_TOKEN \\
  --output shopify_skus.csv

# Step 2: Use amplifier_client to fetch Amplifier SKUs
python3 -c "from amplifier_client import AmplifierClient; \\
  c = AmplifierClient('YOUR_AMPLIFIER_API_KEY'); \\
  print(len(c.get_all_products()))"

# Step 3: Compare with integration report
python3 amplifier_shopify_integration.py --action report
```

### 3. Order Sync Workflow

```bash
# Sync last 30 days of orders
python3 amplifier_shopify_integration.py --action sync-orders \\
  --from-date $(date -v-30d +%Y-%m-%d)

# Sync specific date range
python3 amplifier_shopify_integration.py --action sync-orders \\
  --from-date 2025-01-01
```

## API Rate Limits

**Shopify:**
- 2 requests per second (handled by existing scripts)
- Automatic pagination with Link headers

**Amplifier:**
- 120 requests per minute
- Automatically handled by amplifier_client with retry logic
- Rate limit headers: X-RateLimit-Limit, X-RateLimit-Remaining

## Error Handling

All scripts include comprehensive error handling:

- **Network errors:** Automatic retry with exponential backoff
- **Rate limiting:** Automatic wait and retry
- **Authentication errors:** Clear error messages
- **Data validation:** Validates before API calls

## Extending the Integration

### Add a new Amplifier endpoint

1. Add method to `amplifier_client.py`:
```python
def new_method(self, param):
    return self._request('GET', '/new-endpoint', params={'param': param})
```

2. Use in integration script:
```python
result = self.amplifier.new_method(param_value)
```

### Add a new sync direction

Add method to `ShopifyAmplifierIntegration` class in `amplifier_shopify_integration.py`:

```python
def sync_new_data(self):
    # Fetch from source
    data = self.fetch_shopify_new_data()

    # Transform
    transformed = self.transform_data(data)

    # Push to destination
    self.amplifier.create_new_data(transformed)
```

## Troubleshooting

**"401 Unauthorized"**
- Check API keys are correct
- Verify tokens haven't expired
- Ensure proper header format

**"429 Too Many Requests"**
- Scripts automatically handle this
- If persistent, increase delays in code

**"No products found"**
- Verify store has active products
- Check status filters in API calls

**Sync mismatches**
- Run `--action report` to see discrepancies
- Check SKU mappings between systems
- Verify product creation succeeded

## Dependencies

```bash
pip3 install requests
```

All scripts use only standard library + requests for minimal dependencies.

## Security Notes

- API keys are hardcoded for convenience but should be moved to environment variables in production
- Never commit .env files with real credentials
- Use HTTPS for all webhook URLs
- Rotate API keys periodically

---

*Created: 2025-11-14*
*Integration between Shopify (CineConcerts) and Amplifier*
