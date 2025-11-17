import type { VercelRequest, VercelResponse } from '@vercel/node';
import { fetchSyncStatus } from '../lib/syncStatus.js';

export const config = {
  runtime: 'nodejs',
};

export default async function handler(req: VercelRequest, res: VercelResponse) {
  try {
    const snapshot = await fetchSyncStatus();
    const html = renderHtml(snapshot);
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('Cache-Control', 's-maxage=60');
    return res.status(200).send(html);
  } catch (error) {
    console.error('Status page failed', error);
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res
      .status(500)
      .send(`<html><body><h1>Sync status unavailable</h1><p>${escapeHtml(error instanceof Error ? error.message : 'Unknown error')}</p></body></html>`);
  }
}

function renderHtml(snapshot: Awaited<ReturnType<typeof fetchSyncStatus>>): string {
  const notion = snapshot.notion;
  const shopify = snapshot.shopify;
  const lastOrderDate = notion?.date ? formatDate(notion.date) : 'Unknown';
  const lastEdited = notion?.lastEditedTime ? formatDate(notion.lastEditedTime) : '—';
  const lastShopifyDate = shopify?.latestOrder?.createdAt ? formatDate(shopify.latestOrder.createdAt) : 'Unknown';

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Shopify → Notion Sync Status</title>
    <style>
      :root {
        color-scheme: dark;
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: #050505;
        color: #f5f5f5;
      }
      body {
        margin: 0;
        padding: 32px 16px 64px;
        display: flex;
        justify-content: center;
        background: radial-gradient(circle at top, #111 0%, #050505 45%);
      }
      .card {
        width: min(960px, 100%);
        background: rgba(20, 20, 20, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 32px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
        backdrop-filter: blur(16px);
      }
      h1 {
        margin: 0 0 8px;
        font-size: 1.9rem;
      }
      p.lead {
        margin: 0 0 24px;
        color: #a3a3a3;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 16px;
      }
      .metric {
        padding: 16px;
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
      }
      .metric label {
        display: block;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.72rem;
        color: #8b8b8b;
        margin-bottom: 8px;
      }
      .metric strong {
        font-size: 1.4rem;
        display: block;
        margin-bottom: 4px;
      }
      .metric span {
        font-size: 0.95rem;
        color: #c7c7c7;
      }
      .section {
        margin-top: 32px;
      }
      .section h2 {
        font-size: 1.2rem;
        margin-bottom: 12px;
        color: #e8e8e8;
      }
      .detail-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        gap: 8px;
      }
      .detail-list li {
        padding: 12px 16px;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.04);
      }
      .detail-list span {
        display: block;
        color: #9c9c9c;
        font-size: 0.85rem;
      }
      a {
        color: #70cfff;
        text-decoration: none;
      }
      .warnings {
        margin-top: 24px;
        padding: 16px;
        border-radius: 12px;
        border: 1px solid rgba(255, 0, 0, 0.3);
        background: rgba(255, 0, 0, 0.08);
        color: #ffb3b3;
      }
      .backfill-status {
        padding: 16px;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.04);
      }
      .progress-bar {
        width: 100%;
        height: 24px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        overflow: hidden;
        margin: 12px 0;
      }
      .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #70cfff 0%, #4a9eff 100%);
        transition: width 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #050505;
        font-size: 0.75rem;
        font-weight: 600;
      }
    </style>
  </head>
  <body>
    <main class="card">
      <h1>Shopify → Notion Sync</h1>
      <p class="lead">
        Schedule: every 15 minutes (${escapeHtml(snapshot.cronSchedule)}). Last refresh ${formatDate(snapshot.lastRefreshed)} · Env: ${escapeHtml(snapshot.vercelEnv)}
      </p>
      <div class="grid">
        <div class="metric">
          <label>Latest Notion Order</label>
          <strong>${escapeHtml(notion?.orderName ?? '—')}</strong>
          <span>${escapeHtml(lastOrderDate)}</span>
        </div>
        <div class="metric">
          <label>Last Sync Write</label>
          <strong>${escapeHtml(lastEdited)}</strong>
          <span>Notion data source</span>
        </div>
        <div class="metric">
          <label>Shopify Orders (API)</label>
          <strong>${shopify?.count ?? '—'}</strong>
          <span>Last order ${escapeHtml(lastShopifyDate)}</span>
        </div>
        <div class="metric">
          <label>Status</label>
          <strong>${snapshot.healthy ? 'Healthy' : 'Needs attention'}</strong>
          <span>${snapshot.warnings.length ? 'Warnings present' : 'All systems nominal'}</span>
        </div>
      </div>

      <section class="section">
        <h2>Last Synced Order Details</h2>
        ${
          notion
            ? `<ul class="detail-list">
                <li><strong>Customer</strong><span>${escapeHtml(notion.customer ?? '—')}</span></li>
                <li><strong>Total</strong><span>${notion.total != null ? '$' + notion.total.toFixed(2) : '—'}</span></li>
                <li><strong>Payment · Fulfillment</strong><span>${escapeHtml(
                  [notion.paymentStatus, notion.fulfillmentStatus].filter(Boolean).join(' · ') || '—',
                )}</span></li>
                <li><strong>Tags</strong><span>${escapeHtml(
                  notion.tags && notion.tags.length ? notion.tags.join(', ') : '—',
                )}</span></li>
                <li><strong>Notion page</strong><span>${
                  notion.url ? `<a href="${notion.url}" target="_blank">Open in Notion</a>` : '—'
                }</span></li>
              </ul>`
            : '<p>No Notion data available yet.</p>'
        }
      </section>

      <section class="section">
        <h2>Shopify Snapshot</h2>
        ${
          shopify?.latestOrder
            ? `<ul class="detail-list">
                <li><strong>Order</strong><span>${escapeHtml(
                  shopify.latestOrder.name ?? `#${shopify.latestOrder.orderNumber ?? ''}`,
                )}</span></li>
                <li><strong>Customer</strong><span>${escapeHtml(shopify.latestOrder.customerName ?? '—')}</span></li>
                <li><strong>Total</strong><span>${escapeHtml(
                  shopify.latestOrder.totalPrice ? '$' + shopify.latestOrder.totalPrice : '—',
                )}</span></li>
                <li><strong>Status</strong><span>${escapeHtml(
                  [shopify.latestOrder.financialStatus, shopify.latestOrder.fulfillmentStatus]
                    .filter(Boolean)
                    .join(' · ') || '—',
                )}</span></li>
              </ul>`
            : '<p>No Shopify snapshot available.</p>'
        }
      </section>

      <section class="section">
        <h2>Backfill Progress</h2>
        <div id="backfill-status" class="backfill-status">
          <p>Loading backfill status...</p>
        </div>
      </section>

      <section class="section">
        <h2>Shortcuts</h2>
        <ul class="detail-list">
          <li><strong>Notion Database</strong><span><a href="${snapshot.notionDatabaseUrl}" target="_blank">${snapshot.notionDatabaseUrl}</a></span></li>
          <li><strong>Shopify Admin</strong><span><a href="${snapshot.shopifyAdminUrl}" target="_blank">${snapshot.shopifyAdminUrl}</a></span></li>
          <li><strong>Status API</strong><span><a href="/api/status" target="_blank">/api/status</a></span></li>
        </ul>
      </section>

      ${
        snapshot.warnings.length
          ? `<div class="warnings">
              <strong>Warnings</strong>
              <ul>${snapshot.warnings.map((w: string) => `<li>${escapeHtml(w)}</li>`).join('')}</ul>
            </div>`
          : ''
      }
    </main>
    <script>
      async function updateBackfillStatus() {
        try {
          const res = await fetch('/api/backfill-status');
          const data = await res.json();
          const container = document.getElementById('backfill-status');
          if (!container) return;

          const oldestDate = data.oldestPopulatedDate 
            ? new Date(data.oldestPopulatedDate).toLocaleDateString()
            : 'None yet';
          const newestDate = data.newestPopulatedDate
            ? new Date(data.newestPopulatedDate).toLocaleDateString()
            : 'None yet';

          container.innerHTML = \`
            <div class="metric">
              <label>Status</label>
              <strong>\${data.isRunning || 'Unknown'}</strong>
              <span>\${data.estimatedProgress || 'Unknown'}</span>
            </div>
            <div class="metric">
              <label>Progress</label>
              <strong>\${data.populatedPercentage}%</strong>
              <span>of recent orders populated</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" style="width: \${data.populatedPercentage}%">
                \${data.populatedPercentage}%
              </div>
            </div>
            <ul class="detail-list">
              <li><strong>Oldest Populated</strong><span>\${oldestDate}</span></li>
              <li><strong>Newest Populated</strong><span>\${newestDate}</span></li>
              <li><strong>Sample Size</strong><span>\${data.sampleSize} orders checked</span></li>
              <li><strong>Populated Count</strong><span>\${data.populatedCount} orders</span></li>
            </ul>
          \`;
        } catch (error) {
          const container = document.getElementById('backfill-status');
          if (container) {
            container.innerHTML = '<p style="color: #ffb3b3;">Failed to load backfill status</p>';
          }
        }
      }

      // Update immediately and then every 30 seconds
      updateBackfillStatus();
      setInterval(updateBackfillStatus, 30000);
    </script>
  </body>
</html>`;
}

function formatDate(value: string): string {
  try {
    const date = new Date(value);
    return new Intl.DateTimeFormat('en-US', {
      dateStyle: 'medium',
      timeStyle: 'short',
      timeZone: 'UTC',
    }).format(date);
  } catch {
    return value;
  }
}

function escapeHtml(value: string | number): string {
  const str = value == null ? '' : String(value);
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

