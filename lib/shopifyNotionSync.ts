import { Client } from '@notionhq/client';
import type { BlockObjectRequest } from '@notionhq/client/build/src/api-endpoints.js';

export const SHOPIFY_API_VERSION = '2025-10';
export const NOTION_VERSION = '2025-09-03';
const REQUIRED_ENV_VARS = [
  'SHOPIFY_STORE_DOMAIN',
  'SHOPIFY_ADMIN_TOKEN',
  'NOTION_TOKEN',
  'NOTION_DATABASE_ID',
];

export type SyncOptions = {
  createdAtMin?: string;
  createdAtMax?: string;
  dryRun?: boolean;
};

export type EnvConfig = {
  storeDomain: string;
  shopifyToken: string;
  notionToken: string;
  notionDatabaseId: string;
  notionDataSourceId: string | undefined;
};

type ShopifyOrder = {
  id: number;
  name: string;
  order_number: number;
  tags?: string;
  created_at: string;
  processed_at?: string | null;
  updated_at?: string;
  closed_at?: string | null;
  canceled_at?: string | null;
  cancel_reason?: string | null;
  current_total_price?: string;
  total_price?: string;
  subtotal_price?: string;
  total_discounts?: string;
  total_tax?: string;
  current_total_tax?: string;
  total_shipping_price_set?: {
    shop_money?: {
      amount?: string;
      currency_code?: string;
    };
  };
  currency?: string;
  financial_status?: string;
  fulfillment_status?: string | null;
  email?: string;
  phone?: string | null;
  note?: string | null;
  source_name?: string | null;
  gateway?: string | null;
  payment_gateway_names?: string[];
  line_items: ShopifyLineItem[];
  shipping_lines?: ShopifyShippingLine[];
  fulfillments?: ShopifyFulfillment[];
  customer?: ShopifyCustomer | null;
  shipping_address?: ShopifyAddress | null;
  billing_address?: ShopifyAddress | null;
};

type ShopifyLineItem = {
  id: number;
  name: string;
  title: string;
  sku?: string | null;
  quantity: number;
  price: string;
  fulfillment_status?: string | null;
  vendor?: string | null;
  variant_title?: string | null;
  grams?: number;
  properties?: { name: string; value: string }[];
};

type ShopifyShippingLine = {
  code?: string | null;
  price: string;
  title?: string | null;
  source?: string | null;
  carrier_identifier?: string | null;
  requested_fulfillment_service_id?: string | null;
};

type ShopifyFulfillment = {
  id: number;
  status?: string | null;
  tracking_company?: string | null;
  tracking_numbers?: string[] | null;
  tracking_urls?: string[] | null;
  shipment_status?: string | null;
  created_at?: string;
  updated_at?: string;
  location_id?: number | null;
};

type ShopifyCustomer = {
  id: number;
  first_name?: string | null;
  last_name?: string | null;
  email?: string | null;
  phone?: string | null;
  tags?: string | null;
  default_address?: ShopifyAddress | null;
};

type ShopifyAddress = {
  name?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  address1?: string | null;
  address2?: string | null;
  phone?: string | null;
  city?: string | null;
  province?: string | null;
  province_code?: string | null;
  zip?: string | null;
  country?: string | null;
  country_code?: string | null;
  company?: string | null;
};

type ExistingPageMap = Map<number, string>;

let cachedDataSourceId: string | null = null;

export async function runShopifyNotionSync(options: SyncOptions = {}) {
  const env = getEnvConfig();
  const notion = new Client({ auth: env.notionToken, notionVersion: NOTION_VERSION });
  const dataSourceId = await resolveDataSourceId(notion, env, options);

  await ensureDatabaseSchema(notion, dataSourceId);
  const existingPages = await loadExistingOrderPageMap(notion, dataSourceId);

  const orders = await fetchAllOrders(env, options);
  console.log(`📦 Shopify orders fetched: ${orders.length}`);

  if (options.dryRun) {
    console.log('🧪 Dry run enabled. Skipping Notion writes.');
    return {
      dryRun: true,
      totalOrders: orders.length,
    };
  }

  let created = 0;
  let updated = 0;
  let skipped = 0;

  for (const order of orders) {
    const notionProps = buildNotionProperties(order);
    const blocks = buildPageBlocks(order);
    const existingPageId = existingPages.get(order.id);

    if (existingPageId) {
      await notion.pages.update({
        page_id: existingPageId,
        properties: notionProps,
      });
      updated += 1;
      continue;
    }

    await notion.pages.create({
      parent: {
        type: 'data_source_id',
        data_source_id: dataSourceId,
      } as any,
      properties: notionProps,
      children: blocks,
    });
    created += 1;
  }

  skipped = orders.length - created - updated;

  return {
    totalOrders: orders.length,
    notionCreated: created,
    notionUpdated: updated,
    notionSkipped: skipped,
  };
}

