#!/usr/bin/env tsx
import { Client } from '@notionhq/client';
import {
  getEnvConfig,
  resolveDataSourceId,
  NOTION_VERSION,
  SHOPIFY_API_VERSION,
} from '../lib/shopifyNotionSync.js';

// Suppress Notion client conflict_error warnings (they're handled by retry logic)
const originalWarn = console.warn;
console.warn = (...args: any[]) => {
  const message = args[0]?.toString() || '';
  // Skip conflict_error warnings from Notion client - they're handled gracefully
  if (message.includes('conflict_error') || message.includes('@notionhq/client warn')) {
    return; // Suppress these warnings
  }
  originalWarn.apply(console, args);
};

const BATCH_SIZE = 100; // Increased batch size
const CONCURRENT_REQUESTS = 3; // Process 3 orders concurrently (reduced to minimize conflicts)
const NOTION_RATE_LIMIT = 3; // 3 requests per second (180/minute) - conservative Notion limit
const SHOPIFY_RATE_LIMIT = 2; // 2 requests per second (120/minute) - conservative Shopify limit

// Rate limiter class with proper concurrency and rate limiting
class RateLimiter {
  private queue: Array<{ fn: () => Promise<any>; resolve: (value: any) => void; reject: (error: any) => void }> = [];
  private running = 0;
  private maxConcurrent: number;
  private minDelay: number;
  private lastRequestTime = 0;

  constructor(maxConcurrent: number, requestsPerSecond: number) {
    this.maxConcurrent = maxConcurrent;
    this.minDelay = 1000 / requestsPerSecond;
  }

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push({ fn, resolve, reject });
      this.processQueue();
    });
  }

  private async processQueue() {
    if (this.running >= this.maxConcurrent || this.queue.length === 0) {
      return;
    }

    const item = this.queue.shift()!;
    this.running++;

    // Ensure minimum delay between requests
    const now = Date.now();
    const timeSinceLastRequest = now - this.lastRequestTime;
    if (timeSinceLastRequest < this.minDelay) {
      await delay(this.minDelay - timeSinceLastRequest);
    }
    this.lastRequestTime = Date.now();

    // Execute the function
    item.fn()
      .then((result) => {
        item.resolve(result);
      })
      .catch((error) => {
        item.reject(error);
      })
      .finally(() => {
        this.running--;
        this.processQueue();
      });
  }
}

const notionLimiter = new RateLimiter(CONCURRENT_REQUESTS, NOTION_RATE_LIMIT);
const shopifyLimiter = new RateLimiter(CONCURRENT_REQUESTS, SHOPIFY_RATE_LIMIT);

async function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchOrderFromShopify(env: ReturnType<typeof getEnvConfig>, orderId: number) {
  return shopifyLimiter.execute(async () => {
    const url = `https://${env.storeDomain}/admin/api/${SHOPIFY_API_VERSION}/orders/${orderId}.json`;
    const headers = {
      'X-Shopify-Access-Token': env.shopifyToken,
      'Content-Type': 'application/json',
    };

    try {
      const response = await fetch(url, { headers });
      if (!response.ok) {
        if (response.status === 404) {
          return null; // Order deleted
        }
        throw new Error(`Shopify fetch failed (${response.status})`);
      }
      const data = (await response.json()) as { order: any };
      return data.order;
    } catch (error) {
      console.error(`❌ Error fetching order ${orderId}:`, error);
      return null;
    }
  });
}

function buildSelectProperty(shopifyValue: string | null | undefined, existingValue: any, defaultValue: string) {
  // If Shopify has a value, use it
  if (shopifyValue) {
    return { select: { name: normalizeStatus(shopifyValue) } };
  }
  // If Notion already has a value, preserve it
  if (existingValue?.select?.name) {
    return { select: { name: existingValue.select.name } };
  }
  // Otherwise use default
  return { select: { name: defaultValue } };
}

