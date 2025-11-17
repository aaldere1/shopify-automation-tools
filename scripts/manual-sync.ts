import { runShopifyNotionSync } from '../lib/shopifyNotionSync.js';

async function main() {
  try {
    const result = await runShopifyNotionSync();
    console.log('✅ Sync complete:', result);
    process.exit(0);
  } catch (error) {
    console.error('❌ Sync failed:', error);
    process.exit(1);
  }
}

void main();

