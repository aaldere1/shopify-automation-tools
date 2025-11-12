# Shopify Admin Automation Tools

A collection of Python scripts for automating Shopify Admin API operations, including order fetching, filtering, and batch refund processing.

## 🚀 Features

### Order Fetcher (`shopify_order_fetcher.py`)
- Fetch orders with flexible filters
- Filter by price, date range, status, tags, and more
- Export to CSV or JSON
- Pagination handling (unlimited orders)
- Comprehensive summary statistics

### Batch Refund Processor (`shopify_batch_refund.py`)
- Process refunds for multiple orders from CSV
- Full or partial refunds
- Dry-run mode for testing
- Automatic rate limiting
- Customer notification options
- Inventory restocking support

## 📋 Requirements

- Python 3.7+
- `requests` library

```bash
pip install requests
```

## 🔑 Setup

### 1. Create Shopify Custom App

1. Log into your Shopify Admin
2. Go to **Settings** → **Apps and sales channels** → **Develop apps**
3. Click **Create an app**
4. Configure Admin API scopes:
   - `read_orders` - Required for fetching orders
   - `write_orders` - Required for processing refunds
5. Install the app and copy the **Admin API access token**

### 2. Store Configuration

You can either:
- Pass credentials via command-line arguments
- Use environment variables (recommended for security)

```bash
export SHOPIFY_STORE="your-store.myshopify.com"
export SHOPIFY_TOKEN="shpat_xxxxx"
```

## 📖 Usage

### Order Fetcher

#### Fetch all $0.99 orders
```bash
python3 shopify_order_fetcher.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --price 0.99
```

#### Fetch orders in a price range
```bash
python3 shopify_order_fetcher.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --min-price 10 \
  --max-price 50
```

#### Fetch unfulfilled orders with specific tag
```bash
python3 shopify_order_fetcher.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --fulfillment-status unfulfilled \
  --tag WHOLESALE
```

#### Fetch orders from specific date
```bash
python3 shopify_order_fetcher.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --from-date 2025-01-01 \
  --to-date 2025-01-31
```

#### Fetch from specific order number onwards
```bash
python3 shopify_order_fetcher.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --from-order "#5377" \
  --price 0.99
```

#### Export to JSON instead of CSV
```bash
python3 shopify_order_fetcher.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --price 0.99 \
  --format json
```

### Batch Refund Processor

#### Full refunds (basic)
```bash
python3 shopify_batch_refund.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --input orders.csv
```

#### Auto-approve without confirmation
```bash
python3 shopify_batch_refund.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --input orders.csv \
  --yes
```

#### Dry run (preview only)
```bash
python3 shopify_batch_refund.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --input orders.csv \
  --dry-run
```

#### Partial refunds
```bash
python3 shopify_batch_refund.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --input orders.csv \
  --amount 10.00
```

#### With customer notifications
```bash
python3 shopify_batch_refund.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --input orders.csv \
  --notify
```

#### Restock inventory
```bash
python3 shopify_batch_refund.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --input orders.csv \
  --restock
```

## 📁 CSV Format

The refund script accepts CSV files with order numbers in any of these column names:
- `Order Number` or `order_number`
- `Order Name` or `order_name`
- `order`
- `name`
- `number`

### Example CSV:
```csv
order_number
#5377
#5381
#5383
```

The order fetcher automatically generates properly formatted CSV files.

## 🔄 Complete Workflow Example

**Scenario:** Refund all $0.99 orders from October 24th onwards

```bash
# Step 1: Fetch matching orders
python3 shopify_order_fetcher.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --from-date 2025-10-24 \
  --price 0.99 \
  --output orders_to_refund

# Step 2: Review the generated CSV
cat orders_to_refund.csv

# Step 3: Dry run to preview
python3 shopify_batch_refund.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --input orders_to_refund.csv \
  --dry-run

# Step 4: Process refunds
python3 shopify_batch_refund.py \
  --store your-store.myshopify.com \
  --token shpat_xxxxx \
  --input orders_to_refund.csv \
  --yes
```

## ⚙️ Advanced Options

### Order Fetcher Options

