#!/usr/bin/env tsx
import { Client } from '@notionhq/client';
import {
  getEnvConfig,
  resolveDataSourceId,
  NOTION_VERSION,
  SHOPIFY_API_VERSION,
} from '../lib/shopifyNotionSync.js';

// Copy the exact same helper functions from backfill script
function normalizeStatus(status: string): string {
  return status
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function sanitizeString(str: string | null | undefined): string | null {
  if (!str) return null;
  return str.replace(/[\u2060\u200B\u200C\u200D\uFEFF]/g, '').trim();
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
  const raw = line.title || line.source || line.code || line.carrier_identifier || null;
  return sanitizeString(raw);
}

function buildSelectProperty(shopifyValue: string | null | undefined, existingValue: any, defaultValue: string) {
  if (shopifyValue) {
    return { select: { name: normalizeStatus(shopifyValue) } };
  }
  if (existingValue?.select?.name) {
    return { select: { name: existingValue.select.name } };
  }
  return { select: { name: defaultValue } };
}

async function main() {
  const env = getEnvConfig();
  const notion = new Client({ auth: env.notionToken, notionVersion: NOTION_VERSION });
  const dataSourceId = await resolveDataSourceId(notion, env);

  // Get an older order that should have blank fields (CC5880 for example)
  console.log('=== STEP 1: Query Notion for order ===');
  const response: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 1,
    filter: {
      property: 'ORDER',
      title: { equals: '#CC5880' },
    },
  } as any);

  const page = response.results?.[0];
  if (!page) {
    console.log('Order not found');
    return;
  }

  console.log('Page ID:', page.id);
  const existingProps = page.properties || {};

  console.log('\nCurrent Notion properties:');
  console.log('  Order ID:', existingProps['Order ID']?.number);
  console.log('  Channel:', existingProps.Channel?.select?.name ?? '(blank)');
  console.log('  Payment Status:', existingProps['Payment Status']?.select?.name ?? '(blank)');
  console.log('  Fulfillment Status:', existingProps['Fulfillment Status']?.select?.name ?? '(blank)');
  console.log('  Delivery Status:', existingProps['Delivery Status']?.select?.name ?? '(blank)');
  console.log('  Delivery method:', existingProps['Delivery method']?.select?.name ?? '(blank)');

  const orderId = existingProps['Order ID']?.number;
  if (!orderId) {
    console.log('No Order ID found');
    return;
  }

  // Backfill check 1: needsUpdate in processOrder
  const needsUpdateCheck1 =
    !existingProps.Channel?.select?.name ||
    !existingProps['Payment Status']?.select?.name ||
    !existingProps['Fulfillment Status']?.select?.name ||
    !existingProps['Delivery Status']?.select?.name ||
    !existingProps['Delivery method']?.select?.name;

  console.log('\n=== STEP 2: Check if update needed (processOrder check) ===');
  console.log('needsUpdate (check 1):', needsUpdateCheck1);
  console.log('  !Channel:', !existingProps.Channel?.select?.name);
  console.log('  !Payment Status:', !existingProps['Payment Status']?.select?.name);
  console.log('  !Fulfillment Status:', !existingProps['Fulfillment Status']?.select?.name);
  console.log('  !Delivery Status:', !existingProps['Delivery Status']?.select?.name);
  console.log('  !Delivery method:', !existingProps['Delivery method']?.select?.name);

  if (!needsUpdateCheck1) {
    console.log('Would return early - no update needed');
    return;
  }

  // Fetch from Shopify
  console.log('\n=== STEP 3: Fetch order from Shopify ===');
  const shopifyResp = await fetch(
    `https://${env.storeDomain}/admin/api/${SHOPIFY_API_VERSION}/orders/${orderId}.json`,
    { headers: { 'X-Shopify-Access-Token': env.shopifyToken } }
  );

  if (!shopifyResp.ok) {
    console.log('Shopify fetch failed:', shopifyResp.status);
    return;
  }

  const { order } = await shopifyResp.json() as { order: any };
  console.log('Shopify order data:');
  console.log('  name:', order.name);
  console.log('  source_name:', order.source_name);
  console.log('  financial_status:', order.financial_status);
  console.log('  fulfillment_status:', order.fulfillment_status);
  console.log('  shipping_lines:', JSON.stringify(order.shipping_lines));
  console.log('  fulfillments:', order.fulfillments?.length || 0, 'fulfillments');

  // Backfill check 2: needsUpdate in updateOrderFields (THE PROBLEMATIC ONE)
  const derivedDeliveryMethod = deriveDeliveryMethod(order);
  const needsUpdateCheck2 =
    !existingProps.Channel?.select?.name ||
    !existingProps['Payment Status']?.select?.name ||
    !existingProps['Fulfillment Status']?.select?.name ||
    !existingProps['Delivery Status']?.select?.name ||
    (!existingProps['Delivery method']?.select?.name && derivedDeliveryMethod);

  console.log('\n=== STEP 4: Check if update needed (updateOrderFields check) ===');
  console.log('derivedDeliveryMethod:', derivedDeliveryMethod);
  console.log('needsUpdate (check 2):', needsUpdateCheck2);
  console.log('  !Channel:', !existingProps.Channel?.select?.name);
  console.log('  !Payment Status:', !existingProps['Payment Status']?.select?.name);
  console.log('  !Fulfillment Status:', !existingProps['Fulfillment Status']?.select?.name);
  console.log('  !Delivery Status:', !existingProps['Delivery Status']?.select?.name);
  console.log('  (!Delivery method && derivedMethod):', (!existingProps['Delivery method']?.select?.name && derivedDeliveryMethod));

  if (!needsUpdateCheck2) {
    console.log('\n❌ FOUND THE BUG! Check 2 fails but Check 1 passed!');
    console.log('The backfill would early return from updateOrderFields without updating');
    return;
  }

  // Build updates (same logic as backfill)
  console.log('\n=== STEP 5: Build updates object ===');
  const updates: Record<string, any> = {};

  if (!existingProps.Channel?.select?.name) {
    updates.Channel = buildSelectProperty(order.source_name, existingProps.Channel, 'Online Store');
    if (order.source_name) {
      updates.Channel = { select: { name: formatChannel(order.source_name) } };
    }
    console.log('  Setting Channel:', JSON.stringify(updates.Channel));
  }

  if (!existingProps['Payment Status']?.select?.name) {
    updates['Payment Status'] = buildSelectProperty(
      order.financial_status,
      existingProps['Payment Status'],
      'Unknown',
    );
    console.log('  Setting Payment Status:', JSON.stringify(updates['Payment Status']));
  }

  if (!existingProps['Fulfillment Status']?.select?.name) {
    updates['Fulfillment Status'] = buildSelectProperty(
      order.fulfillment_status,
      existingProps['Fulfillment Status'],
      'unfulfilled',
    );
    console.log('  Setting Fulfillment Status:', JSON.stringify(updates['Fulfillment Status']));
  }

  if (!existingProps['Delivery Status']?.select?.name) {
    const deliveryStatus = order.fulfillment_status
      ? normalizeStatus(order.fulfillment_status)
      : order.fulfillments?.[0]?.shipment_status
        ? normalizeStatus(order.fulfillments[0].shipment_status)
        : 'pending';
    updates['Delivery Status'] = { select: { name: deliveryStatus } };
    console.log('  Setting Delivery Status:', JSON.stringify(updates['Delivery Status']));
  }

  if (!existingProps['Delivery method']?.select?.name) {
    const deliveryMethod = deriveDeliveryMethod(order);
    if (deliveryMethod) {
      updates['Delivery method'] = { select: { name: deliveryMethod } };
    } else {
      updates['Delivery method'] = { select: { name: 'Standard Shipping' } };
    }
    console.log('  Setting Delivery method:', JSON.stringify(updates['Delivery method']));
  }

  console.log('\nFull updates object:', JSON.stringify(updates, null, 2));

  if (Object.keys(updates).length === 0) {
    console.log('No updates to make!');
    return;
  }

  // Perform update
  console.log('\n=== STEP 6: Call notion.pages.update ===');
  try {
    const result = await notion.pages.update({
      page_id: page.id,
      properties: updates,
    });
    console.log('✅ Update succeeded!');
    console.log('Response has properties:', Object.keys((result as any).properties || {}));
  } catch (error: any) {
    console.error('❌ Update failed:', error.message);
    console.error('Error code:', error.code);
    console.error('Error body:', JSON.stringify(error.body, null, 2));
    return;
  }

  // Verify
  console.log('\n=== STEP 7: Verify update persisted ===');
  await new Promise(r => setTimeout(r, 2000));

  const verify: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 1,
    filter: {
      property: 'ORDER',
      title: { equals: '#CC5880' },
    },
  } as any);

  const verifyPage = verify.results?.[0];
  console.log('After update:');
  console.log('  Channel:', verifyPage?.properties?.Channel?.select?.name ?? '(blank)');
  console.log('  Payment Status:', verifyPage?.properties?.['Payment Status']?.select?.name ?? '(blank)');
  console.log('  Fulfillment Status:', verifyPage?.properties?.['Fulfillment Status']?.select?.name ?? '(blank)');
  console.log('  Delivery Status:', verifyPage?.properties?.['Delivery Status']?.select?.name ?? '(blank)');
  console.log('  Delivery method:', verifyPage?.properties?.['Delivery method']?.select?.name ?? '(blank)');
}

main().catch(console.error);