function normalizeStatus(status: string): string {
  return status
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatChannel(sourceName: string | null | undefined): string {
  if (!sourceName) return 'Online Store';
  const normalized = sourceName.toLowerCase();
  switch (normalized) {
    case 'web':
      return 'Online Store';
    case 'pos':
      return 'POS';
    case 'shopify_draft_order':
      return 'Draft Order';
    default:
      return normalized.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  }
}

// Remove invisible Unicode characters that can cause issues with Notion select options
function sanitizeString(str: string | null | undefined): string | null {
  if (!str) return null;
  // Remove: WORD JOINER (2060), ZERO WIDTH SPACE (200B), ZERO WIDTH NON-JOINER (200C),
  // ZERO WIDTH JOINER (200D), BYTE ORDER MARK (FEFF)
  return str.replace(/[\u2060\u200B\u200C\u200D\uFEFF]/g, '').trim();
}

function deriveDeliveryMethod(order: any): string | null {
  const line = order.shipping_lines?.[0];
  if (!line) return null;
  const raw = line.title || line.source || line.code || line.carrier_identifier || null;
  return sanitizeString(raw);
}

async function updateOrderFields(
  notion: Client,
  pageId: string,
  order: any,
  existingProps: Record<string, any>,
) {
  return notionLimiter.execute(async () => {
    const needsUpdate =
      !existingProps.Channel?.select?.name ||
      !existingProps['Payment Status']?.select?.name ||
      !existingProps['Fulfillment Status']?.select?.name ||
      !existingProps['Delivery Status']?.select?.name ||
      (!existingProps['Delivery method']?.select?.name && deriveDeliveryMethod(order));

    if (!needsUpdate) {
      return false; // Already has all fields
    }

    const updates: Record<string, any> = {};

    // Only update fields that are missing
    if (!existingProps.Channel?.select?.name) {
      updates.Channel = buildSelectProperty(order.source_name, existingProps.Channel, 'Online Store');
      if (order.source_name) {
        updates.Channel = { select: { name: formatChannel(order.source_name) } };
      }
    }

    if (!existingProps['Payment Status']?.select?.name) {
      updates['Payment Status'] = buildSelectProperty(
        order.financial_status,
        existingProps['Payment Status'],
        'Unknown',
      );
    }

    if (!existingProps['Fulfillment Status']?.select?.name) {
      updates['Fulfillment Status'] = buildSelectProperty(
        order.fulfillment_status,
        existingProps['Fulfillment Status'],
        'unfulfilled',
      );
    }

    if (!existingProps['Delivery Status']?.select?.name) {
      const deliveryStatus = order.fulfillment_status
        ? normalizeStatus(order.fulfillment_status)
        : order.fulfillments?.[0]?.shipment_status
          ? normalizeStatus(order.fulfillments[0].shipment_status)
          : 'pending';
      updates['Delivery Status'] = { select: { name: deliveryStatus } };
    }

    if (!existingProps['Delivery method']?.select?.name) {
      const deliveryMethod = deriveDeliveryMethod(order);
      if (deliveryMethod) {
        updates['Delivery method'] = { select: { name: deliveryMethod } };
      } else {
        updates['Delivery method'] = { select: { name: 'Standard Shipping' } };
      }
    }

    if (Object.keys(updates).length === 0) {
      return false;
    }

    // Retry logic for conflict errors (409) - these are common with concurrent updates
    let retries = 5;
    let lastError: any = null;
    while (retries > 0) {
      try {
        await notion.pages.update({
          page_id: pageId,
          properties: updates,
        });
        return true;
      } catch (error: any) {
        lastError = error;
        // Retry conflict errors with exponential backoff
        if (error.code === 'conflict_error' && retries > 1) {
          retries--;
          const backoffMs = Math.min(1000 * Math.pow(2, 5 - retries), 5000); // 1s, 2s, 4s, 5s, 5s
          await delay(backoffMs);
          continue;
        }
        // If it's a conflict error but we're out of retries, it's likely a real conflict
        // (e.g., page being edited in Notion UI). Skip it silently.
        if (error.code === 'conflict_error') {
          return false; // Skip this update, don't treat as error
        }
        throw error; // Re-throw if not a conflict error
      }
    }

    // If we exhausted retries on a conflict, just skip it
    if (lastError?.code === 'conflict_error') {
      return false;
    }
    throw lastError;
  });
}

async function processOrder(
  notion: Client,
  env: ReturnType<typeof getEnvConfig>,
  page: any,
): Promise<{ updated: boolean; skipped: boolean; error: boolean }> {
  try {
    const orderId = page.properties?.['Order ID']?.number;
    if (!orderId) {
      return { updated: false, skipped: true, error: false };
    }

    const existingProps = page.properties || {};
    const needsUpdate =
      !existingProps.Channel?.select?.name ||
      !existingProps['Payment Status']?.select?.name ||
      !existingProps['Fulfillment Status']?.select?.name ||
      !existingProps['Delivery Status']?.select?.name ||
      !existingProps['Delivery method']?.select?.name;

    if (!needsUpdate) {
      return { updated: false, skipped: true, error: false };
    }

    // Fetch order from Shopify
    const order = await fetchOrderFromShopify(env, orderId);
    if (!order) {
      return { updated: false, skipped: true, error: false };
    }

    // Update missing fields
    const updated = await updateOrderFields(notion, page.id, order, existingProps);
    if (updated) {
      process.stdout.write(`✅ Updated order #${order.name || orderId}  `);
      return { updated: true, skipped: false, error: false };
    } else {
      return { updated: false, skipped: true, error: false };
    }
  } catch (error: any) {
    // Don't log conflict errors - they're handled gracefully with retries
    if (error?.code !== 'conflict_error') {
      console.error(`\n❌ Error processing order:`, error);
    }
    // Treat conflict errors as skipped (not errors) since we retry them
    if (error?.code === 'conflict_error') {
      return { updated: false, skipped: true, error: false };
    }
    return { updated: false, skipped: false, error: true };
  }
}

async function main() {
  console.log('🚀 Starting optimized backfill of existing Notion orders');
  console.log(`📦 Batch size: ${BATCH_SIZE} orders`);
  console.log(`⚡ Concurrent requests: ${CONCURRENT_REQUESTS}`);
  console.log(`🚦 Notion rate limit: ${NOTION_RATE_LIMIT} req/sec`);
  console.log(`🚦 Shopify rate limit: ${SHOPIFY_RATE_LIMIT} req/sec\n`);

  const env = getEnvConfig();
  const notion = new Client({ auth: env.notionToken, notionVersion: NOTION_VERSION });
  const dataSourceId = await resolveDataSourceId(notion, env);

  let cursor: string | undefined;
  let totalProcessed = 0;
  let totalUpdated = 0;
  let totalSkipped = 0;
  let totalErrors = 0;
  const startTime = Date.now();

  do {
    try {
      const queryBody: any = {
        data_source_id: dataSourceId,
        page_size: BATCH_SIZE,
        sorts: [{ property: 'Date', direction: 'descending' }],
      };
      if (cursor) {
        queryBody.start_cursor = cursor;
      }

      const response: any = await notion.dataSources.query(queryBody);
      const pages = response.results || [];

      if (pages.length === 0) {
        break;
      }

      console.log(`\n📦 Processing batch: ${totalProcessed + 1} to ${totalProcessed + pages.length}`);

      // Process orders in parallel - rate limiters handle concurrency and rate limiting
      const results = await Promise.all(
        pages.map((page: any) => processOrder(notion, env, page))
      );

      // Count results
      for (const result of results) {
        totalProcessed++;
        if (result.updated) totalUpdated++;
        if (result.skipped) totalSkipped++;
        if (result.error) totalErrors++;
      }

      cursor = response.has_more ? response.next_cursor : undefined;

      if (cursor) {
        console.log(`\n✅ Batch complete. Processed: ${totalProcessed} | Updated: ${totalUpdated} | Skipped: ${totalSkipped}`);
      }
    } catch (error) {
      console.error(`\n❌ Batch error:`, error);
      totalErrors++;
      await delay(1000); // Brief delay on error
    }
  } while (cursor);

  const duration = ((Date.now() - startTime) / 1000 / 60).toFixed(1);
  console.log('\n' + '='.repeat(60));
  console.log('📊 BACKFILL COMPLETE');
  console.log('='.repeat(60));
  console.log(`⏱️  Total time: ${duration} minutes`);
  console.log(`📦 Total processed: ${totalProcessed}`);
  console.log(`✅ Updated: ${totalUpdated}`);
  console.log(`⏭️  Skipped (already complete): ${totalSkipped}`);
  console.log(`❌ Errors: ${totalErrors}`);
  console.log(`⚡ Average speed: ${((totalProcessed / (Date.now() - startTime)) * 1000 * 60).toFixed(1)} orders/minute`);
  console.log('='.repeat(60));
}

main().catch((error) => {
  console.error('💥 Fatal error:', error);
  process.exit(1);
});