```
--store STORE          Shopify store URL (required)
--token TOKEN          Admin API access token (required)
--from-date DATE       Fetch orders from this date (YYYY-MM-DD)
--to-date DATE         Fetch orders up to this date (YYYY-MM-DD)
--price PRICE          Filter orders with exact price
--min-price PRICE      Filter orders with minimum price
--max-price PRICE      Filter orders with maximum price
--from-order ORDER     Start from specific order number
--to-order ORDER       End at specific order number
--status STATUS        Order status (any, open, closed, cancelled)
--financial-status     Financial status filter
--fulfillment-status   Fulfillment status filter
--tag TAG              Filter by order tag
--email EMAIL          Filter by customer email (partial match)
--output FILE          Output filename (without extension)
--format FORMAT        Output format (csv, json, both)
--no-summary           Skip displaying summary
```

### Batch Refund Options

```
--store STORE          Shopify store URL (required)
--token TOKEN          Admin API access token (required)
--input FILE           Input CSV file with order numbers (required)
--amount AMOUNT        Specific refund amount (default: full refund)
--notify               Send customer notification emails
--restock              Restock inventory
--note NOTE            Refund note (default: "Batch refund processed")
--yes                  Auto-approve without confirmation
--dry-run              Preview only, do not create actual refunds
--delay SECONDS        Delay between refunds (default: 12)
--log FILE             Custom log file name
--quiet                Minimal output
```

## 🛡️ Rate Limiting

Both scripts automatically handle Shopify's API rate limits:
- **Order Fetcher:** Automatically paginates through all results
- **Batch Refund:** Default 12-second delay between refunds (5 per minute)
  - Adjustable with `--delay` flag
  - Complies with Shopify's 5 refunds/minute limit

## 🔒 Security Best Practices

1. **Never commit API tokens** to version control
2. Use **environment variables** for credentials
3. Use **minimum required scopes** (only what you need)
4. **Rotate tokens periodically**
5. **Test with dry-run first** before processing live refunds
6. **Keep logs** of all operations

### Using Environment Variables

```bash
# In your .bashrc or .zshrc
export SHOPIFY_STORE="your-store.myshopify.com"
export SHOPIFY_TOKEN="shpat_xxxxx"

# Then use in scripts
python3 shopify_order_fetcher.py \
  --store $SHOPIFY_STORE \
  --token $SHOPIFY_TOKEN \
  --price 0.99
```

## 📊 Output Examples

### Order Fetcher Summary
```
======================================================================
ORDER SUMMARY
======================================================================
Total Orders: 427
Total Amount: USD $422.73

Financial Status:
  paid: 427

Fulfillment Status:
  fulfilled: 427

Order Range:
  First: #CC5377 - 2025-10-24T18:04:29-04:00
  Last: #CC5865 - 2025-11-03T07:10:28-05:00
======================================================================
```

### Batch Refund Progress
```
[1/427]
📦 Processing order: #5377
  📋 Order ID: 5787975548974
     Total: USD $0.99
  💰 Creating refund...
  ✅ Refund created successfully ($0.99)
  ⏳ Waiting 12 seconds (rate limit)...

...

============================================================
Batch Refund Processing Complete
============================================================
✅ Successful: 426
❌ Failed: 1
📊 Total: 427
⏱️  Time elapsed: 5134.5 seconds (85.6 minutes)
```

## ⚠️ Troubleshooting

### Error: "Order not found"
- Verify the order number is correct
- Ensure the order exists in your store
- Order numbers are case-sensitive

### Error: "Cannot refund more items than were purchased"
- Order has already been refunded
- Check order status in Shopify Admin

### Error: "Authentication failed"
- Verify your access token is correct
- Ensure the token has required scopes (`read_orders`, `write_orders`)
- Check your store URL is correct

### Rate Limit Issues
- Scripts automatically handle rate limiting
- Do not run multiple instances simultaneously
- Adjust `--delay` if needed for custom rate limiting

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 💬 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/shopify-admin-tools/issues)
- **Documentation:** [Shopify Admin API Docs](https://shopify.dev/docs/api/admin)

## 📜 Changelog

### v2.0.0 - 2025-11
- Complete rewrite with command-line argument support
- Added flexible filtering for order fetcher
- Added dry-run mode for batch refunds
- Added partial refund support
- Added customer notification options
- Added inventory restocking support
- Improved error handling and logging
- Added JSON export option

### v1.0.0 - 2025-11
- Initial release
- Basic order fetching and batch refund functionality

---

**Made with ❤️ for the Shopify community**
