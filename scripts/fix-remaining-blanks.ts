#!/usr/bin/env tsx
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

function deriveDeliveryMethod(order: any): string | null {
  const line = order.shipping_lines?.[0];
  if (!line) return null;
  return line.title || line.source || line.code || line.carrier_identifier || null;
}

async function main() {
  const env = getEnvConfig();
  const notion = new Client({ auth: env.notionToken, notionVersion: NOTION_VERSION });
  const dataSourceId = await resolveDataSourceId(notion, env);

  // Fix CC4022 (missing Delivery method)
  console.log('=== Fixing CC4022 (Order ID: 5175774674990) ===');

  // Get page ID
  const resp1: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 1,
    filter: { property: 'Order ID', number: { equals: 5175774674990 } },
  } as any);

  const page1 = resp1.results?.[0];
  if (page1) {
    // Fetch from Shopify
    const shopifyResp1 = await fetch(
      `https://${env.storeDomain}/admin/api/${SHOPIFY_API_VERSION}/orders/5175774674990.json`,
      { headers: { 'X-Shopify-Access-Token': env.shopifyToken } }
    );
    const { order: order1 } = await shopifyResp1.json() as { order: any };

    const deliveryMethod = deriveDeliveryMethod(order1) || 'Standard Shipping';
    console.log(`  Will set Delivery method to: "${deliveryMethod}"`);

    try {
      await notion.pages.update({
        page_id: page1.id,
        properties: {
          'Delivery method': { select: { name: deliveryMethod } },
        },
      });
      console.log('  ✅ Updated successfully!');
    } catch (error: any) {
      console.error('  ❌ Failed:', error.message);
    }
  }

  // Fix CC5558 (missing Payment Status)
  console.log('\n=== Fixing CC5558 (Order ID: 5796501159982) ===');

  const resp2: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 1,
    filter: { property: 'Order ID', number: { equals: 5796501159982 } },
  } as any);

  const page2 = resp2.results?.[0];
  if (page2) {
    // Fetch from Shopify
    const shopifyResp2 = await fetch(
      `https://${env.storeDomain}/admin/api/${SHOPIFY_API_VERSION}/orders/5796501159982.json`,
      { headers: { 'X-Shopify-Access-Token': env.shopifyToken } }
    );
    const { order: order2 } = await shopifyResp2.json() as { order: any };

    const paymentStatus = order2.financial_status
      ? normalizeStatus(order2.financial_status)
      : 'Unknown';
    console.log(`  Will set Payment Status to: "${paymentStatus}"`);

    try {
      await notion.pages.update({
        page_id: page2.id,
        properties: {
          'Payment Status': { select: { name: paymentStatus } },
        },
      });
      console.log('  ✅ Updated successfully!');
    } catch (error: any) {
      console.error('  ❌ Failed:', error.message);
    }
  }

  // Verify
  console.log('\n=== Verifying fixes ===');

  const verify1: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 1,
    filter: { property: 'Order ID', number: { equals: 5175774674990 } },
  } as any);
  console.log('CC4022 Delivery method:', verify1.results?.[0]?.properties?.['Delivery method']?.select?.name ?? '(blank)');

  const verify2: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 1,
    filter: { property: 'Order ID', number: { equals: 5796501159982 } },
  } as any);
  console.log('CC5558 Payment Status:', verify2.results?.[0]?.properties?.['Payment Status']?.select?.name ?? '(blank)');
}

main().catch(console.error);
