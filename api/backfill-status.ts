import type { VercelRequest, VercelResponse } from '@vercel/node';
import { Client } from '@notionhq/client';
import { getEnvConfig, resolveDataSourceId, NOTION_VERSION } from '../lib/shopifyNotionSync.js';

export const config = {
  runtime: 'nodejs',
};

export default async function handler(req: VercelRequest, res: VercelResponse) {
  try {
    const env = getEnvConfig();
    const notion = new Client({ auth: env.notionToken, notionVersion: NOTION_VERSION });
    const dataSourceId = await resolveDataSourceId(notion, env);

    // Check orders without filter first to see overall state
    const sampleRes = await notion.dataSources.query({
      data_source_id: dataSourceId,
      page_size: 100,
      sorts: [{ property: 'Date', direction: 'descending' }],
    });

    const totalSampled = sampleRes.results.length;
    const populatedCount = sampleRes.results.filter(
      (page: any) => page.properties?.Channel?.select?.name
    ).length;
    const populatedPercentage = totalSampled > 0 ? Math.round((populatedCount / totalSampled) * 100) : 0;

    // Check oldest and newest orders with populated fields
    let oldestDate: string | null = null;
    let newestDate: string | null = null;
    let estimatedProgress = 'Not started';

    if (populatedCount > 0) {
      const [oldestRes, newestRes] = await Promise.all([
        notion.dataSources.query({
          data_source_id: dataSourceId,
          page_size: 1,
          sorts: [{ property: 'Date', direction: 'ascending' }],
          filter: {
            property: 'Channel',
            select: { is_not_empty: true },
          },
        }),
        notion.dataSources.query({
          data_source_id: dataSourceId,
          page_size: 1,
          sorts: [{ property: 'Date', direction: 'descending' }],
          filter: {
            property: 'Channel',
            select: { is_not_empty: true },
          },
        }),
      ]);

      const oldestPopulated: any = oldestRes.results[0];
      const newestPopulated: any = newestRes.results[0];
      
      oldestDate = oldestPopulated?.properties?.Date?.date?.start || null;
      newestDate = newestPopulated?.properties?.Date?.date?.start || null;
      
      if (oldestDate) {
        estimatedProgress = estimateProgressFromDate(oldestDate);
      }
    } else {
      // Check oldest order overall to see where we are
      const oldestOverall = await notion.dataSources.query({
        data_source_id: dataSourceId,
        page_size: 1,
        sorts: [{ property: 'Date', direction: 'ascending' }],
      });
      const oldestOrder: any = oldestOverall.results[0];
      const oldestOrderDate = oldestOrder?.properties?.Date?.date?.start;
      if (oldestOrderDate) {
        estimatedProgress = `Processing ${new Date(oldestOrderDate).getFullYear()} (fields not yet populated)`;
      }
    }

    res.setHeader('Cache-Control', 's-maxage=30');
    return res.status(200).json({
      oldestPopulatedDate: oldestDate,
      newestPopulatedDate: newestDate,
      sampleSize: totalSampled,
      populatedCount,
      populatedPercentage,
      estimatedProgress,
      isRunning: populatedCount === 0 && totalSampled > 0 ? 'Likely running' : populatedCount > 0 ? 'Complete or running' : 'Unknown',
    });
  } catch (error) {
    console.error('Backfill status failed', error);
    return res.status(500).json({
      error: error instanceof Error ? error.message : 'Unknown error',
    });
  }
}

function estimateProgressFromDate(oldestDate: string): string {
  const date = new Date(oldestDate);
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  
  // Estimate which range we're in based on oldest populated date
  if (year < 2019) return '2018 (Complete)';
  if (year < 2020) return '2019 (Complete)';
  if (year < 2021) return '2020 (Complete)';
  if (year < 2022) return '2021 (Complete)';
  if (year < 2023) return '2022 (Complete)';
  if (year < 2024) return '2023 (Complete)';
  if (year === 2024 && month < 7) return '2024 H1 (Complete)';
  if (year === 2024) return '2024 H2 (In Progress)';
  return '2025 (In Progress)';
}

