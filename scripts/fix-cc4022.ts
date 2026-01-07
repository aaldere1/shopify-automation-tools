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

  // Get order from Shopify
  const shopifyResp = await fetch(
    `https://${env.storeDomain}/admin/api/${SHOPIFY_API_VERSION}/orders/5175774674990.json`,
    { headers: { 'X-Shopify-Access-Token': env.shopifyToken } }
  );
  const { order } = await shopifyResp.json() as { order: any };

  console.log('Raw shipping_lines[0].title:');
  const title = order.shipping_lines?.[0]?.title;
  console.log('  String:', JSON.stringify(title));
  console.log('  Length:', title?.length);
  console.log('  Char codes:', title?.split('').map((c: string) => c.charCodeAt(0)));

  // Get page ID
  const resp: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 1,
    filter: { property: 'Order ID', number: { equals: 5175774674990 } },
  } as any);

  const page = resp.results?.[0];
  if (!page) {
    console.log('Page not found');
    return;
  }

  // Clean the title - remove invisible Unicode characters
  const cleanTitle = title
    ? title.replace(/[\u2060\u200B\u200C\u200D\uFEFF]/g, '').trim()
    : 'Standard Shipping';

  console.log('\nCleaned title:', JSON.stringify(cleanTitle));

  // Update with cleaned title
  try {
    await notion.pages.update({
      page_id: page.id,
      properties: {
        'Delivery method': { select: { name: cleanTitle } },
      },
    });
    console.log('✅ Updated successfully!');
  } catch (error: any) {
    console.error('❌ Failed:', error.message);
    console.error('Error body:', error.body);
  }

  // Verify
  const verify: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 1,
    filter: { property: 'Order ID', number: { equals: 5175774674990 } },
  } as any);
  console.log('\nVerification:');
  console.log('  Delivery method:', verify.results?.[0]?.properties?.['Delivery method']?.select?.name ?? '(blank)');
}

main().catch(console.error);