export function getEnvConfig(): EnvConfig {
  const missing = REQUIRED_ENV_VARS.filter((key) => !process.env[key]);
  if (missing.length) {
    throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
  }
  return {
    storeDomain: process.env.SHOPIFY_STORE_DOMAIN as string,
    shopifyToken: process.env.SHOPIFY_ADMIN_TOKEN as string,
    notionToken: process.env.NOTION_TOKEN as string,
    notionDatabaseId: process.env.NOTION_DATABASE_ID as string,
    notionDataSourceId: process.env.NOTION_DATA_SOURCE_ID ?? undefined,
  };
}

export async function resolveDataSourceId(
  notion: Client,
  env: EnvConfig,
  options: SyncOptions = {},
): Promise<string> {
  if (options.dryRun && env.notionDataSourceId) {
    return env.notionDataSourceId;
  }
  if (cachedDataSourceId) {
    return cachedDataSourceId;
  }
  if (env.notionDataSourceId) {
    cachedDataSourceId = env.notionDataSourceId;
    return env.notionDataSourceId;
  }

  const database: any = await notion.databases.retrieve({
    database_id: env.notionDatabaseId,
  });

  const dataSources = database.data_sources as Array<{ id: string; name?: string }> | undefined;
  if (!dataSources || dataSources.length === 0) {
    throw new Error(
      'No data sources found for the Notion database. Please add at least one data source or provide NOTION_DATA_SOURCE_ID.',
    );
  }

  const primaryDataSource = dataSources[0];
  if (!primaryDataSource) {
    throw new Error('No primary Notion data source available.');
  }

  cachedDataSourceId = primaryDataSource.id;
  return cachedDataSourceId;
}

async function ensureDatabaseSchema(notion: Client, dataSourceId: string) {
  const dataSource: any = await notion.dataSources.retrieve({ data_source_id: dataSourceId });
  const existingProps: Record<string, { id?: string; name?: string }> = dataSource.properties ?? {};

  const propertyDefinitions: Record<string, any> = {};

  propertyDefinitions[getPropertyKey(existingProps, ['ORDER', 'Order', 'Name']) ?? 'ORDER'] =
    buildPropertyConfig(existingProps, ['ORDER', 'Order', 'Name'], 'ORDER', {
      type: 'title',
      title: {},
    });

  propertyDefinitions[getPropertyKey(existingProps, ['Tags']) ?? 'Tags'] = buildPropertyConfig(
    existingProps,
    ['Tags'],
    'Tags',
    {
      type: 'multi_select',
      multi_select: {},
    },
  );

  propertyDefinitions[getPropertyKey(existingProps, ['Date']) ?? 'Date'] = buildPropertyConfig(
    existingProps,
    ['Date'],
    'Date',
    {
      type: 'date',
      date: {},
    },
  );

  propertyDefinitions[getPropertyKey(existingProps, ['Customer']) ?? 'Customer'] =
    buildPropertyConfig(existingProps, ['Customer'], 'Customer', {
      type: 'rich_text',
      rich_text: {},
    });

  propertyDefinitions[getPropertyKey(existingProps, ['Channel']) ?? 'Channel'] = buildPropertyConfig(
    existingProps,
    ['Channel'],
    'Channel',
    {
      type: 'select',
      select: {},
    },
  );

  propertyDefinitions[getPropertyKey(existingProps, ['Total']) ?? 'Total'] = buildPropertyConfig(
    existingProps,
    ['Total'],
    'Total',
    {
      type: 'number',
      number: { format: 'dollar' },
    },
  );

  propertyDefinitions[getPropertyKey(existingProps, ['Payment Status']) ?? 'Payment Status'] =
    buildPropertyConfig(existingProps, ['Payment Status'], 'Payment Status', {
      type: 'select',
      select: {},
    });

  propertyDefinitions[getPropertyKey(existingProps, ['Fulfillment Status']) ?? 'Fulfillment Status'] =
    buildPropertyConfig(existingProps, ['Fulfillment Status'], 'Fulfillment Status', {
      type: 'select',
      select: {},
    });

  propertyDefinitions[getPropertyKey(existingProps, ['Items']) ?? 'Items'] = buildPropertyConfig(
    existingProps,
    ['Items'],
    'Items',
    {
      type: 'rich_text',
      rich_text: {},
    },
  );

  propertyDefinitions[getPropertyKey(existingProps, ['Delivery Status']) ?? 'Delivery Status'] =
    buildPropertyConfig(existingProps, ['Delivery Status'], 'Delivery Status', {
      type: 'select',
      select: {},
    });

  propertyDefinitions[getPropertyKey(existingProps, ['Delivery method']) ?? 'Delivery method'] =
    buildPropertyConfig(existingProps, ['Delivery method'], 'Delivery method', {
      type: 'select',
      select: {},
    });

  propertyDefinitions[getPropertyKey(existingProps, ['Order ID']) ?? 'Order ID'] =
    buildPropertyConfig(existingProps, ['Order ID'], 'Order ID', {
      type: 'number',
      number: {},
    });

  await notion.dataSources.update({
    data_source_id: dataSourceId,
    properties: propertyDefinitions,
  });
}

