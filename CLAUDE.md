# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

A toolkit for Shopify Admin API automation and integrations. The codebase has two main parts:

1. **Python CLI Tools** - Standalone scripts for order fetching, batch refunds, replacement orders, and third-party API clients (Amplifier, Printful)
2. **TypeScript/Vercel Integration** - Shopify→Notion sync running on Vercel cron (every 15 minutes)

## Architecture

### Python Tools (CLI)

All Python scripts are self-contained with class-based architecture and `argparse` for argument handling.

**Core Order Management:**
- `shopify_order_fetcher.py` - Fetch/filter orders → exports CSV/JSON
- `shopify_batch_refund.py` - Process batch refunds from CSV
- `create_replacement_order.py` - Create $0 replacement orders for customers who didn't receive shipments

**Sales Analysis & Reporting:**
- `program_book_sales_analysis.py` - Analyze program book sales with breakdowns by show, time period, geography → exports CSV
- `full_sales_analysis.py` - Comprehensive analysis of ALL products with category detection → exports multiple CSVs

**Third-Party Clients:**
- `amplifier_client.py` - Amplifier fulfillment API client
- `printful_client.py` - Printful API v2 client

**Typical Workflow:**
```
shopify_order_fetcher.py → CSV file → shopify_batch_refund.py
```

### TypeScript/Vercel (Automated Sync)

Deployed on Vercel with cron job running every 15 minutes.

**Key Files:**
- `lib/shopifyNotionSync.ts` - Core sync logic (Shopify orders → Notion database)
- `api/shopify-notion-sync.ts` - Vercel serverless function endpoint
- `api/status-page.ts` - Status dashboard (root route)

**Sync Behavior:**
- Cron runs fetch only last 24 hours of orders
- Creates new pages for new orders, updates unfulfilled orders
- Skips fulfilled orders (they rarely change)
- Uses Notion Data Sources API

## Commands

### Setup
```bash
pip install -r requirements.txt  # Python dependencies
npm install                       # TypeScript/Vercel dependencies
vercel env pull .env              # Pull credentials from Vercel
```

### Python Tools
```bash
# Fetch orders with filters
python3 shopify_order_fetcher.py --store $SHOPIFY_STORE --token $TOKEN --price 0.99

# Batch refund (ALWAYS dry-run first)
python3 shopify_batch_refund.py --store $SHOPIFY_STORE --token $TOKEN --input orders.csv --dry-run

# Create replacement order (sends confirmation email)
python3 create_replacement_order.py CC5875
python3 create_replacement_order.py CC5875 --dry-run
python3 create_replacement_order.py CC5875 --no-email
```

### Sales Analysis
```bash
# Program book sales analysis (for partnership discussions)
python3 program_book_sales_analysis.py

# Full sales analysis (all products, all time)
python3 full_sales_analysis.py

# With date range filter
python3 full_sales_analysis.py --from-date 2024-01-01 --to-date 2024-12-31
```

### TypeScript/Notion Sync
```bash
npm run sync:notion              # Manual sync
npm run backfill:existing        # Backfill existing orders
npm run backfill:progress        # Check backfill progress
```

## Environment Variables

Stored in Vercel, pull locally with `vercel env pull .env`:

| Variable | Description |
|----------|-------------|
| `SHOPIFY_STORE_DOMAIN` | Store URL (e.g., shop.myshopify.com) |
| `SHOPIFY_ADMIN_TOKEN` | Admin API token (shpat_xxx) |
| `NOTION_TOKEN` | Notion integration token |
| `NOTION_DATABASE_ID` | Target Notion database |
| `NOTION_DATA_SOURCE_ID` | Notion data source (optional) |

**Required Shopify Scopes:** `read_orders`, `write_orders`, `write_draft_orders`

### 1Password Credentials (CineConcerts Team)

API credentials are stored in 1Password:
- **Account:** `alderete-family.1password.com`
- **Vault:** Private
- **Item:** "CineConcerts - API Keys"

```bash
# View all credentials
op item get "CineConcerts - API Keys" --vault="Private" --account="alderete-family.1password.com" --reveal

# Export to .env.local
op item get "CineConcerts - API Keys" --vault="Private" --account="alderete-family.1password.com" --format=json | jq -r '.fields[] | select(.value != null and .label != "notesPlain" and .id != "validFrom" and .id != "expires") | "\(.label)=\"\(.value)\""' > .env.local
```

**Available:** `SHOPIFY_STORE`, `SHOPIFY_TOKEN`, `AMPLIFIER_API_KEY`, `PRINTFUL_TOKEN`

## Shopify API Integration

- **API Version:** `2025-10` (hardcoded in Python scripts and `lib/shopifyNotionSync.ts`)
- **Authentication:** `X-Shopify-Access-Token` header
- **Rate Limiting:**
  - Refund processor: 12-second delay (5/minute)
  - Order fetcher: Automatic pagination via Link header
  - Notion sync: 200-300ms delays between API calls

**Transaction Detection for Refunds:**
- Requires finding transactions with `kind` in `['capture', 'sale']` and `status == 'success'`
- Shopify stores may use either transaction type

## Key Design Patterns

**Order Creation via API:**
- Use `send_receipt: true` to trigger confirmation email
- Use `send_fulfillment_receipt: true` for shipping notifications
- $0 orders work with `financial_status: 'paid'` and no transaction

**Notion Sync:**
- Uses `Order ID` (Shopify numeric ID) as unique identifier
- Preserves manual tag edits while syncing
- Rebuilds page blocks on updates for fresh timeline/tracking data

## Common Issues

**"Cannot refund more items than were purchased"** - Order already refunded

**"No payment transaction found"** - Check for both 'capture' and 'sale' transaction kinds

**Rate Limiting** - Don't run multiple refund instances simultaneously

**API Scope Errors** - Verify token has required scopes; may need to recreate app if adding scopes doesn't work

**Notion Sync Duplicates** - Check `Order ID` property; sync uses this as unique key

---

## Detailed Shopify→Notion Sync Documentation

**For comprehensive documentation on the Notion sync system, see: `SHOPIFY_NOTION_SYNC_README.md`**

This includes:
- Architecture diagrams and data flow
- Notion database schema (all 12 properties)
- Cron job behavior (fulfilled vs unfulfilled orders)
- Backfill script configuration
- Field mapping tables
- Known issues and fixes
- Troubleshooting guide

### Key Sync Behaviors (Quick Reference)

**Cron Job (every 15 min):**
- Fetches last 24 hours of orders from Shopify
- **Fulfilled orders**: SKIPPED entirely (never touched)
- **Unfulfilled orders**: Updates Payment Status, Fulfillment Status, Delivery Status only
- **New orders**: Creates full page with all properties and content blocks

**Backfill Script:**
- Run with `npm run backfill:existing`
- Updates missing fields: Channel, Payment Status, Fulfillment Status, Delivery Status, Delivery method
- Uses rate limiting (3 concurrent, 3 req/sec Notion, 2 req/sec Shopify)

### Recent Fixes (November 2024)

1. **Unicode sanitization**: Added `sanitizeString()` to strip invisible characters (U+2060) from Shopify shipping titles that caused Notion select value errors

2. **Backfill Delivery method bug**: Fixed condition in `updateOrderFields` that skipped Delivery method updates for orders without Shopify shipping_lines. Now correctly defaults to "Standard Shipping"
