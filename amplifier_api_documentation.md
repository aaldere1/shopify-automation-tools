# Amplifier® API Documentation

**API Base URL:** `https://api.amplifier.com`
**Authentication:** API Key
**API Key:** `YOUR_AMPLIFIER_API_KEY`
**Documentation Source:** https://amplifier.docs.apiary.io/

---

## Authentication

The Amplifier API uses API key authentication. Include your API key in the request headers:

```
Authorization: Bearer YOUR_AMPLIFIER_API_KEY
```

or

```
X-API-Key: YOUR_AMPLIFIER_API_KEY
```

---

## Common Headers

All requests should include:

```
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY
```

---

## API Endpoints

### Base Information

#### GET /
- **Description:** Get API information and available endpoints
- **Method:** GET
- **Authentication:** Required
- **Response:** API metadata and available routes

---

### Products

#### GET /products
- **Description:** List all products
- **Method:** GET
- **Authentication:** Required
- **Parameters:**
  - `limit` (optional): Number of results per page (default: 50, max: 250)
  - `page` (optional): Page number (default: 1)
  - `status` (optional): Filter by status (`active`, `archived`)
- **Response:**
  ```json
  {
    "products": [
      {
        "id": "string",
        "name": "string",
        "sku": "string",
        "price": number,
        "inventory": number,
        "status": "string",
        "created_at": "ISO 8601 date",
        "updated_at": "ISO 8601 date"
      }
    ],
    "pagination": {
      "page": number,
      "limit": number,
      "total": number,
      "pages": number
    }
  }
  ```

#### GET /products/{id}
- **Description:** Get a specific product by ID
- **Method:** GET
- **Authentication:** Required
- **Parameters:**
  - `id` (required): Product ID
- **Response:** Single product object

#### POST /products
- **Description:** Create a new product
- **Method:** POST
- **Authentication:** Required
- **Body:**
  ```json
  {
    "name": "string",
    "sku": "string",
    "price": number,
    "inventory": number,
    "description": "string",
    "category": "string"
  }
  ```
- **Response:** Created product object

#### PUT /products/{id}
- **Description:** Update an existing product
- **Method:** PUT
- **Authentication:** Required
- **Parameters:**
  - `id` (required): Product ID
- **Body:** Same as POST (partial updates allowed)
- **Response:** Updated product object

#### DELETE /products/{id}
- **Description:** Delete a product
- **Method:** DELETE
- **Authentication:** Required
- **Parameters:**
  - `id` (required): Product ID
- **Response:**
  ```json
  {
    "success": true,
    "message": "Product deleted successfully"
  }
  ```

---

### Orders

#### GET /orders
- **Description:** List all orders
- **Method:** GET
- **Authentication:** Required
- **Parameters:**
  - `limit` (optional): Number of results per page (default: 50, max: 250)
  - `page` (optional): Page number (default: 1)
  - `status` (optional): Filter by status
  - `from_date` (optional): Start date (ISO 8601)
  - `to_date` (optional): End date (ISO 8601)
- **Response:**
  ```json
  {
    "orders": [
      {
        "id": "string",
        "order_number": "string",
        "customer": {
          "name": "string",
          "email": "string"
        },
        "items": [],
        "total": number,
        "status": "string",
        "created_at": "ISO 8601 date"
      }
    ],
    "pagination": {...}
  }
  ```

#### GET /orders/{id}
- **Description:** Get a specific order by ID
- **Method:** GET
- **Authentication:** Required
- **Parameters:**
  - `id` (required): Order ID
- **Response:** Single order object with full details

#### POST /orders
- **Description:** Create a new order
- **Method:** POST
- **Authentication:** Required
- **Body:**
  ```json
  {
    "customer": {
      "name": "string",
      "email": "string",
      "phone": "string"
    },
    "items": [
      {
        "product_id": "string",
        "quantity": number,
        "price": number
      }
    ],
    "shipping_address": {...},
    "billing_address": {...}
  }
  ```
- **Response:** Created order object

#### PUT /orders/{id}
- **Description:** Update an order (status, shipping, etc.)
- **Method:** PUT
- **Authentication:** Required
- **Parameters:**
  - `id` (required): Order ID
- **Body:** Partial order object
- **Response:** Updated order object

---

### Inventory

#### GET /inventory
- **Description:** Get inventory levels for all products
- **Method:** GET
- **Authentication:** Required
- **Parameters:**
  - `product_id` (optional): Filter by specific product
  - `location` (optional): Filter by location
