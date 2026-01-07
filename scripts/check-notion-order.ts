import { Client } from '@notionhq/client';
import { getEnvConfig, resolveDataSourceId, NOTION_VERSION } from '../lib/shopifyNotionSync.js';

async function main() {
  const env = getEnvConfig();
  const notion = new Client({ auth: env.notionToken, notionVersion: NOTION_VERSION });
  const dataSourceId = await resolveDataSourceId(notion, env);

  // Query for first few orders
  const response: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 3,
  } as any);

  console.log('Checking first 3 orders in Notion:\n');

  for (const page of response.results || []) {
    const props = page.properties || {};
    console.log('Order:', props.ORDER?.title?.[0]?.plain_text);
    console.log('  Order ID:', props['Order ID']?.number);
    console.log('  Fulfillment Status:', props['Fulfillment Status']?.select?.name ?? '(blank)');
    console.log('  Payment Status:', props['Payment Status']?.select?.name ?? '(blank)');
    console.log('  Delivery Status:', props['Delivery Status']?.select?.name ?? '(blank)');
    console.log('  Delivery method:', props['Delivery method']?.select?.name ?? '(blank)');
    console.log('  Channel:', props.Channel?.select?.name ?? '(blank)');
    console.log('');
  }
}

main().catch(console.error);