function getProperty(
  existingProps: Record<string, { id?: string }>,
  names: string[],
): { id?: string } | undefined {
  for (const name of names) {
    if (existingProps[name]) {
      return existingProps[name];
    }
  }
  return undefined;
}

function getPropertyKey(
  existingProps: Record<string, { id?: string }>,
  names: string[],
): string | undefined {
  for (const name of names) {
    if (existingProps[name]) {
      return name;
    }
  }
  return undefined;
}

function buildPropertyConfig(
  existingProps: Record<string, { id?: string }>,
  searchNames: string[],
  targetName: string,
  config: Record<string, unknown>,
) {
  const match = getProperty(existingProps, searchNames);
  const base: Record<string, unknown> = { name: targetName, ...config };

  if (match?.id) {
    base.id = match.id;
  } else if (targetName === 'ORDER') {
    base.id = 'title';
  }

  return base;
}

async function loadExistingOrderPageMap(
  notion: Client,
  dataSourceId: string,
): Promise<ExistingPageMap> {
  const map: ExistingPageMap = new Map();
  let cursor: string | undefined;

  do {
    const queryBody: Record<string, unknown> = {
      data_source_id: dataSourceId,
      page_size: 100,
      filter: {
        property: 'Order ID',
        number: { is_not_empty: true },
      },
    };
    if (cursor) {
      queryBody.start_cursor = cursor;
    }

    const response: any = await notion.dataSources.query(queryBody as any);

    for (const result of response.results as any[]) {
      const orderId = result.properties?.['Order ID']?.number;
      if (typeof orderId === 'number') {
        map.set(orderId, result.id);
      }
    }

    cursor = response.has_more ? response.next_cursor ?? undefined : undefined;
  } while (cursor);

  return map;
}

async function fetchAllOrders(env: EnvConfig, options: SyncOptions): Promise<ShopifyOrder[]> {
  const baseUrl = new URL(
    `https://${env.storeDomain}/admin/api/${SHOPIFY_API_VERSION}/orders.json`,
  );
  baseUrl.searchParams.set('status', 'any');
  baseUrl.searchParams.set('limit', '250');
  baseUrl.searchParams.set('order', 'created_at asc');

  const createdAtMin = options.createdAtMin ?? process.env.SHOPIFY_CREATED_AT_MIN;
  const createdAtMax = options.createdAtMax ?? process.env.SHOPIFY_CREATED_AT_MAX;
  if (createdAtMin) {
    baseUrl.searchParams.set('created_at_min', createdAtMin);
  }
  if (createdAtMax) {
    baseUrl.searchParams.set('created_at_max', createdAtMax);
  }

  const headers = {
    'X-Shopify-Access-Token': env.shopifyToken,
    'Content-Type': 'application/json',
  };

  const orders: ShopifyOrder[] = [];
  let nextUrl: string | null = baseUrl.toString();

  while (nextUrl) {
    console.log(`⬇️  Fetching Shopify orders batch: ${orders.length} processed so far`);
    const response = await fetch(nextUrl, { headers });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Shopify fetch failed (${response.status}): ${body}`);
    }

    const data = (await response.json()) as { orders: ShopifyOrder[] };
    orders.push(...(data.orders ?? []));

    const linkHeader = response.headers.get('link');
    nextUrl = parseNextLink(linkHeader);
    if (nextUrl && !nextUrl.startsWith('http')) {
      nextUrl = `https://${env.storeDomain}${nextUrl}`;
    }

    if (nextUrl) {
      await delay(300);
    }
  }

  return orders;
}

