#!/usr/bin/env tsx
import { runShopifyNotionSync } from '../lib/shopifyNotionSync.js';

const DATE_RANGES = [
  { min: '2018-01-01T00:00:00Z', max: '2019-01-01T00:00:00Z', label: '2018' },
  { min: '2019-01-01T00:00:00Z', max: '2020-01-01T00:00:00Z', label: '2019' },
  { min: '2020-01-01T00:00:00Z', max: '2021-01-01T00:00:00Z', label: '2020' },
  { min: '2021-01-01T00:00:00Z', max: '2022-01-01T00:00:00Z', label: '2021' },
  { min: '2022-01-01T00:00:00Z', max: '2023-01-01T00:00:00Z', label: '2022' },
  { min: '2023-01-01T00:00:00Z', max: '2024-01-01T00:00:00Z', label: '2023' },
  { min: '2024-01-01T00:00:00Z', max: '2024-07-01T00:00:00Z', label: '2024 H1' },
  { min: '2024-07-01T00:00:00Z', max: '2025-01-01T00:00:00Z', label: '2024 H2' },
  { min: '2025-01-01T00:00:00Z', max: '2026-01-01T00:00:00Z', label: '2025' },
];

async function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function backfillRange(range: typeof DATE_RANGES[0], retries = 3) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      console.log(`\n📅 Processing ${range.label} (${range.min} to ${range.max}) - Attempt ${attempt}/${retries}`);
      const result = await runShopifyNotionSync({
        createdAtMin: range.min,
        createdAtMax: range.max,
      });
      console.log(`✅ ${range.label} complete: ${result.notionCreated} created, ${result.notionUpdated} updated, ${result.notionSkipped} skipped`);
      return result;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      console.error(`❌ ${range.label} failed (attempt ${attempt}/${retries}): ${errorMsg}`);
      
      if (attempt < retries) {
        const waitTime = attempt * 10 * 1000; // Exponential backoff: 10s, 20s, 30s
        console.log(`⏳ Retrying in ${waitTime / 1000}s...`);
        await delay(waitTime);
      } else {
        console.error(`💥 ${range.label} failed after ${retries} attempts. Continuing to next range.`);
        throw error;
      }
    }
  }
}

async function main() {
  console.log('🚀 Starting full backfill of all Shopify orders to Notion');
  console.log(`📊 Total date ranges to process: ${DATE_RANGES.length}\n`);

  const startTime = Date.now();
  let totalCreated = 0;
  let totalUpdated = 0;
  let totalSkipped = 0;
  let failedRanges: string[] = [];

  for (const range of DATE_RANGES) {
    try {
      const result = await backfillRange(range);
      if (result) {
        totalCreated += result.notionCreated ?? 0;
        totalUpdated += result.notionUpdated ?? 0;
        totalSkipped += result.notionSkipped ?? 0;
      }
      
      // Small delay between ranges to avoid rate limits
      await delay(2000);
    } catch (error) {
      failedRanges.push(range.label);
      console.error(`⚠️  Skipping ${range.label} due to persistent errors`);
      // Continue with next range even if this one failed
      await delay(2000);
    }
  }

  const duration = ((Date.now() - startTime) / 1000 / 60).toFixed(1);
  console.log('\n' + '='.repeat(60));
  console.log('📊 BACKFILL SUMMARY');
  console.log('='.repeat(60));
  console.log(`⏱️  Total time: ${duration} minutes`);
  console.log(`✅ Created: ${totalCreated}`);
  console.log(`🔄 Updated: ${totalUpdated}`);
  console.log(`⏭️  Skipped: ${totalSkipped}`);
  console.log(`📦 Total processed: ${totalCreated + totalUpdated + totalSkipped}`);
  
  if (failedRanges.length > 0) {
    console.log(`\n⚠️  Failed ranges: ${failedRanges.join(', ')}`);
    console.log('   You may need to retry these manually.');
  } else {
    console.log('\n🎉 All ranges processed successfully!');
  }
  console.log('='.repeat(60));
}

main().catch((error) => {
  console.error('💥 Fatal error:', error);
  process.exit(1);
});

