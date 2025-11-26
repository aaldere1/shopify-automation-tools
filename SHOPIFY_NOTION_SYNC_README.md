# Shopify → Notion Order Sync System

This document provides comprehensive documentation for the automated Shopify to Notion order synchronization system.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Notion Database Schema](#notion-database-schema)
4. [Cron Job Behavior](#cron-job-behavior)
5. [Backfill Script](#backfill-script)
6. [Environment Variables](#environment-variables)
7. [Commands](#commands)
8. [Data Flow](#data-flow)
9. [Field Mapping](#field-mapping)
10. [Known Issues & Fixes](#known-issues--fixes)
11. [Troubleshooting](#troubleshooting)

---

## Overview

The system synchronizes Shopify orders to a Notion database, providing a visual dashboard for order tracking. It consists of two main components:

1. **Cron Job** (`api/shopify-notion-sync.ts`) - Runs every 15 minutes on Vercel, syncs new orders and updates unfulfilled orders
2. **Backfill Script** (`scripts/backfill-existing-orders.ts`) - One-time script to populate missing fields on existing orders

### Key Design Principles

- **Incremental sync**: Only fetches last 24 hours of orders (not entire history)
- **Non-destructive**: Preserves manual edits to Tags and other fields
- **Fulfilled orders are immutable**: Once fulfilled, orders are never modified
- **Rate-limited**: Respects both Shopify and Notion API limits

---

## Architecture

```
┌─────────────────┐     Every 15 min      ┌─────────────────┐
│   Vercel Cron   │ ───────────────────── │  Shopify API    │
│   (api/shopify- │                       │  (last 24 hrs)  │
│   notion-sync)  │                       └─────────────────┘
└────────┬────────┘                              │
         │                                       │
         │  For each order:                      │
         │  1. Check if exists in Notion         │
         │  2. If fulfilled → skip               │
         │  3. If unfulfilled → update status    │
         │  4. If new → create full page         │
         │                                       ▼
         │                               ┌─────────────────┐
         └─────────────────────────────► │  Notion DB      │
                                         │  (Data Source)  │
                                         └─────────────────┘
```

### Key Files

| File | Purpose |
|------|---------|
| `lib/shopifyNotionSync.ts` | Core sync logic, shared by cron and manual runs |
| `api/shopify-notion-sync.ts` | Vercel serverless function (cron endpoint) |
| `api/status-page.ts` | Status dashboard at root URL |
| `scripts/backfill-existing-orders.ts` | Backfill missing fields on existing orders |

---

## Notion Database Schema

The sync creates/updates these properties on each order page:

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `ORDER` | Title | `order.name` | Order name (e.g., #CC5922) |
| `Order ID` | Number | `order.id` | Shopify numeric ID (unique key) |
| `Date` | Date | `order.created_at` | Order creation date |
| `Customer` | Rich Text | `order.customer` | Customer name or email |
| `Total` | Number | `order.total_price` | Order total in dollars |
| `Items` | Rich Text | `order.line_items` | Summary of items purchased |
| `Tags` | Multi-select | `order.tags` | Order tags (preserved on updates) |
| `Channel` | Select | `order.source_name` | Sales channel (Online Store, POS, Draft Order) |
| `Payment Status` | Select | `order.financial_status` | Paid, Refunded, Pending, etc. |
| `Fulfillment Status` | Select | `order.fulfillment_status` | Fulfilled, Unfulfilled, Partial |
| `Delivery Status` | Select | Derived | Pending, Fulfilled, In Transit, etc. |
| `Delivery method` | Select | `order.shipping_lines[0]` | Shipping method name |

### Select Field Values

**Payment Status**: Paid, Pending, Refunded, Partially Refunded, Voided, Unknown

**Fulfillment Status**: Fulfilled, Unfulfilled, Partial

**Delivery Status**: Pending, Fulfilled, In Transit, Out For Delivery, Delivered, Failure

**Channel**: Online Store, POS, Draft Order

**Delivery method**: Priority Mail, Flat Shipping Rate, Standard Shipping, Standard International, etc.

---

## Cron Job Behavior

The cron job runs every 15 minutes and follows this logic:

### 1. Fetch Orders from Shopify
- Only fetches orders from the **last 24 hours**
- Uses `created_at_min` parameter to limit scope
- Paginates through all results (250 per page)

### 2. Process Each Order

```
For each order in fetched orders:
│
├─► Order exists in Notion?
│   │
│   ├─► YES + Fulfilled in Shopify
│   │   └─► SKIP (don't touch fulfilled orders)
│   │
│   ├─► YES + Unfulfilled in Shopify
│   │   └─► UPDATE status fields only:
│   │       • Payment Status
│   │       • Fulfillment Status
│   │       • Delivery Status
│   │
│   └─► NO (new order)
│       └─► CREATE full page with all properties and content blocks
```

### What Gets Updated vs. Preserved

| Field | On Update (Unfulfilled) | Preserved |
|-------|------------------------|-----------|
| Payment Status | ✅ Updated | |
| Fulfillment Status | ✅ Updated | |
| Delivery Status | ✅ Updated | |
| Delivery method | | ✅ Preserved |
| Channel | | ✅ Preserved |
| Tags | | ✅ Preserved |
| Customer | | ✅ Preserved |
| Total | | ✅ Preserved |
| Page content/blocks | | ✅ Preserved |

### Why Fulfilled Orders Are Skipped

Once an order is fulfilled:
- Payment is complete
- Shipping is done
- Status won't change further
- Skipping saves API calls and prevents accidental overwrites

---

## Backfill Script

The backfill script (`scripts/backfill-existing-orders.ts`) is used to populate missing fields on orders that were created before certain fields were added, or when initial sync didn't capture all data.

### When to Run Backfill

- After adding new fields to the schema
- If orders are missing Delivery method, Channel, or status fields
- After fixing bugs in the sync logic

### How It Works

1. Queries ALL orders from Notion (paginated, 100 at a time)
2. For each order with missing fields:
   - Fetches fresh data from Shopify API
   - Updates only the missing fields
   - Preserves existing data
3. Uses rate limiting to avoid API throttling

### Configuration

```typescript
const BATCH_SIZE = 100;           // Orders per Notion query
const CONCURRENT_REQUESTS = 3;    // Parallel updates
const NOTION_RATE_LIMIT = 3;      // Requests per second
const SHOPIFY_RATE_LIMIT = 2;     // Requests per second
```

### Fields Updated by Backfill

Only updates fields that are **blank** in Notion:
- Channel (defaults to "Online Store")
- Payment Status (from Shopify or "Unknown")
- Fulfillment Status (from Shopify or "unfulfilled")
- Delivery Status (derived from fulfillment data or "pending")
- Delivery method (from shipping_lines or "Standard Shipping")

---

## Environment Variables

Store these in Vercel (pull locally with `vercel env pull .env`):

| Variable | Required | Description |
|----------|----------|-------------|
| `SHOPIFY_STORE_DOMAIN` | Yes | Store URL (e.g., `mystore.myshopify.com`) |
| `SHOPIFY_ADMIN_TOKEN` | Yes | Admin API access token (`shpat_xxx`) |
| `NOTION_TOKEN` | Yes | Notion integration token |
| `NOTION_DATABASE_ID` | Yes | Target Notion database ID |
| `NOTION_DATA_SOURCE_ID` | No | Data source ID (auto-detected if not set) |

### Required Shopify Scopes

The Admin API token needs these scopes:
- `read_orders` - Fetch order data
- `write_orders` - (Optional, for other scripts)

---

## Commands

### Setup

```bash
# Install dependencies
npm install

# Pull environment variables from Vercel
vercel env pull .env
```

### Manual Sync

```bash
# Run sync manually (same as cron)
npm run sync:notion
```

### Backfill

```bash
# Run backfill to populate missing fields
npm run backfill:existing

# Check backfill progress (while running)
npm run backfill:progress
```

### Deployment

```bash
# Deploy to Vercel production
vercel --prod

# Check deployment status
vercel ls
```

---

## Data Flow

### New Order Created in Shopify

```
T+0:   Customer places order
T+15m: Cron job runs, detects new order
       → Creates Notion page with full content
       → Sets all properties (Channel, Payment Status, etc.)
       → Adds page blocks (Timeline, Items, Tracking, etc.)
```

### Order Gets Fulfilled

```
T+0:   Order fulfilled in Shopify
T+15m: Cron job runs, detects order is unfulfilled in Notion
       → Updates Payment Status, Fulfillment Status, Delivery Status
T+30m: Cron job runs, sees order is now fulfilled
       → Skips order entirely (no changes made)
```

### Order Gets Refunded

```
T+0:   Order refunded in Shopify
T+15m: Cron job runs (if within 24 hours of creation)
       → Updates Payment Status to "Refunded"
       → If order is unfulfilled, also updates fulfillment fields
```

---

## Field Mapping

### Channel (source_name)

| Shopify Value | Notion Value |
|---------------|--------------|
| `web` | Online Store |
| `pos` | POS |
| `shopify_draft_order` | Draft Order |
| `null` / undefined | Online Store |
| Other | Capitalized version |

### Fulfillment Status

| Shopify Value | Notion Value |
|---------------|--------------|
| `fulfilled` | Fulfilled |
| `partial` | Partial |
| `null` / undefined | unfulfilled |

### Payment Status (financial_status)

| Shopify Value | Notion Value |
|---------------|--------------|
| `paid` | Paid |
| `pending` | Pending |
| `refunded` | Refunded |
| `partially_refunded` | Partially Refunded |
| `voided` | Voided |
| `null` / undefined | Unknown |

### Delivery Status

Derived from fulfillment data:
1. If `fulfillment_status` exists → use normalized version
2. Else if `fulfillments[0].shipment_status` exists → use that
3. Else → "pending"

### Delivery Method

From `shipping_lines[0]`:
1. `title` (e.g., "Priority Mail")
2. `source` (e.g., "shopify")
3. `code` (e.g., "STANDARD")
4. `carrier_identifier`
5. Default: "Standard Shipping"

---

## Known Issues & Fixes

### Issue: Unicode Characters in Shipping Titles

**Problem**: Shopify sometimes returns invisible Unicode characters (U+2060 WORD JOINER) in shipping line titles, causing Notion to reject the select value.

**Fix**: Added `sanitizeString()` function to strip invisible characters:
```typescript
function sanitizeString(str: string | null | undefined): string | null {
  if (!str) return null;
  return str.replace(/[\u2060\u200B\u200C\u200D\uFEFF]/g, '').trim();
}
```

### Issue: Backfill Not Updating Delivery Method

**Problem**: The backfill script had a bug where orders without Shopify shipping_lines would skip the Delivery method update entirely, even though they should default to "Standard Shipping".

**Root Cause**: The `needsUpdate` check in `updateOrderFields` had an extra condition:
```typescript
// Buggy version:
(!existingProps['Delivery method']?.select?.name && deriveDeliveryMethod(order))

// Fixed version:
!existingProps['Delivery method']?.select?.name
```

**Fix**: Commit `fc903d9` - Removed the `&& deriveDeliveryMethod(order)` condition.

### Issue: Cron Timeout with Large Backfill

**Problem**: Trying to backfill thousands of orders in a single cron run causes Vercel timeout.

**Solution**:
1. Cron only processes last 24 hours (incremental)
2. Use separate backfill script for historical data
3. Backfill script has its own rate limiting

---

## Troubleshooting

### Orders Not Appearing in Notion

1. Check if order is within last 24 hours
2. Verify environment variables are set correctly
3. Check Vercel function logs for errors
4. Run manual sync: `npm run sync:notion`

### Fields Are Blank

1. Run backfill: `npm run backfill:existing`
2. Check if Shopify has the data (some fields may be null)
3. Verify field exists in Notion database schema

### Rate Limiting Errors

1. Don't run multiple sync/backfill processes simultaneously
2. Check Shopify API usage in admin dashboard
3. Increase delay between requests if needed

### Notion API Errors

**`conflict_error`**: Page is being edited elsewhere. The backfill script retries these automatically with exponential backoff.

**`object_already_exists`**: Order was created between check and create. Safe to ignore.

**`validation_failed`**: Usually means a select value doesn't exist. Check for Unicode issues or invalid characters.

### Checking Order Status

```bash
# Check specific orders
npx tsx scripts/check-multiple-orders.ts

# Check older orders
npx tsx scripts/check-older-orders.ts
```

---

## API Versions

| API | Version | Location |
|-----|---------|----------|
| Shopify Admin API | `2025-10` | `lib/shopifyNotionSync.ts` line 4 |
| Notion API | `2025-09-03` | `lib/shopifyNotionSync.ts` line 5 |

---

## Maintenance

### Adding New Fields

1. Add property definition in `ensureDatabaseSchema()`
2. Add field mapping in `buildNotionProperties()`
3. If needed for existing orders, add to backfill script
4. Run backfill after deploying

### Updating API Versions

1. Update version constant in `lib/shopifyNotionSync.ts`
2. Test with `npm run sync:notion`
3. Check for breaking changes in API changelog
4. Deploy to Vercel

### Monitoring

- **Vercel Dashboard**: Check function invocations and errors
- **Status Page**: Visit root URL of deployment
- **Notion**: Verify orders are appearing with correct data

---

## Contact & Support

For issues with this sync system:
1. Check this README and troubleshooting section
2. Review Vercel function logs
3. Check Shopify and Notion API status pages
4. Review recent commits for changes

Last Updated: November 2024
