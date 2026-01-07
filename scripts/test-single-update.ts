#!/usr/bin/env tsx
/**
 * Test updating a single order to see if it works
 */
import { Client } from '@notionhq/client';
import {
  getEnvConfig,
  resolveDataSourceId,
  NOTION_VERSION,
} from '../lib/shopifyNotionSync.js';

async function main() {
  const env = getEnvConfig();
  const notion = new Client({ auth: env.notionToken, notionVersion: NOTION_VERSION });
  const dataSourceId = await resolveDataSourceId(notion, env);

  // Get first order from Notion
  const response: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 1,
  } as any);

  const page = response.results?.[0];
  if (!page) {
    console.log('No orders found');
    return;
  }

  const pageId = page.id;
  const orderName = page.properties?.ORDER?.title?.[0]?.plain_text || 'Unknown';
  console.log(`Testing update on ${orderName} (page ID: ${pageId})`);

  // Try to update
  const updates = {
    'Channel': { select: { name: 'Online Store' } },
    'Fulfillment Status': { select: { name: 'Fulfilled' } },
    'Delivery Status': { select: { name: 'Fulfilled' } },
    'Delivery method': { select: { name: 'Standard Shipping' } },
  };

  console.log('Attempting update with:', JSON.stringify(updates, null, 2));

  try {
    const result = await notion.pages.update({
      page_id: pageId,
      properties: updates,
    });
    console.log('✅ Update succeeded!');
    console.log('Result properties:', JSON.stringify((result as any).properties?.Channel, null, 2));
  } catch (error: any) {
    console.error('❌ Update failed:', error.message);
    console.error('Error code:', error.code);
    console.error('Full error:', error);
  }

  // Check the page again
  console.log('\nRe-querying to verify...');
  const verify: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 1,
    filter: {
      property: 'Order ID',
      number: { equals: page.properties?.['Order ID']?.number },
    },
  } as any);

  const updatedPage = verify.results?.[0];
  if (updatedPage) {
    console.log('After update:');
    console.log('  Channel:', JSON.stringify(updatedPage.properties?.Channel?.select));
    console.log('  Fulfillment Status:', JSON.stringify(updatedPage.properties?.['Fulfillment Status']?.select));
    console.log('  Delivery Status:', JSON.stringify(updatedPage.properties?.['Delivery Status']?.select));
    console.log('  Delivery method:', JSON.stringify(updatedPage.properties?.['Delivery method']?.select));
  }
}

main().catch(console.error);