function parseNextLink(linkHeader: string | null): string | null {
  if (!linkHeader) return null;
  const parts = linkHeader.split(',');
  for (const part of parts) {
    const [urlPartRaw, relPart] = part.split(';').map((entry) => entry.trim());
    if (!urlPartRaw || !relPart) continue;
    if (relPart === 'rel="next"' && urlPartRaw.startsWith('<') && urlPartRaw.endsWith('>')) {
      return urlPartRaw.slice(1, -1);
    }
  }
  return null;
}

function buildNotionProperties(order: ShopifyOrder): Record<string, any> {
  const currency = order.currency ?? 'USD';
  const total = parseFloat(order.total_price ?? order.current_total_price ?? '0') || 0;
  const tags = (order.tags ?? '')
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean);

  const customerName = formatCustomerName(order);
  const itemsSummary = summarizeLineItems(order);
  const deliveryStatus = determineDeliveryStatus(order);
  const deliveryMethod = deriveDeliveryMethod(order);
  const channel = formatChannel(order.source_name);

  const props: Record<string, any> = {
    ORDER: {
      title: [
        {
          type: 'text',
          text: { content: order.name || `Order ${order.order_number}` },
        },
      ],
    },
    Tags: {
      multi_select: tags.map((name) => ({ name })),
    },
    Date: {
      date: { start: order.created_at },
    },
    Customer: {
      rich_text: [
        {
          type: 'text',
          text: { content: truncate(customerName || 'Unknown Customer') },
        },
      ],
    },
    Total: {
      number: Number(total.toFixed(2)),
    },
    Items: {
      rich_text: [
        {
          type: 'text',
          text: { content: truncate(itemsSummary || 'No line items') },
        },
      ],
    },
    'Order ID': {
      number: order.id,
    },
  };

  // Always set select properties with defaults to ensure data is populated
  // formatChannel already returns 'Online Store' as default, so channel is always truthy
  props.Channel = { select: { name: channel } };
  
  props['Payment Status'] = order.financial_status
    ? { select: { name: normalizeStatus(order.financial_status) } }
    : { select: { name: 'Unknown' } };
  
  props['Fulfillment Status'] = order.fulfillment_status
    ? { select: { name: normalizeStatus(order.fulfillment_status) } }
    : { select: { name: 'unfulfilled' } };
  
  // determineDeliveryStatus always returns a value (defaults to 'pending')
  props['Delivery Status'] = { select: { name: deliveryStatus } };
  
  props['Delivery method'] = deliveryMethod
    ? { select: { name: deliveryMethod } }
    : { select: { name: 'Standard Shipping' } };

  return props;
}

