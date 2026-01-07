import { getEnvConfig, SHOPIFY_API_VERSION } from '../lib/shopifyNotionSync.js';

async function main() {
  const env = getEnvConfig();
  const url = `https://${env.storeDomain}/admin/api/${SHOPIFY_API_VERSION}/orders.json?limit=1&status=any`;
  const resp = await fetch(url, { headers: { 'X-Shopify-Access-Token': env.shopifyToken } });
  const data = await resp.json() as { orders: any[] };
  const order = data.orders?.[0];
  if (order) {
    console.log('Order:', order.name);
    console.log('fulfillment_status:', JSON.stringify(order.fulfillment_status));
    console.log('financial_status:', JSON.stringify(order.financial_status));
    console.log('source_name:', JSON.stringify(order.source_name));
    console.log('shipping_lines:', JSON.stringify(order.shipping_lines?.slice(0,1)));
  }
}

main();
