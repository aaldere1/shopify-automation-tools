#!/usr/bin/env tsx
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

  // Check orders from different ranges
  const response: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 20,
    sorts: [{ property: 'Date', direction: 'descending' }],
  } as any);

  console.log('Checking 20 most recent orders:\n');

  for (const page of response.results || []) {
    const props = page.properties || {};
    const orderName = props.ORDER?.title?.[0]?.plain_text || 'Unknown';
    const fulfillment = props['Fulfillment Status']?.select?.name ?? '(blank)';
    const delivery = props['Delivery Status']?.select?.name ?? '(blank)';
    const method = props['Delivery method']?.select?.name ?? '(blank)';
    const channel = props.Channel?.select?.name ?? '(blank)';
    const payment = props['Payment Status']?.select?.name ?? '(blank)';

    const allBlank = fulfillment === '(blank)' && delivery === '(blank)' && method === '(blank)' && channel === '(blank)';
    const status = allBlank ? '❌' : (fulfillment === '(blank)' || delivery === '(blank)' || method === '(blank)' ? '⚠️' : '✅');

    console.log(`${status} ${orderName}: F=${fulfillment}, D=${delivery}, M=${method}, C=${channel}, P=${payment}`);
  }

  // Also check some older orders
  console.log('\n--- Checking older orders (page 2) ---\n');

  const response2: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 10,
    start_cursor: response.next_cursor,
    sorts: [{ property: 'Date', direction: 'descending' }],
  } as any);

  for (const page of response2.results || []) {
    const props = page.properties || {};
    const orderName = props.ORDER?.title?.[0]?.plain_text || 'Unknown';
    const fulfillment = props['Fulfillment Status']?.select?.name ?? '(blank)';
    const delivery = props['Delivery Status']?.select?.name ?? '(blank)';
    const method = props['Delivery method']?.select?.name ?? '(blank)';
    const channel = props.Channel?.select?.name ?? '(blank)';

    const allBlank = fulfillment === '(blank)' && delivery === '(blank)' && method === '(blank)' && channel === '(blank)';
    const status = allBlank ? '❌' : (fulfillment === '(blank)' || delivery === '(blank)' || method === '(blank)' ? '⚠️' : '✅');

    console.log(`${status} ${orderName}: F=${fulfillment}, D=${delivery}, M=${method}, C=${channel}`);
  }
}

main().catch(console.error);
