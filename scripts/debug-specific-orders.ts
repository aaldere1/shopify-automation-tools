#!/usr/bin/env tsx
import { Client } from '@notionhq/client';
import {
  getEnvConfig,
  resolveDataSourceId,
  NOTION_VERSION,
  SHOPIFY_API_VERSION,
} from '../lib/shopifyNotionSync.js';

async function main() {
  const env = getEnvConfig();
  const notion = new Client({ auth: env.notionToken, notionVersion: NOTION_VERSION });
  const dataSourceId = await resolveDataSourceId(notion, env);

  // Check specific problematic orders
  const orderIds = [5175774674990, 5796501159982]; // CC4022 and CC5558

  for (const orderId of orderIds) {
    console.log(`\n=== Order ID: ${orderId} ===`);

    // Get from Notion
    const notionResp: any = await notion.dataSources.query({
      data_source_id: dataSourceId,
      page_size: 1,
      filter: {
        property: 'Order ID',
        number: { equals: orderId },
      },
    } as any);

    const page = notionResp.results?.[0];
    if (!page) {
      console.log('NOT FOUND in Notion');
      continue;
    }

    const props = page.properties || {};
    console.log('Notion properties:');
    console.log('  Order:', props.ORDER?.title?.[0]?.plain_text);
    console.log('  Fulfillment Status:', JSON.stringify(props['Fulfillment Status']?.select));
    console.log('  Payment Status:', JSON.stringify(props['Payment Status']?.select));
    console.log('  Delivery method:', JSON.stringify(props['Delivery method']?.select));
    console.log('  Delivery Status:', JSON.stringify(props['Delivery Status']?.select));
    console.log('  Channel:', JSON.stringify(props.Channel?.select));

    // Fetch from Shopify
    const url = `https://${env.storeDomain}/admin/api/${SHOPIFY_API_VERSION}/orders/${orderId}.json`;
    const resp = await fetch(url, {
      headers: { 'X-Shopify-Access-Token': env.shopifyToken },
    });

    if (!resp.ok) {
      console.log('Shopify fetch failed:', resp.status);
      continue;
    }

    const data = await resp.json() as { order: any };
    const order = data.order;

    console.log('\nShopify data:');
    console.log('  financial_status:', order.financial_status);
    console.log('  fulfillment_status:', order.fulfillment_status);
    console.log('  source_name:', order.source_name);
    console.log('  shipping_lines[0]:', order.shipping_lines?.[0] ? {
      title: order.shipping_lines[0].title,
      code: order.shipping_lines[0].code,
      source: order.shipping_lines[0].source,
    } : null);
  }
}

main().catch(console.error);
