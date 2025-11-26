/**
 * Repair Affected Orders Script
 *
 * This script identifies orders in Notion that have missing/empty content blocks
 * and rebuilds them with fresh data from Shopify without touching the properties.
 *
 * Usage:
 *   npx tsx scripts/repair-affected-orders.ts --dry-run    # Preview what would be fixed
 *   npx tsx scripts/repair-affected-orders.ts              # Actually fix the orders
 *   npx tsx scripts/repair-affected-orders.ts --from-date 2025-11-17  # Only orders from specific date
 */

import { Client } from '@notionhq/client';

const SHOPIFY_API_VERSION = '2025-10';
const NOTION_VERSION = '2025-09-03';

type ShopifyOrder = {
  id: number;
  name: string;
  order_number: number;
  tags?: string;
  created_at: string;
  processed_at?: string | null;
  updated_at?: string;
  closed_at?: string | null;
  canceled_at?: string | null;
  cancel_reason?: string | null;
  current_total_price?: string;
  total_price?: string;
  subtotal_price?: string;
  total_discounts?: string;
  total_tax?: string;
  current_total_tax?: string;
  total_shipping_price_set?: {
    shop_money?: {
      amount?: string;
      currency_code?: string;
    };
  };
  currency?: string;
  financial_status?: string;
  fulfillment_status?: string | null;
  email?: string;
  phone?: string | null;
  note?: string | null;
  source_name?: string | null;
  gateway?: string | null;
  payment_gateway_names?: string[];
  line_items: any[];
  shipping_lines?: any[];
  fulfillments?: any[];
  customer?: any | null;
  shipping_address?: any | null;
  billing_address?: any | null;
};

import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

function loadEnv() {
  const envPath = join(process.cwd(), '.env');

  if (existsSync(envPath)) {
    const content = readFileSync(envPath, 'utf-8');
    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
        const [key, ...valueParts] = trimmed.split('=');
        const value = valueParts.join('=').replace(/^["']|["']$/g, '');
        process.env[key] = value;
      }
    }
  }
}

function getEnvConfig() {
  const required = ['SHOPIFY_STORE_DOMAIN', 'SHOPIFY_ADMIN_TOKEN', 'NOTION_TOKEN', 'NOTION_DATABASE_ID'];
  const missing = required.filter(k => !process.env[k]);
  if (missing.length) {
    throw new Error(`Missing env vars: ${missing.join(', ')}`);
  }
  return {
    storeDomain: process.env.SHOPIFY_STORE_DOMAIN!,
    shopifyToken: process.env.SHOPIFY_ADMIN_TOKEN!,
    notionToken: process.env.NOTION_TOKEN!,
    notionDatabaseId: process.env.NOTION_DATABASE_ID!,
    notionDataSourceId: process.env.NOTION_DATA_SOURCE_ID,
  };
}

