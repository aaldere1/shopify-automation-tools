# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Python-based toolkit for automating Shopify Admin API operations. The codebase consists of two main standalone scripts that work together but can be used independently:

1. **shopify_order_fetcher.py** - Fetches and filters orders from Shopify
2. **shopify_batch_refund.py** - Processes batch refunds for orders

Both scripts are command-line tools with `argparse` for argument handling. No build system or package manager beyond pip is used.

## Architecture

### Two-Tool Workflow Pattern
The typical workflow is: fetch → review → refund

```
shopify_order_fetcher.py → CSV file → shopify_batch_refund.py
```

Each script is self-contained with its own class-based architecture:
- `ShopifyOrderFetcher` class handles all order fetching logic
- `ShopifyRefundProcessor` class handles all refund logic

### Shopify API Integration
- API Version: `2025-10` (hardcoded in both scripts)
- Authentication: Admin API access token via header `X-Shopify-Access-Token`
- Required scopes: `read_orders` (fetcher), `write_orders` (refund)

### Key Design Decisions

**Rate Limiting:**
- Refund processor: Default 12-second delay between refunds (5 per minute max)
- Order fetcher: Automatic pagination with Link header parsing
- Both handle Shopify's rate limits automatically

**Transaction Detection:**
- Refunds require finding payment transactions with `kind` in `['capture', 'sale']` and `status == 'success'`
- This is critical - Shopify stores may use either "capture" or "sale" transaction types

**CSV Flexibility:**
- Refund script accepts multiple column name variations for order numbers
- Column detection is case-insensitive with normalization (spaces → underscores)
- Accepted column names: `order_number`, `order_name`, `order`, `name`, `number` (and variations)

## Running the Tools

### Setup
```bash
pip install -r requirements.txt
```

### Order Fetcher Examples
```bash
# Fetch with price filter
python3 shopify_order_fetcher.py --store store.myshopify.com --token shpat_xxx --price 0.99

# Fetch with date range and export to JSON
python3 shopify_order_fetcher.py --store store.myshopify.com --token shpat_xxx \
  --from-date 2025-01-01 --to-date 2025-01-31 --format json

# Fetch from specific order number
python3 shopify_order_fetcher.py --store store.myshopify.com --token shpat_xxx \
  --from-order CC5377 --price 0.99
```

### Batch Refund Examples
```bash
# Always test with dry-run first
python3 shopify_batch_refund.py --store store.myshopify.com --token shpat_xxx \
  --input orders.csv --dry-run

# Process full refunds
python3 shopify_batch_refund.py --store store.myshopify.com --token shpat_xxx \
  --input orders.csv --yes

# Partial refund with notification
python3 shopify_batch_refund.py --store store.myshopify.com --token shpat_xxx \
  --input orders.csv --amount 10.00 --notify
```

### Complete Workflow
```bash
# 1. Fetch orders
python3 shopify_order_fetcher.py --store store.com --token $TOKEN \
  --from-date 2025-10-24 --price 0.99 --output orders_to_refund

# 2. Review CSV
cat orders_to_refund.csv

# 3. Test with dry-run
python3 shopify_batch_refund.py --store store.com --token $TOKEN \
  --input orders_to_refund.csv --dry-run

# 4. Execute refunds
python3 shopify_batch_refund.py --store store.com --token $TOKEN \
  --input orders_to_refund.csv --yes
```

## Common Modifications

### Changing API Version
Both scripts hardcode `self.api_version = '2025-10'`. Update this in both files if Shopify deprecates this version.

### Adding New Filters to Order Fetcher
1. Add argument in `main()` argparse setup
2. Pass parameter to `fetch_orders()` method (for API-level filters) or `filter_orders()` method (for client-side filters)
3. API-level filters go in the `params` dict before the request
4. Client-side filters are list comprehensions in `filter_orders()`

### Adding New Refund Options
1. Add argument in `main()` argparse setup
2. Pass to `process_refund()` then `create_refund()` method
3. Modify the `payload` dict structure in `create_refund()` method

## Credentials and Security

**Environment Variables (Recommended):**
```bash
export SHOPIFY_STORE="store.myshopify.com"
export SHOPIFY_TOKEN="shpat_xxxxx"
```

Then use: `--store $SHOPIFY_STORE --token $SHOPIFY_TOKEN`

**What .gitignore Blocks:**
- All generated order/refund files: `orders_for_refund_*.csv`, `refund_log_*.txt`
- All output files: `shopify_orders_*.csv`, `shopify_orders_*.json`
- `.env` files, anything with `token` or `credentials` in the name

## Testing Approach

**No formal test suite exists.** Testing is done manually:

1. **Order Fetcher Testing:**
   - Test with `--no-summary` and small datasets first
   - Verify CSV output structure matches expected columns
   - Check JSON output is valid with: `python3 -m json.tool output.json`

2. **Refund Testing:**
   - **ALWAYS use `--dry-run` first** - this is critical
   - Test with 1-2 orders before bulk processing
   - Verify transaction detection works (check for "capture" or "sale" transactions)
   - Monitor for rate limit compliance (12-second delays should be visible)

3. **Production Verification:**
   - The codebase was production-tested with 427 successful refunds
   - Known working: $0.99 refunds, capture-type transactions, rate limiting

## Common Issues

**"Cannot refund more items than were purchased"**
- Order already refunded or partially refunded
- Check `financial_status` in Shopify Admin

**"Refund amount must be greater than 0"**
- The `calculate` endpoint returns $0 for some edge cases
- Scripts bypass this by using explicit amounts from `total_price`

**"No payment transaction found"**
- Looking for wrong transaction type
- Scripts check for both 'capture' and 'sale' kinds
- Verify transaction has `status == 'success'`

**Rate Limiting**
- Default is 12 seconds between refunds (5/minute)
- Adjustable via `--delay` flag
- Do not run multiple instances simultaneously

## Output Files

**Order Fetcher Generates:**
- `shopify_orders_TIMESTAMP.csv` (or custom name via `--output`)
- `shopify_orders_TIMESTAMP.json` (if `--format json` or `--format both`)

**Refund Processor Generates:**
- `refund_log_TIMESTAMP.txt` (summary of refund run)

All timestamped files use format: `YYYYMMDD_HHMMSS`
