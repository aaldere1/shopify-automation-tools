#!/usr/bin/env tsx
/**
 * Debug script to see what updates would be applied
 */
import { Client } from '@notionhq/client';
import {
  getEnvConfig,
  resolveDataSourceId,
  NOTION_VERSION,
  SHOPIFY_API_VERSION,
} from '../lib/shopifyNotionSync.js';

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

function deriveDeliveryMethod(order: any): string | null {
  const line = order.shipping_lines?.[0];
  if (!line) return null;
  return line.title || line.source || line.code || line.carrier_identifier || null;
}

async function main() {
  const env = getEnvConfig();
  const notion = new Client({ auth: env.notionToken, notionVersion: NOTION_VERSION });
  const dataSourceId = await resolveDataSourceId(notion, env);

  // Get first 3 orders from Notion
  const response: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 3,
  } as any);

  for (const page of response.results || []) {
    const props = page.properties || {};
    const orderId = props['Order ID']?.number;
    const orderName = props.ORDER?.title?.[0]?.plain_text || 'Unknown';

    console.log(`\n=== ${orderName} (ID: ${orderId}) ===`);
    console.log('Current Notion props:');
    console.log('  Channel:', JSON.stringify(props.Channel));
    console.log('  Payment Status:', JSON.stringify(props['Payment Status']));
    console.log('  Fulfillment Status:', JSON.stringify(props['Fulfillment Status']));
    console.log('  Delivery Status:', JSON.stringify(props['Delivery Status']));
    console.log('  Delivery method:', JSON.stringify(props['Delivery method']));

    if (!orderId) continue;

    // Fetch from Shopify
    const url = `https://${env.storeDomain}/admin/api/${SHOPIFY_API_VERSION}/orders/${orderId}.json`;
    const resp = await fetch(url, {
      headers: { 'X-Shopify-Access-Token': env.shopifyToken },
    });

    if (!resp.ok) {
      console.log('  Shopify fetch failed:', resp.status);
      continue;
    }

    const data = await resp.json() as { order: any };
    const order = data.order;

    console.log('\nShopify data:');
    console.log('  source_name:', JSON.stringify(order.source_name));
    console.log('  financial_status:', JSON.stringify(order.financial_status));
    console.log('  fulfillment_status:', JSON.stringify(order.fulfillment_status));
    console.log('  shipping_lines[0].title:', JSON.stringify(order.shipping_lines?.[0]?.title));
    console.log('  fulfillments[0].shipment_status:', JSON.stringify(order.fulfillments?.[0]?.shipment_status));

    // What would be updated
    console.log('\nWould update:');

    const existingProps = props;
    const updates: Record<string, any> = {};

    if (!existingProps.Channel?.select?.name) {
      updates.Channel = { select: { name: formatChannel(order.source_name) } };
      console.log('  Channel ->', updates.Channel.select.name);
    }

    if (!existingProps['Payment Status']?.select?.name) {
      const val = order.financial_status
        ? normalizeStatus(order.financial_status)
        : 'Unknown';
      updates['Payment Status'] = { select: { name: val } };
      console.log('  Payment Status ->', val);
    }

    if (!existingProps['Fulfillment Status']?.select?.name) {
      const val = order.fulfillment_status
        ? normalizeStatus(order.fulfillment_status)
        : 'unfulfilled';
      updates['Fulfillment Status'] = { select: { name: val } };
      console.log('  Fulfillment Status ->', val);
    }

    if (!existingProps['Delivery Status']?.select?.name) {
      let val = 'pending';
      if (order.fulfillment_status) {
        val = normalizeStatus(order.fulfillment_status);
      } else if (order.fulfillments?.[0]?.shipment_status) {
        val = normalizeStatus(order.fulfillments[0].shipment_status);
      }
      updates['Delivery Status'] = { select: { name: val } };
      console.log('  Delivery Status ->', val);
    }

    if (!existingProps['Delivery method']?.select?.name) {
      const method = deriveDeliveryMethod(order);
      const val = method || 'Standard Shipping';
      updates['Delivery method'] = { select: { name: val } };
      console.log('  Delivery method ->', val);
    }

    if (Object.keys(updates).length === 0) {
      console.log('  (nothing to update)');
    }
  }
}

main().catch(console.error);