- **Response:**
  ```json
  {
    "inventory": [
      {
        "product_id": "string",
        "sku": "string",
        "quantity": number,
        "location": "string",
        "updated_at": "ISO 8601 date"
      }
    ]
  }
  ```

#### PUT /inventory/{product_id}
- **Description:** Update inventory for a product
- **Method:** PUT
- **Authentication:** Required
- **Parameters:**
  - `product_id` (required): Product ID
- **Body:**
  ```json
  {
    "quantity": number,
    "location": "string",
    "operation": "set|adjust"
  }
  ```
- **Response:** Updated inventory object

---

### Customers

#### GET /customers
- **Description:** List all customers
- **Method:** GET
- **Authentication:** Required
- **Parameters:**
  - `limit` (optional): Number of results per page
  - `page` (optional): Page number
  - `search` (optional): Search by name or email
- **Response:**
  ```json
  {
    "customers": [
      {
        "id": "string",
        "name": "string",
        "email": "string",
        "phone": "string",
        "orders_count": number,
        "total_spent": number,
        "created_at": "ISO 8601 date"
      }
    ],
    "pagination": {...}
  }
  ```

#### GET /customers/{id}
- **Description:** Get a specific customer
- **Method:** GET
- **Authentication:** Required
- **Parameters:**
  - `id` (required): Customer ID
- **Response:** Single customer object with full details

---

### Webhooks

#### GET /webhooks
- **Description:** List all registered webhooks
- **Method:** GET
- **Authentication:** Required
- **Response:**
  ```json
  {
    "webhooks": [
      {
        "id": "string",
        "event": "string",
        "url": "string",
        "active": boolean,
        "created_at": "ISO 8601 date"
      }
    ]
  }
  ```

#### POST /webhooks
- **Description:** Register a new webhook
- **Method:** POST
- **Authentication:** Required
- **Body:**
  ```json
  {
    "event": "order.created|order.updated|product.created|...",
    "url": "https://your-server.com/webhook",
    "secret": "string"
  }
  ```
- **Response:** Created webhook object

#### DELETE /webhooks/{id}
- **Description:** Delete a webhook
- **Method:** DELETE
- **Authentication:** Required
- **Parameters:**
  - `id` (required): Webhook ID
- **Response:** Success message

---

## Available Webhook Events

- `order.created` - Triggered when a new order is created
- `order.updated` - Triggered when an order is updated
- `order.cancelled` - Triggered when an order is cancelled
- `product.created` - Triggered when a new product is created
- `product.updated` - Triggered when a product is updated
- `product.deleted` - Triggered when a product is deleted
- `inventory.updated` - Triggered when inventory levels change
- `customer.created` - Triggered when a new customer is created
- `customer.updated` - Triggered when a customer is updated

---

## Error Responses

All error responses follow this format:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

### Common Error Codes

- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Invalid or missing API key
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

---

## Rate Limiting

- **Rate Limit:** 120 requests per minute per API key
- **Headers:**
  - `X-RateLimit-Limit`: Maximum requests per minute
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Unix timestamp when the rate limit resets

When rate limit is exceeded, the API returns `429 Too Many Requests` with a `Retry-After` header.

---

## Pagination

All list endpoints support pagination:

**Request Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 50, max: 250)

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 1000,
    "pages": 20,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## Best Practices

1. **Always handle rate limiting** - Implement exponential backoff when hitting rate limits
2. **Use webhooks for real-time updates** - More efficient than polling
3. **Cache responses** - Reduce API calls by caching frequently accessed data
4. **Batch operations** - Use bulk endpoints when available
5. **Error handling** - Always check response status codes and handle errors gracefully
6. **Security** - Never expose your API key in client-side code

---

## Integration with Shopify

When integrating Amplifier with Shopify:

1. **Sync Products:** Use Amplifier API to fetch products and push to Shopify
2. **Sync Inventory:** Keep inventory levels synchronized between systems
3. **Order Management:** Create orders in Amplifier when Shopify orders are placed
4. **Customer Data:** Sync customer information between platforms

See `amplifier_shopify_integration.py` for implementation examples.

---

## Support

For API support and questions:
- Documentation: https://amplifier.docs.apiary.io/
- API Key: Stored securely in your integration scripts

---

*Last Updated: 2025-11-14*
*API Version: v1*
