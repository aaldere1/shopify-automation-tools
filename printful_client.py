#!/usr/bin/env python3
"""
Printful API Client
A Python client for interacting with the Printful API v2

Usage:
    from printful_client import PrintfulClient

    client = PrintfulClient(access_token="your-access-token")
    products = client.get_products()
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import time


class PrintfulAPIError(Exception):
    """Custom exception for Printful API errors"""
    pass


class PrintfulClient:
    def __init__(self, access_token: str, base_url: str = "https://api.printful.com"):
        """
        Initialize Printful API client

        Args:
            access_token: Your Printful OAuth access token
            base_url: API base URL (default: https://api.printful.com)
        """
        self.access_token = access_token
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'Printful-Python-Client/1.0'
        })

    def _request(self,
                 method: str,
                 endpoint: str,
                 params: Optional[Dict] = None,
                 data: Optional[Dict] = None,
                 retry_count: int = 3) -> Dict[str, Any]:
        """
        Make HTTP request to Printful API with error handling and retries

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            endpoint: API endpoint (e.g., '/v2/products')
            params: Query parameters
            data: Request body data
            retry_count: Number of retries for failed requests

        Returns:
            Response data as dictionary

        Raises:
            PrintfulAPIError: If the request fails after retries
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

                # Printful API v2 returns data in a specific format
                result = response.json()
                return result

            except requests.exceptions.HTTPError as e:
                if attempt == retry_count - 1:
                    error_msg = f"HTTP error: {e}"
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            error_data = e.response.json()
                            error_msg = error_data.get('error', {}).get('message', str(e))
                        except:
                            error_msg = e.response.text or str(e)
                    raise PrintfulAPIError(error_msg)
                time.sleep(2 ** attempt)  # Exponential backoff

            except requests.exceptions.RequestException as e:
                if attempt == retry_count - 1:
                    raise PrintfulAPIError(f"Request failed: {str(e)}")
                time.sleep(2 ** attempt)

        raise PrintfulAPIError("Max retries exceeded")

    # Stores

    def get_stores(self, store_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get list of stores or specific store

        Args:
            store_id: Optional store ID to filter

        Returns:
            Dictionary containing stores data
        """
        params = {}
        if store_id:
            params['store_id'] = store_id

        return self._request('GET', '/v2/stores', params=params)

    def get_store(self, store_id: int) -> Dict[str, Any]:
        """
        Get a specific store by ID

        Args:
            store_id: Store ID

        Returns:
            Store object
        """
        return self._request('GET', f'/v2/stores/{store_id}')

    # Catalog - Products

    def get_products(self,
                     category_ids: Optional[List[int]] = None,
                     colors: Optional[List[str]] = None,
                     limit: int = 100,
                     offset: int = 0,
                     new: Optional[bool] = None,
                     placements: Optional[List[str]] = None,
                     selling_region: Optional[str] = None,
                     sort_direction: str = 'asc',
                     sort_type: Optional[str] = None,
                     techniques: Optional[List[str]] = None,
                     destination_country: Optional[str] = None,
                     locale: Optional[str] = None) -> Dict[str, Any]:
        """
        Get list of catalog products

        Args:
            category_ids: Filter by category IDs
            colors: Filter by colors
            limit: Number of results (max 100)
            offset: Pagination offset
            new: Filter new products
            placements: Filter by placement types
            selling_region: Selling region filter
            sort_direction: Sort direction ('asc' or 'desc')
            sort_type: Sort type
            techniques: Filter by techniques
            destination_country: Destination country code
            locale: Locale code

        Returns:
            Dictionary containing products list and pagination info
        """
        params = {'limit': limit, 'offset': offset, 'sort_direction': sort_direction}

        if category_ids:
            params['category_ids'] = ','.join(map(str, category_ids))
        if colors:
            params['colors'] = ','.join(colors)
        if new is not None:
            params['new'] = str(new).lower()
        if placements:
            params['placements'] = ','.join(placements)
        if selling_region:
            params['selling_region'] = selling_region
        if sort_type:
            params['sort_type'] = sort_type
        if techniques:
            params['techniques'] = ','.join(techniques)
        if destination_country:
            params['destination_country'] = destination_country
        if locale:
            params['locale'] = locale

        return self._request('GET', '/v2/catalog-products', params=params)

    def get_product(self,
                    product_id: int,
                    selling_region: Optional[str] = None,
                    locale: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a specific catalog product

        Args:
            product_id: Product ID
            selling_region: Selling region
            locale: Locale code

        Returns:
            Product object
        """
        params = {}
        if selling_region:
            params['selling_region'] = selling_region
        if locale:
            params['locale'] = locale

        return self._request('GET', f'/v2/catalog-products/{product_id}', params=params)

    def get_product_variants(self,
                            product_id: int,
                            selling_region: Optional[str] = None,
                            locale: Optional[str] = None) -> Dict[str, Any]:
        """
        Get variants for a specific product

        Args:
            product_id: Product ID
            selling_region: Selling region
            locale: Locale code

        Returns:
            List of product variants
        """
        params = {}
        if selling_region:
            params['selling_region'] = selling_region
        if locale:
            params['locale'] = locale

        return self._request('GET', f'/v2/catalog-products/{product_id}/catalog-variants', params=params)

    def get_variant(self, variant_id: int) -> Dict[str, Any]:
        """
        Get a specific catalog variant

        Args:
            variant_id: Variant ID

        Returns:
            Variant object
        """
        return self._request('GET', f'/v2/catalog-variants/{variant_id}')

    # Catalog - Categories

    def get_categories(self) -> Dict[str, Any]:
        """
        Get list of catalog categories

        Returns:
            List of categories
        """
        return self._request('GET', '/v2/catalog-categories')

    def get_category(self, category_id: int) -> Dict[str, Any]:
        """
        Get a specific category

        Args:
            category_id: Category ID

        Returns:
            Category object
        """
        return self._request('GET', f'/v2/catalog-categories/{category_id}')

    # Orders

    def get_orders(self,
                   store_id: Optional[int] = None,
                   limit: int = 20,
                   offset: int = 0,
                   status: Optional[str] = None) -> Dict[str, Any]:
        """
        Get list of orders

        Args:
            store_id: Filter by store ID
            limit: Number of results
            offset: Pagination offset
            status: Filter by status

        Returns:
            Dictionary containing orders list and pagination
        """
        params = {'limit': limit, 'offset': offset}
        if store_id:
            params['store_id'] = store_id
        if status:
            params['status'] = status

        return self._request('GET', '/v2/orders', params=params)

    def get_order(self, order_id: str, store_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get a specific order

        Args:
            order_id: Order ID
            store_id: Store ID

        Returns:
            Order object
        """
        params = {}
        if store_id:
            params['store_id'] = store_id

        return self._request('GET', f'/v2/orders/{order_id}', params=params)

    def create_order(self, order_data: Dict[str, Any], store_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a new order

        Args:
            order_data: Order data
            store_id: Store ID

        Returns:
            Created order object
        """
        params = {}
        if store_id:
            params['store_id'] = store_id

        return self._request('POST', '/v2/orders', params=params, data=order_data)

    def update_order(self,
                     order_id: str,
                     order_data: Dict[str, Any],
                     store_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Update an existing order

        Args:
            order_id: Order ID
            order_data: Updated order data
            store_id: Store ID

        Returns:
            Updated order object
        """
        params = {}
        if store_id:
            params['store_id'] = store_id

        return self._request('PATCH', f'/v2/orders/{order_id}', params=params, data=order_data)

    def delete_order(self, order_id: str, store_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Delete an order

        Args:
            order_id: Order ID
            store_id: Store ID

        Returns:
            Success response
        """
        params = {}
        if store_id:
            params['store_id'] = store_id

        return self._request('DELETE', f'/v2/orders/{order_id}', params=params)

    # Files

    def get_files(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Get list of files from library

        Args:
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of files
        """
        params = {'limit': limit, 'offset': offset}
        return self._request('GET', '/v2/files', params=params)

    def get_file(self, file_id: int) -> Dict[str, Any]:
        """
        Get a specific file

        Args:
            file_id: File ID

        Returns:
            File object
        """
        return self._request('GET', f'/v2/files/{file_id}')

    # Webhooks

    def get_webhooks(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Get list of webhooks

        Args:
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of webhooks
        """
        params = {'limit': limit, 'offset': offset}
        return self._request('GET', '/v2/webhooks', params=params)

    # Shipping

    def calculate_shipping_rates(self, shipping_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate shipping rates

        Args:
            shipping_data: Shipping calculation data

        Returns:
            Shipping rates
        """
        return self._request('POST', '/v2/shipping-rates', data=shipping_data)

    # Countries

    def get_countries(self) -> Dict[str, Any]:
        """
        Get list of countries

        Returns:
            List of countries
        """
        return self._request('GET', '/v2/countries')

    # Warehouse Products

    def get_warehouse_products(self, store_id: Optional[int] = None, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Get warehouse products

        Args:
            store_id: Store ID (required by API)
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of warehouse products
        """
        params = {'limit': limit, 'offset': offset}
        if store_id:
            params['store_id'] = store_id
        return self._request('GET', '/v2/warehouse-products', params=params)

    def get_warehouse_product(self, warehouse_product_id: int) -> Dict[str, Any]:
        """
        Get a specific warehouse product

        Args:
            warehouse_product_id: Warehouse product ID

        Returns:
            Warehouse product object
        """
        return self._request('GET', f'/v2/warehouse-products/{warehouse_product_id}')

    # Bulk Operations

    def get_all_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch all products across all pages

        Args:
            **kwargs: Arguments to pass to get_products

        Returns:
            List of all products
        """
        all_products = []
        offset = 0
        limit = 100  # Maximum per page

        print("📥 Fetching all products from Printful...")

        while True:
            response = self.get_products(limit=limit, offset=offset, **kwargs)

            # Printful v2 API structure - data is directly a list
            products = response.get('data', [])

            if not products:
                break

            all_products.extend(products)
            print(f"   Fetched {len(products)} products (Total: {len(all_products)})")

            # Check if there are more pages
            paging = response.get('paging', {})
            total = paging.get('total', 0)

            if offset + limit >= total:
                break

            offset += limit
            time.sleep(0.5)  # Rate limiting courtesy

        print(f"✅ Total products fetched: {len(all_products)}\n")
        return all_products

    def get_all_orders(self, store_id: Optional[int] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch all orders across all pages

        Args:
            store_id: Store ID filter
            **kwargs: Additional arguments

        Returns:
            List of all orders
        """
        all_orders = []
        offset = 0
        limit = 100

        print("📥 Fetching all orders from Printful...")

        while True:
            response = self.get_orders(store_id=store_id, limit=limit, offset=offset, **kwargs)

            # Printful v2 API structure - data is directly a list
            orders = response.get('data', [])

            if not orders:
                break

            all_orders.extend(orders)
            print(f"   Fetched {len(orders)} orders (Total: {len(all_orders)})")

            paging = response.get('paging', {})
            total = paging.get('total', 0)

            if offset + limit >= total:
                break

            offset += limit
            time.sleep(0.5)

        print(f"✅ Total orders fetched: {len(all_orders)}\n")
        return all_orders


# Example usage
if __name__ == "__main__":
    # Initialize client
    ACCESS_TOKEN = "YOUR_PRINTFUL_TOKEN"
    client = PrintfulClient(access_token=ACCESS_TOKEN)

    try:
        # Example: Get stores
        stores = client.get_stores()
        print(f"Stores: {stores}")

        # Example: Get products
        products = client.get_products(limit=10)
        print(f"\nProducts: {products}")

    except PrintfulAPIError as e:
        print(f"❌ API Error: {e}")
