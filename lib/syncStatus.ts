import { Client } from '@notionhq/client';
import {
  SHOPIFY_API_VERSION,
  NOTION_VERSION,
  getEnvConfig,
  resolveDataSourceId,
  type EnvConfig,
} from './shopifyNotionSync.js';

export type NotionOrderSummary = {
  orderName?: string | null;
  orderNumber?: number | null;
  date?: string | null;
  total?: number | null;
  customer?: string | null;
  paymentStatus?: string | null;
  fulfillmentStatus?: string | null;
  tags?: string[];
  itemsSummary?: string | null;
  lastEditedTime?: string | null;
  url?: string | null;
};

export type ShopifyOrderSummary = {
  name?: string | null;
  orderNumber?: number | null;
  createdAt?: string | null;
  totalPrice?: string | null;
  financialStatus?: string | null;
  fulfillmentStatus?: string | null;
  customerName?: string | null;
};

export type ShopifySyncSummary = {
  count: number | null;
  latestOrder: ShopifyOrderSummary | null;
};

export type SyncStatusSnapshot = {
  healthy: boolean;
  cronSchedule: string;
  lastRefreshed: string;
  vercelEnv: string;
  notionDatabaseUrl: string;
  shopifyAdminUrl: string;
  notion: NotionOrderSummary | null;
  shopify: ShopifySyncSummary | null;
  warnings: string[];
};

export async function fetchSyncStatus(): Promise<SyncStatusSnapshot> {
  const env = getEnvConfig();
  const notion = new Client({ auth: env.notionToken, notionVersion: NOTION_VERSION });
  const dataSourceId = await resolveDataSourceId(notion, env);
  const notionUrl = buildNotionDatabaseUrl(env);

  const [notionResult, shopifyResult] = await Promise.allSettled([
    getLatestNotionOrder(notion, dataSourceId),
    getShopifySummary(env),
  ]);

  const warnings: string[] = [];
  const notionSummary =
    notionResult.status === 'fulfilled' ? notionResult.value : logAndCaptureWarning(notionResult.reason, warnings, 'Notion');
  const shopifySummary =
    shopifyResult.status === 'fulfilled'
      ? shopifyResult.value
      : logAndCaptureWarning(shopifyResult.reason, warnings, 'Shopify');

  return {
    healthy: warnings.length === 0,
    cronSchedule: '*/15 * * * *',
    lastRefreshed: new Date().toISOString(),
    vercelEnv: process.env.VERCEL_ENV ?? 'development',
    notionDatabaseUrl: notionUrl,
    shopifyAdminUrl: `https://${env.storeDomain}/admin/orders`,
    notion: notionSummary,
    shopify: shopifySummary,
    warnings,
  };
}

async function getLatestNotionOrder(notion: Client, dataSourceId: string): Promise<NotionOrderSummary | null> {
  const response: any = await notion.dataSources.query({
    data_source_id: dataSourceId,
    page_size: 1,
    sorts: [
      {
        property: 'Date',
        direction: 'descending',
      },
      {
        property: 'ORDER',
        direction: 'descending',
      },
    ],
  });

  const page = response.results?.[0];
  if (!page) {
    return null;
  }

  const props = page.properties ?? {};

  return {
    orderName: extractTitle(props['ORDER']) ?? null,
    orderNumber: props['Order ID']?.number ?? null,
    date: props['Date']?.date?.start ?? null,
    total: props['Total']?.number ?? null,
    customer: extractRichText(props['Customer']) ?? null,
    paymentStatus: props['Payment Status']?.select?.name ?? null,
    fulfillmentStatus: props['Fulfillment Status']?.select?.name ?? null,
    tags: (props['Tags']?.multi_select ?? []).map((tag: { name: string }) => tag.name).filter(Boolean),
    itemsSummary: extractRichText(props['Items']) ?? null,
    lastEditedTime: page.last_edited_time ?? null,
    url: page.url ?? null,
  };
}

async function getShopifySummary(env: EnvConfig): Promise<ShopifySyncSummary> {
  const headers = {
    'X-Shopify-Access-Token': env.shopifyToken,
    'Content-Type': 'application/json',
  };

  const countResp = await fetch(
    `https://${env.storeDomain}/admin/api/${SHOPIFY_API_VERSION}/orders/count.json?status=any`,
    { headers },
  );
  if (!countResp.ok) {
    const body = await countResp.text();
    throw new Error(`Shopify count failed (${countResp.status}): ${body}`);
  }
  const countData = (await countResp.json()) as { count: number };

  const latestResp = await fetch(
    `https://${env.storeDomain}/admin/api/${SHOPIFY_API_VERSION}/orders.json?status=any&limit=1&order=created_at%20desc`,
    { headers },
  );
  if (!latestResp.ok) {
    const body = await latestResp.text();
    throw new Error(`Shopify latest order fetch failed (${latestResp.status}): ${body}`);
  }
  const latestData = (await latestResp.json()) as { orders: Array<Record<string, any>> };
  const latestOrder = latestData.orders?.[0];

  return {
    count: countData.count ?? null,
    latestOrder: latestOrder
      ? {
          name: latestOrder.name ?? null,
          orderNumber: latestOrder.order_number ?? null,
          createdAt: latestOrder.created_at ?? null,
          totalPrice: latestOrder.total_price ?? null,
          financialStatus: latestOrder.financial_status ?? null,
          fulfillmentStatus: latestOrder.fulfillment_status ?? null,
          customerName: formatShopifyCustomer(latestOrder) ?? null,
        }
      : null,
  };
}

function extractTitle(property: any): string | undefined {
  const title = property?.title ?? [];
  if (!Array.isArray(title) || !title.length) return undefined;
  return title.map((item: any) => item.plain_text ?? '').join('').trim() || undefined;
}

function extractRichText(property: any): string | undefined {
  const rich = property?.rich_text ?? [];
  if (!Array.isArray(rich) || !rich.length) return undefined;
  return rich.map((item: any) => item.plain_text ?? '').join('').trim() || undefined;
}

function formatShopifyCustomer(order: Record<string, any>): string | null {
  const customer = order.customer || {};
  const first = customer.first_name ?? '';
  const last = customer.last_name ?? '';
  const fullName = `${first} ${last}`.trim();
  if (fullName) return fullName;
  return order.email ?? customer.email ?? null;
}

function buildNotionDatabaseUrl(env: EnvConfig): string {
  const compactId = env.notionDatabaseId.replace(/-/g, '');
  return `https://www.notion.so/${compactId}`;
}

function logAndCaptureWarning(reason: unknown, warnings: string[], scope: string) {
  const message =
    reason instanceof Error ? reason.message : typeof reason === 'string' ? reason : 'Unknown error';
  warnings.push(`${scope}: ${message}`);
  console.warn(`[status] ${scope} warning: ${message}`);
  return null;
}