function buildPageBlocks(order: ShopifyOrder): BlockObjectRequest[] {
  const blocks: BlockObjectRequest[] = [];

  blocks.push(headingBlock('Order Overview'));
  blocks.push(
    paragraphBlock(
      `${order.name} • ${formatMoney(
        parseFloat(order.total_price ?? order.current_total_price ?? '0'),
        order.currency,
      )}`,
    ),
  );

  blocks.push(headingBlock('Timeline'));
  const timeline = buildTimeline(order);
  if (timeline.length) {
    blocks.push(...timeline.map((entry) => bulletBlock(entry)));
  } else {
    blocks.push(paragraphBlock('No timeline data available.'));
  }

  blocks.push(headingBlock('Line Items'));
  const itemBlocks = buildLineItemBlocks(order);
  blocks.push(...(itemBlocks.length ? itemBlocks : [paragraphBlock('No items found.')]));

  blocks.push(headingBlock('Tracking & Fulfillment'));
  const trackingBlocks = buildTrackingBlocks(order);
  blocks.push(...(trackingBlocks.length ? trackingBlocks : [paragraphBlock('No tracking yet.')]));

  blocks.push(headingBlock('Customer & Addresses'));
  blocks.push(paragraphBlock(`Customer: ${formatCustomerName(order) || 'Unknown'}`));
  if (order.email) {
    blocks.push(paragraphBlock(`Email: ${order.email}`));
  }
  if (order.phone) {
    blocks.push(paragraphBlock(`Phone: ${order.phone}`));
  }
  const shippingAddress = formatAddress(order.shipping_address);
  const billingAddress = formatAddress(order.billing_address);
  if (shippingAddress) {
    blocks.push(paragraphBlock(`Shipping:\n${shippingAddress}`));
  }
  if (billingAddress) {
    blocks.push(paragraphBlock(`Billing:\n${billingAddress}`));
  }

  blocks.push(headingBlock('Payment & Totals'));
  const financialLines = buildFinancialSummary(order);
  blocks.push(...financialLines.map((line) => bulletBlock(line)));

  if (order.note) {
    blocks.push(headingBlock('Order Note'));
    blocks.push(paragraphBlock(truncate(order.note)));
  }

  return blocks.slice(0, 90);
}

function buildTimeline(order: ShopifyOrder): string[] {
  const entries: string[] = [];
  entries.push(`Created: ${formatDate(order.created_at)}`);
  if (order.processed_at) entries.push(`Processed: ${formatDate(order.processed_at)}`);
  if (order.updated_at) entries.push(`Updated: ${formatDate(order.updated_at)}`);
  if (order.closed_at) entries.push(`Closed: ${formatDate(order.closed_at)}`);
  if (order.canceled_at) {
    entries.push(
      `Cancelled: ${formatDate(order.canceled_at)}${order.cancel_reason ? ` (${order.cancel_reason})` : ''}`,
    );
  }
  return entries;
}

function buildLineItemBlocks(order: ShopifyOrder): BlockObjectRequest[] {
  return order.line_items.map((item) =>
    bulletBlock(
      `${item.quantity} × ${item.title}${item.variant_title ? ` (${item.variant_title})` : ''}${
        item.sku ? ` • SKU: ${item.sku}` : ''
      } • ${formatMoney(parseFloat(item.price) * item.quantity, order.currency)}`,
    ),
  );
}

function buildTrackingBlocks(order: ShopifyOrder): BlockObjectRequest[] {
  const fulfillments = order.fulfillments ?? [];
  if (!fulfillments.length) {
    return [];
  }
  const blocks: BlockObjectRequest[] = [];
  fulfillments.forEach((fulfillment, index) => {
    blocks.push(
      bulletBlock(
        `Fulfillment #${index + 1}: ${normalizeStatus(
          fulfillment.status ?? fulfillment.shipment_status ?? 'pending',
        )}`,
      ),
    );
    if (fulfillment.tracking_company) {
      blocks.push(bulletBlock(`Carrier: ${fulfillment.tracking_company}`));
    }
    const numbers = fulfillment.tracking_numbers ?? [];
    if (numbers.length) {
      blocks.push(bulletBlock(`Tracking #: ${numbers.join(', ')}`));
    }
    const urls = fulfillment.tracking_urls ?? [];
    if (urls.length) {
      urls.slice(0, 3).forEach((url) => {
        blocks.push(
          {
            object: 'block',
            type: 'paragraph',
            paragraph: {
              rich_text: [
                {
                  type: 'text',
                  text: { content: 'Tracking Link', link: { url } },
                },
              ],
            },
          },
        );
      });
    }
  });
  return blocks;
}