async function delay(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function resolveDataSourceId(notion: Client, env: ReturnType<typeof getEnvConfig>): Promise<string> {
  if (env.notionDataSourceId) return env.notionDataSourceId;

  const database: any = await notion.databases.retrieve({ database_id: env.notionDatabaseId });
  const dataSources = database.data_sources as Array<{ id: string }> | undefined;
  if (!dataSources?.length) throw new Error('No data sources found');
  return dataSources[0].id;
}

// Find orders in Notion that have few or no content blocks (damaged)
async function findDamagedOrders(
  notion: Client,
  dataSourceId: string,
  fromDate?: string
): Promise<Array<{ pageId: string; orderId: number; orderName: string; blockCount: number }>> {
  const damaged: Array<{ pageId: string; orderId: number; orderName: string; blockCount: number }> = [];
  let cursor: string | undefined;
  let totalChecked = 0;

  console.log('🔍 Scanning Notion pages for damaged orders...');

  do {
    const queryBody: Record<string, unknown> = {
      data_source_id: dataSourceId,
      page_size: 100,
    };

    // Add date filter if specified
    if (fromDate) {
      queryBody.filter = {
        property: 'Date',
        date: { on_or_after: fromDate },
      };
    }

    if (cursor) {
      queryBody.start_cursor = cursor;
    }

    const response: any = await notion.dataSources.query(queryBody as any);
    const results = response.results || [];

    for (const page of results) {
      totalChecked++;
      const orderId = page.properties?.['Order ID']?.number;
      const orderTitle = page.properties?.ORDER?.title?.[0]?.plain_text || 'Unknown';

      if (!orderId) continue;

      // Check how many blocks the page has
      try {
        const blocks: any = await notion.blocks.children.list({
          block_id: page.id,
          page_size: 10,
        });

        const blockCount = blocks.results?.length || 0;

        // If page has 0-2 blocks, it's likely damaged (normal pages have ~20+ blocks)
        if (blockCount <= 2) {
          damaged.push({
            pageId: page.id,
            orderId,
            orderName: orderTitle,
            blockCount,
          });
          console.log(`  ❌ ${orderTitle} - only ${blockCount} blocks (damaged)`);
        }

        await delay(100); // Rate limit for block reads
      } catch (err) {
        console.error(`  ⚠️  Error checking blocks for ${orderTitle}:`, err);
      }
    }

    cursor = response.has_more ? response.next_cursor ?? undefined : undefined;

    if (totalChecked % 50 === 0) {
      console.log(`  Checked ${totalChecked} pages, found ${damaged.length} damaged so far...`);
    }
  } while (cursor);

  console.log(`\n📊 Scan complete: ${totalChecked} pages checked, ${damaged.length} damaged found`);
  return damaged;
}

// Fetch a specific order from Shopify by Order ID
async function fetchOrderFromShopify(env: ReturnType<typeof getEnvConfig>, orderId: number): Promise<ShopifyOrder | null> {
  const url = `https://${env.storeDomain}/admin/api/${SHOPIFY_API_VERSION}/orders/${orderId}.json`;

  const response = await fetch(url, {
    headers: {
      'X-Shopify-Access-Token': env.shopifyToken,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    console.error(`Failed to fetch order ${orderId}: ${response.status}`);
    return null;
  }

  const data = await response.json() as { order: ShopifyOrder };
  return data.order;
}

// Build page blocks from Shopify order (same as in shopifyNotionSync.ts)
function buildPageBlocks(order: ShopifyOrder): any[] {
  const blocks: any[] = [];

  const headingBlock = (content: string) => ({
    object: 'block',
    type: 'heading_2',
    heading_2: {
      rich_text: [{ type: 'text', text: { content: content.slice(0, 1800) } }],
      color: 'default',
    },
  });

  const paragraphBlock = (content: string) => ({
    object: 'block',
    type: 'paragraph',
    paragraph: {
      rich_text: [{ type: 'text', text: { content: content.slice(0, 1800) } }],
      color: 'default',
    },
  });

  const bulletBlock = (content: string) => ({
    object: 'block',
    type: 'bulleted_list_item',
    bulleted_list_item: {
      rich_text: [{ type: 'text', text: { content: content.slice(0, 1800) } }],
      color: 'default',
    },
  });

  const formatMoney = (amount: number, currency = 'USD') => `${currency} ${amount.toFixed(2)}`;
  const formatDate = (d?: string | null) => d ? new Date(d).toISOString() : 'Unknown';

  // Order Overview
  blocks.push(headingBlock('Order Overview'));
  blocks.push(paragraphBlock(`${order.name} • ${formatMoney(parseFloat(order.total_price || '0'), order.currency)}`));

  // Timeline
  blocks.push(headingBlock('Timeline'));
  blocks.push(bulletBlock(`Created: ${formatDate(order.created_at)}`));
  if (order.processed_at) blocks.push(bulletBlock(`Processed: ${formatDate(order.processed_at)}`));
  if (order.updated_at) blocks.push(bulletBlock(`Updated: ${formatDate(order.updated_at)}`));
  if (order.closed_at) blocks.push(bulletBlock(`Closed: ${formatDate(order.closed_at)}`));
  if (order.canceled_at) {
    blocks.push(bulletBlock(`Cancelled: ${formatDate(order.canceled_at)}${order.cancel_reason ? ` (${order.cancel_reason})` : ''}`));
  }

  // Line Items
  blocks.push(headingBlock('Line Items'));
  if (order.line_items?.length) {
    for (const item of order.line_items) {
      const itemText = `${item.quantity} × ${item.title}${item.variant_title ? ` (${item.variant_title})` : ''}${item.sku ? ` • SKU: ${item.sku}` : ''} • ${formatMoney(parseFloat(item.price) * item.quantity, order.currency)}`;
      blocks.push(bulletBlock(itemText));
    }
  } else {
    blocks.push(paragraphBlock('No items found.'));
  }

  // Tracking & Fulfillment
  blocks.push(headingBlock('Tracking & Fulfillment'));
  const fulfillments = order.fulfillments || [];
  if (fulfillments.length) {
    fulfillments.forEach((f: any, i: number) => {
      blocks.push(bulletBlock(`Fulfillment #${i + 1}: ${(f.status || f.shipment_status || 'pending').replace(/_/g, ' ')}`));
      if (f.tracking_company) blocks.push(bulletBlock(`Carrier: ${f.tracking_company}`));
      if (f.tracking_numbers?.length) blocks.push(bulletBlock(`Tracking #: ${f.tracking_numbers.join(', ')}`));
      if (f.tracking_urls?.length) {
        f.tracking_urls.slice(0, 3).forEach((url: string) => {
          blocks.push({
            object: 'block',
            type: 'paragraph',
            paragraph: {
              rich_text: [{ type: 'text', text: { content: 'Tracking Link', link: { url } } }],
            },
          });
        });
      }
    });
  } else {
    blocks.push(paragraphBlock('No tracking yet.'));
  }

  // Customer & Addresses
  blocks.push(headingBlock('Customer & Addresses'));
  const customerName = [
    order.customer?.first_name || order.shipping_address?.first_name || '',
    order.customer?.last_name || order.shipping_address?.last_name || '',
  ].filter(Boolean).join(' ') || order.email || 'Unknown';
  blocks.push(paragraphBlock(`Customer: ${customerName}`));
  if (order.email) blocks.push(paragraphBlock(`Email: ${order.email}`));
  if (order.phone) blocks.push(paragraphBlock(`Phone: ${order.phone}`));

  if (order.shipping_address) {
    const addr = order.shipping_address;
    const parts = [
      addr.name || `${addr.first_name || ''} ${addr.last_name || ''}`.trim(),
      addr.company,
      addr.address1,
      addr.address2,
      [addr.city, addr.province || addr.province_code, addr.zip].filter(Boolean).join(', '),
      addr.country || addr.country_code,
      addr.phone,
    ].filter(Boolean).join('\n');
    if (parts) blocks.push(paragraphBlock(`Shipping:\n${parts}`));
  }

  // Payment & Totals
  blocks.push(headingBlock('Payment & Totals'));
  const subtotal = parseFloat(order.subtotal_price || order.total_price || '0');
  const discounts = parseFloat(order.total_discounts || '0');
  const tax = parseFloat(order.total_tax || '0');
  const total = parseFloat(order.total_price || '0');

  blocks.push(bulletBlock(`Subtotal: ${formatMoney(subtotal, order.currency)}`));
  if (discounts) blocks.push(bulletBlock(`Discounts: -${formatMoney(discounts, order.currency)}`));
  if (tax) blocks.push(bulletBlock(`Tax: ${formatMoney(tax, order.currency)}`));
  blocks.push(bulletBlock(`Total: ${formatMoney(total, order.currency)}`));
  if (order.payment_gateway_names?.length) {
    blocks.push(bulletBlock(`Gateway: ${order.payment_gateway_names.join(', ')}`));
  }

  if (order.note) {
    blocks.push(headingBlock('Order Note'));
    blocks.push(paragraphBlock(order.note.slice(0, 1800)));
  }

  return blocks.slice(0, 90);
}

// Repair a single order by adding blocks (without touching properties)
async function repairOrder(
  notion: Client,
  pageId: string,
  order: ShopifyOrder,
  dryRun: boolean
): Promise<boolean> {
  if (dryRun) {
    console.log(`  [DRY RUN] Would repair ${order.name} with ${buildPageBlocks(order).length} blocks`);
    return true;
  }

  try {
    const blocks = buildPageBlocks(order);

    // Just append blocks - don't delete existing (in case there's valuable content)
    await notion.blocks.children.append({
      block_id: pageId,
      children: blocks,
    });

    console.log(`  ✅ Repaired ${order.name} - added ${blocks.length} blocks`);
    return true;
  } catch (error: any) {
    console.error(`  ❌ Failed to repair ${order.name}:`, error.message);
    return false;
  }
}

async function main() {
  loadEnv();
  const env = getEnvConfig();

  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const fromDateArg = args.find(a => a.startsWith('--from-date='));
  const fromDate = fromDateArg ? fromDateArg.split('=')[1] : undefined;

  console.log('🔧 Repair Affected Orders Script');
  console.log(`   Mode: ${dryRun ? 'DRY RUN' : 'LIVE'}`);
  if (fromDate) console.log(`   From Date: ${fromDate}`);
  console.log('');

  const notion = new Client({ auth: env.notionToken, notionVersion: NOTION_VERSION });
  const dataSourceId = await resolveDataSourceId(notion, env);

  // Step 1: Find damaged orders
  const damagedOrders = await findDamagedOrders(notion, dataSourceId, fromDate);

  if (damagedOrders.length === 0) {
    console.log('\n✅ No damaged orders found! Nothing to repair.');
    return;
  }

  console.log(`\n📋 Found ${damagedOrders.length} damaged orders to repair:`);
  for (const order of damagedOrders) {
    console.log(`   - ${order.orderName} (${order.blockCount} blocks)`);
  }

  // Step 2: Repair each damaged order
  console.log('\n🔧 Starting repairs...');
  let repaired = 0;
  let failed = 0;

  for (const damaged of damagedOrders) {
    console.log(`\n📦 Fetching ${damaged.orderName} from Shopify...`);

    const shopifyOrder = await fetchOrderFromShopify(env, damaged.orderId);
    if (!shopifyOrder) {
      console.log(`  ⚠️  Could not fetch from Shopify - skipping`);
      failed++;
      continue;
    }

    const success = await repairOrder(notion, damaged.pageId, shopifyOrder, dryRun);
    if (success) {
      repaired++;
    } else {
      failed++;
    }

    await delay(200); // Rate limit
  }

  console.log('\n' + '='.repeat(50));
  console.log('📊 Repair Summary:');
  console.log(`   ✅ Repaired: ${repaired}`);
  console.log(`   ❌ Failed: ${failed}`);
  console.log(`   📦 Total: ${damagedOrders.length}`);
  if (dryRun) {
    console.log('\n⚠️  This was a DRY RUN. Run without --dry-run to apply changes.');
  }
}

main().catch(err => {
  console.error('❌ Fatal error:', err);
  process.exit(1);
});
