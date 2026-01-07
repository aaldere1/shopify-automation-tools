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

  // Find CC5890
  const response: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 1,
    filter: {
      property: 'ORDER',
      title: { equals: '#CC5890' },
    },
  } as any);

  const page = response.results?.[0];
  if (!page) {
    console.log('Order not found');
    return;
  }

  console.log('Found page:', page.id);
  console.log('Current properties:');
  console.log('  Fulfillment Status:', page.properties?.['Fulfillment Status']?.select?.name ?? '(blank)');
  console.log('  Delivery Status:', page.properties?.['Delivery Status']?.select?.name ?? '(blank)');
  console.log('  Delivery method:', page.properties?.['Delivery method']?.select?.name ?? '(blank)');
  console.log('  Channel:', page.properties?.Channel?.select?.name ?? '(blank)');

  // Try to update
  console.log('\nAttempting update...');
  const updates = {
    'Fulfillment Status': { select: { name: 'unfulfilled' } },
    'Delivery Status': { select: { name: 'pending' } },
    'Delivery method': { select: { name: 'Standard Shipping' } },
    'Channel': { select: { name: 'Online Store' } },
  };

  try {
    const result = await notion.pages.update({
      page_id: page.id,
      properties: updates,
    });
    console.log('✅ Update call succeeded');
    console.log('Response properties:', JSON.stringify((result as any).properties?.Channel, null, 2));
  } catch (error: any) {
    console.error('❌ Update failed:', error.message);
    console.error('Error code:', error.code);
    console.error('Error body:', JSON.stringify(error.body, null, 2));
    return;
  }

  // Wait a moment and re-query
  console.log('\nWaiting 2 seconds and re-querying...');
  await new Promise(r => setTimeout(r, 2000));

  const verify: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 1,
    filter: {
      property: 'ORDER',
      title: { equals: '#CC5890' },
    },
  } as any);

  const verifyPage = verify.results?.[0];
  console.log('After update:');
  console.log('  Fulfillment Status:', verifyPage?.properties?.['Fulfillment Status']?.select?.name ?? '(blank)');
  console.log('  Delivery Status:', verifyPage?.properties?.['Delivery Status']?.select?.name ?? '(blank)');
  console.log('  Delivery method:', verifyPage?.properties?.['Delivery method']?.select?.name ?? '(blank)');
  console.log('  Channel:', verifyPage?.properties?.Channel?.select?.name ?? '(blank)');
}

main().catch(console.error);