function buildFinancialSummary(order: ShopifyOrder): string[] {
  const lines: string[] = [];
  const total = parseFloat(order.total_price ?? order.current_total_price ?? '0') || 0;
  const subtotal = parseFloat(order.subtotal_price ?? order.total_price ?? '0') || 0;
  const discounts = parseFloat(order.total_discounts ?? '0') || 0;
  const tax = parseFloat(order.total_tax ?? order.current_total_tax ?? '0') || 0;
  const shipping =
    parseFloat(order.total_shipping_price_set?.shop_money?.amount ?? '0') ||
    estimateShipping(order);

  lines.push(`Subtotal: ${formatMoney(subtotal, order.currency)}`);
  if (discounts) {
    lines.push(`Discounts: -${formatMoney(discounts, order.currency)}`);
  }
  if (tax) {
    lines.push(`Tax: ${formatMoney(tax, order.currency)}`);
  }
  if (shipping) {
    lines.push(`Shipping: ${formatMoney(shipping, order.currency)}`);
  }
  lines.push(`Total: ${formatMoney(total, order.currency)}`);
  if (order.payment_gateway_names?.length) {
    lines.push(`Gateway: ${order.payment_gateway_names.join(', ')}`);
  } else if (order.gateway) {
    lines.push(`Gateway: ${order.gateway}`);
  }
  return lines;
}

function estimateShipping(order: ShopifyOrder): number {
  const line = order.shipping_lines?.[0];
  if (!line) return 0;
  return parseFloat(line.price ?? '0') || 0;
}

function summarizeLineItems(order: ShopifyOrder): string {
  return order.line_items
    .map((item) => `${item.quantity}× ${item.title}${item.sku ? ` (${item.sku})` : ''}`)
    .join(' • ');
}

function determineDeliveryStatus(order: ShopifyOrder): string {
  if (order.fulfillment_status) {
    return normalizeStatus(order.fulfillment_status);
  }
  const firstFulfillment = order.fulfillments?.[0];
  if (firstFulfillment?.shipment_status) {
    return normalizeStatus(firstFulfillment.shipment_status);
  }
  return 'pending';
}

function deriveDeliveryMethod(order: ShopifyOrder): string | null {
  const line = order.shipping_lines?.[0];
  if (!line) return null;
  return line.title || line.source || line.code || line.carrier_identifier || null;
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
      return capitalize(normalized.replace(/_/g, ' '));
  }
}

function normalizeStatus(status: string): string {
  return capitalize(status.replace(/_/g, ' '));
}

function formatCustomerName(order: ShopifyOrder): string {
  const first = order.customer?.first_name ?? order.shipping_address?.first_name ?? '';
  const last = order.customer?.last_name ?? order.shipping_address?.last_name ?? '';
  const combined = `${first} ${last}`.trim();
  if (combined) return combined;
  if (order.customer?.email) return order.customer.email;
  return order.email ?? '';
}

function formatAddress(address?: ShopifyAddress | null): string {
  if (!address) return '';
  const parts = [
    address.name || `${address.first_name ?? ''} ${address.last_name ?? ''}`.trim(),
    address.company,
    address.address1,
    address.address2,
    [address.city, address.province || address.province_code, address.zip].filter(Boolean).join(', '),
    address.country || address.country_code,
    address.phone,
  ];
  return parts.filter(Boolean).join('\n');
}

function headingBlock(content: string): BlockObjectRequest {
  return {
    object: 'block',
    type: 'heading_2',
    heading_2: {
      rich_text: [{ type: 'text', text: { content: truncate(content) } }],
      color: 'default',
    },
  };
}

function paragraphBlock(content: string): BlockObjectRequest {
  return {
    object: 'block',
    type: 'paragraph',
    paragraph: {
      rich_text: [{ type: 'text', text: { content: truncate(content) } }],
      color: 'default',
    },
  };
}

function bulletBlock(content: string): BlockObjectRequest {
  return {
    object: 'block',
    type: 'bulleted_list_item',
    bulleted_list_item: {
      rich_text: [{ type: 'text', text: { content: truncate(content) } }],
      color: 'default',
    },
  };
}

function formatMoney(amount: number, currency = 'USD'): string {
  const safeAmount = Number.isFinite(amount) ? amount : 0;
  return `${currency} ${safeAmount.toFixed(2)}`;
}

function truncate(value: string, max = 1800): string {
  if (!value) return '';
  return value.length > max ? `${value.slice(0, max - 3)}...` : value;
}

function formatDate(value?: string | null): string {
  if (!value) return 'Unknown date';
  return new Date(value).toISOString();
}

function capitalize(value: string): string {
  return value
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

