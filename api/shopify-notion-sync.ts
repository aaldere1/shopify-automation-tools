import type { VercelRequest, VercelResponse } from '@vercel/node';
import { runShopifyNotionSync } from '../lib/shopifyNotionSync.js';

export const config = {
  runtime: 'nodejs',
};

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'GET' && req.method !== 'POST') {
    res.setHeader('Allow', 'GET, POST');
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  try {
    const dryRunParam = typeof req.query.dryRun === 'string' ? req.query.dryRun : undefined;
    const dryRun = dryRunParam === 'true';

    // For cron runs, skip schema updates to avoid any potential interference
    // Schema should already be set up from initial deployment
    const result = await runShopifyNotionSync({ 
      dryRun,
      ensureSchema: false, // Skip schema updates on cron runs
    });
    return res.status(200).json({
      ok: true,
      timestamp: new Date().toISOString(),
      ...result,
    });
  } catch (error) {
    console.error('Shopify→Notion sync failed', error);
    return res.status(500).json({
      ok: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    });
  }
}

