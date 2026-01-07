#!/usr/bin/env python3
"""
Amplifier API Client
A Python client for interacting with the Amplifier API

Usage:
    from amplifier_client import AmplifierClient

    client = AmplifierClient(api_key="your-api-key")
    products = client.get_products()
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time


class AmplifierAPIError(Exception):
    """Custom exception for Amplifier API errors"""
    pass


class AmplifierClient:
    def __init__(self, api_key: str, base_url: str = "https://api.amplifier.com"):
        """
        Initialize Amplifier API client

        Args:
            api_key: Your Amplifier API key
            base_url: API base URL (default: https://api.amplifier.com)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

        # Encode API key to Base64 for Basic authentication
        import base64
        encoded_key = base64.b64encode(self.api_key.encode()).decode()

        self.session.headers.update({
            'Authorization': f'Basic {encoded_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'Amplifier-Python-Client/1.0'
        })

    def _request(self,
                 method: str,
                 endpoint: str,
                 params: Optional[Dict] = None,
                 data: Optional[Dict] = None,
                 retry_count: int = 3) -> Dict[str, Any]:
        """
        Make HTTP request to Amplifier API with error handling and retries

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., '/products')
            params: Query parameters
            data: Request body data
            retry_count: Number of retries for failed requests

        Returns:
            Response data as dictionary

        Raises:
            AmplifierAPIError: If the request fails after retries
        """
        url = f"{self.base_url}{endpoint}"

        for attempt in range(retry_count):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    timeout=30
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    print(f"⚠️  Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                if attempt == retry_count - 1:
                    error_msg = f"HTTP error: {e}"
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            error_data = e.response.json()
                            error_msg = error_data.get('error', {}).get('message', str(e))
                        except:
                            error_msg = e.response.text or str(e)
                    raise AmplifierAPIError(error_msg)
                time.sleep(2 ** attempt)  # Exponential backoff

            except requests.exceptions.RequestException as e:
                if attempt == retry_count - 1:
                    raise AmplifierAPIError(f"Request failed: {str(e)}")
                time.sleep(2 ** attempt)

        raise AmplifierAPIError("Max retries exceeded")

    # Items (Products)

    def get_items(self,
                  query: Optional[str] = None,
                  sku: Optional[str] = None,
                  name: Optional[str] = None,
                  discontinued: Optional[bool] = None,
                  page: int = 1,
                  per_page: int = 50) -> Dict[str, Any]:
        """
        Get list of items (products)

        Args:
            query: Search by SKU or Name
            sku: Search by SKU
            name: Search by Name
            discontinued: Filter by discontinued status
            page: Page number
            per_page: Number of results per page

        Returns:
            Dictionary containing items list and pagination info
        """
        params = {'page': page, 'per_page': per_page}
        if query:
            params['query'] = query
        if sku:
            params['sku'] = sku
        if name:
            params['name'] = name
        if discontinued is not None:
            params['discontinued'] = str(discontinued).lower()

        return self._request('GET', '/items/', params=params)

    # Alias for compatibility
    def get_products(self, limit: int = 50, page: int = 1, status: Optional[str] = None):
        """Alias for get_items for backward compatibility"""
        return self.get_items(page=page, per_page=limit)

    def get_product(self, product_id: str) -> Dict[str, Any]:
        """
        Get a specific product by ID

        Args:
            product_id: Product ID

        Returns:
            Product object
        """
        return self._request('GET', f'/products/{product_id}')

    def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new product

        Args:
            product_data: Product information (name, sku, price, etc.)

        Returns:
            Created product object
        """
        return self._request('POST', '/products', data=product_data)

    def update_product(self, product_id: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing product

        Args:
            product_id: Product ID
            product_data: Updated product information

        Returns:
            Updated product object
        """
        return self._request('PUT', f'/products/{product_id}', data=product_data)

    def delete_product(self, product_id: str) -> Dict[str, Any]:
        """
        Delete a product

        Args:
            product_id: Product ID

        Returns:
            Success message
        """
        return self._request('DELETE', f'/products/{product_id}')

    # Orders

    def get_orders(self,
                   limit: int = 50,
                   page: int = 1,
                   status: Optional[str] = None,
                   from_date: Optional[str] = None,
                   to_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get list of orders

        Args:
            limit: Number of results per page
            page: Page number
            status: Filter by status
            from_date: Start date (ISO 8601 format)
            to_date: End date (ISO 8601 format)

        Returns:
            Dictionary containing orders list and pagination info
        """
        params = {'limit': limit, 'page': page}
        if status:
            params['status'] = status
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date

        return self._request('GET', '/orders', params=params)

    def get_order(self, order_id: str) -> Dict[str, Any]:
        """
        Get a specific order by ID

        Args:
            order_id: Order ID

        Returns:
            Order object with full details
        """
        return self._request('GET', f'/orders/{order_id}')

    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new order

        Args:
            order_data: Order information (customer, items, etc.)

        Returns:
            Created order object
        """
        return self._request('POST', '/orders', data=order_data)

    def update_order(self, order_id: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an order

        Args:
            order_id: Order ID
            order_data: Updated order information

        Returns:
            Updated order object
        """
        return self._request('PUT', f'/orders/{order_id}', data=order_data)

    # Inventory

    def get_inventory(self,
                      product_id: Optional[str] = None,
                      location: Optional[str] = None) -> Dict[str, Any]:
        """
        Get inventory levels

        Args:
            product_id: Filter by specific product
            location: Filter by location

        Returns:
            Inventory data
        """
        params = {}
        if product_id:
            params['product_id'] = product_id
        if location:
            params['location'] = location

        return self._request('GET', '/inventory', params=params)

    def update_inventory(self,
                         product_id: str,
                         quantity: int,
                         location: Optional[str] = None,
                         operation: str = 'set') -> Dict[str, Any]:
        """
        Update inventory for a product

        Args:
            product_id: Product ID
            quantity: New quantity
            location: Inventory location
            operation: 'set' (replace) or 'adjust' (add/subtract)

        Returns:
            Updated inventory object
        """
        data = {
            'quantity': quantity,
            'operation': operation
        }
        if location:
            data['location'] = location

        return self._request('PUT', f'/inventory/{product_id}', data=data)

    # Customers

    def get_customers(self,
                      limit: int = 50,
                      page: int = 1,
                      search: Optional[str] = None) -> Dict[str, Any]:
        """
        Get list of customers

        Args:
            limit: Number of results per page
            page: Page number
            search: Search by name or email

        Returns:
            Dictionary containing customers list and pagination info
        """
        params = {'limit': limit, 'page': page}
        if search:
            params['search'] = search

        return self._request('GET', '/customers', params=params)

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """
        Get a specific customer

        Args:
            customer_id: Customer ID

        Returns:
            Customer object with full details
        """
        return self._request('GET', f'/customers/{customer_id}')

    # Webhooks

    def get_webhooks(self) -> Dict[str, Any]:
        """
        Get list of registered webhooks

        Returns:
            List of webhooks
        """
        return self._request('GET', '/webhooks')

    def create_webhook(self, event: str, url: str, secret: Optional[str] = None) -> Dict[str, Any]:
        """
        Register a new webhook

        Args:
            event: Event type (e.g., 'order.created')
            url: Webhook callback URL
            secret: Optional webhook secret for verification

        Returns:
            Created webhook object
        """
        data = {'event': event, 'url': url}
        if secret:
            data['secret'] = secret

        return self._request('POST', '/webhooks', data=data)

    def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Delete a webhook

        Args:
            webhook_id: Webhook ID

        Returns:
            Success message
        """
        return self._request('DELETE', f'/webhooks/{webhook_id}')

    # Bulk Operations

    def get_all_items(self,
                      query: Optional[str] = None,
                      discontinued: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Fetch all items across all pages

        Args:
            query: Search query
            discontinued: Filter by discontinued status

        Returns:
            List of all items
        """
        all_items = []
        page = 1
        per_page = 250  # Maximum per page

        print("📥 Fetching all items from Amplifier...")

        while True:
            response = self.get_items(
                query=query,
                discontinued=discontinued,
                page=page,
                per_page=per_page
            )
            items = response.get('data', [])

            if not items:
                break

            all_items.extend(items)
            print(f"   Page {page}: Fetched {len(items)} items (Total: {len(all_items)})")

            # Check if there are more pages
            total_pages = response.get('total_pages', 1)
            if page >= total_pages:
                break

            page += 1
            time.sleep(0.5)  # Rate limiting courtesy

        print(f"✅ Total items fetched: {len(all_items)}\n")
        return all_items

    # Alias for compatibility
    def get_all_products(self, status: Optional[str] = None):
        """Alias for get_all_items for backward compatibility"""
        discontinued = None if status is None else (status == 'archived')
        return self.get_all_items(discontinued=discontinued)

    def get_all_orders(self,
                       status: Optional[str] = None,
                       from_date: Optional[str] = None,
                       to_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch all orders across all pages

        Args:
            status: Filter by status
            from_date: Start date
            to_date: End date

        Returns:
            List of all orders
        """
        all_orders = []
        page = 1
        limit = 250

        print("📥 Fetching all orders from Amplifier...")

        while True:
            response = self.get_orders(
                limit=limit,
                page=page,
                status=status,
                from_date=from_date,
                to_date=to_date
            )
            orders = response.get('orders', [])

            if not orders:
                break

            all_orders.extend(orders)
            print(f"   Page {page}: Fetched {len(orders)} orders (Total: {len(all_orders)})")

            pagination = response.get('pagination', {})
            if not pagination.get('has_next', False):
                break

            page += 1
            time.sleep(0.5)

        print(f"✅ Total orders fetched: {len(all_orders)}\n")
        return all_orders


# Example usage
if __name__ == "__main__":
    # Initialize client
    API_KEY = "YOUR_AMPLIFIER_API_KEY"
    client = AmplifierClient(api_key=API_KEY)

    try:
        # Example: Get all products
        products = client.get_all_products()
        print(f"Found {len(products)} products")

        # Example: Get orders from the last 30 days
        from_date = (datetime.now() - timedelta(days=30)).isoformat()
        orders = client.get_all_orders(from_date=from_date)
        print(f"Found {len(orders)} orders in the last 30 days")

    except AmplifierAPIError as e:
        print(f"❌ API Error: {e}")
