#!/usr/bin/env tsx
import { Client } from '@notionhq/client';
import { getEnvConfig, resolveDataSourceId, NOTION_VERSION } from '../lib/shopifyNotionSync.js';

async function main() {
  const env = getEnvConfig();
  const notion = new Client({ auth: env.notionToken, notionVersion: NOTION_VERSION });
  const dataSourceId = await resolveDataSourceId(notion, env);

  // Check older orders that shouldn't have been manually touched
  const orders = ['#CC5870', '#CC5860', '#CC5850', '#CC5840', '#CC5830', '#CC5820', '#CC5810', '#CC5800'];

  for (const orderName of orders) {
    const response: any = await notion.dataSources.query({
      data_source_id: dataSourceId,
      page_size: 1,
      filter: { property: 'ORDER', title: { equals: orderName } },
    } as any);

    const page = response.results?.[0];
    if (!page) {
      console.log(`${orderName}: NOT FOUND`);
      continue;
    }

    const props = page.properties || {};
    const f = props['Fulfillment Status']?.select?.name ?? '(blank)';
    const d = props['Delivery Status']?.select?.name ?? '(blank)';
    const m = props['Delivery method']?.select?.name ?? '(blank)';
    const c = props.Channel?.select?.name ?? '(blank)';

    console.log(`${orderName}: F=${f}, D=${d}, M=${m}, C=${c}`);
  }
}

main().catch(console.error);
