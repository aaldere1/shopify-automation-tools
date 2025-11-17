import type { VercelRequest, VercelResponse } from '@vercel/node';
import { fetchSyncStatus } from '../lib/syncStatus.js';

export default async function handler(req: VercelRequest, res: VercelResponse) {
  try {
    const snapshot = await fetchSyncStatus();
    res.setHeader('Cache-Control', 's-maxage=60');
    return res.status(200).json({ ok: snapshot.healthy, snapshot });
  } catch (error) {
    console.error('Status endpoint failed', error);
    return res.status(500).json({
      ok: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    });
  }
}

