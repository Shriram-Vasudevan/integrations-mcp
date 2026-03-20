"""Shopify provider wrapping the Shopify Admin REST API (2024-01) using httpx."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

API_VERSION = "2024-01"


def _get_shop() -> str:
    """Return the Shopify shop domain from environment."""
    shop = os.environ.get("SHOPIFY_SHOP", "")
    if not shop:
        raise RuntimeError("SHOPIFY_SHOP environment variable is not set")
    return shop


def _get_token() -> str:
    """Return the Shopify access token from environment."""
    token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("SHOPIFY_ACCESS_TOKEN environment variable is not set")
    return token


def _base_url() -> str:
    return f"https://{_get_shop()}/admin/api/{API_VERSION}"


async def _request(method: str, path: str, **kwargs) -> dict:
    """Make an authenticated request to the Shopify Admin REST API."""
    url = f"{_base_url()}/{path.lstrip('/')}"
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            url,
            headers={
                "X-Shopify-Access-Token": _get_token(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30,
            **kwargs,
        )
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {"status": "ok"}
        return resp.json()


async def _request_with_link(method: str, path: str, **kwargs):
    """Make an authenticated request and return (json, link_header) for pagination."""
    url = f"{_base_url()}/{path.lstrip('/')}"
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            url,
            headers={
                "X-Shopify-Access-Token": _get_token(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30,
            **kwargs,
        )
        resp.raise_for_status()
        link = resp.headers.get("link", "")
        return resp.json(), link


def _parse_page_info(link_header: str) -> dict:
    """Extract next/previous page_info cursors from Link header."""
    result = {}
    if not link_header:
        return result
    for part in link_header.split(","):
        part = part.strip()
        if 'rel="next"' in part:
            url_part = part.split(";")[0].strip().strip("<>")
            for param in url_part.split("?")[-1].split("&"):
                if param.startswith("page_info="):
                    result["next_page_info"] = param.split("=", 1)[1]
        elif 'rel="previous"' in part:
            url_part = part.split(";")[0].strip().strip("<>")
            for param in url_part.split("?")[-1].split("&"):
                if param.startswith("page_info="):
                    result["previous_page_info"] = param.split("=", 1)[1]
    return result


def register(mcp: FastMCP) -> None:
    """Register Shopify tools with the MCP server."""

    # --- Products ---

    @mcp.tool()
    async def shopify_list_products(
        limit: int = 50,
        title: Optional[str] = None,
        status: Optional[str] = None,
        collection_id: Optional[str] = None,
        product_type: Optional[str] = None,
        page_info: Optional[str] = None,
    ) -> dict:
        """List products from the Shopify store.

        Args:
            limit: Number of products to return (1-250, default 50).
            title: Filter by product title (optional).
            status: Filter by status: active, archived, draft (optional).
            collection_id: Filter by collection ID (optional).
            product_type: Filter by product type (optional).
            page_info: Cursor for pagination from a previous response (optional).

        Returns:
            List of products with pagination cursors.
        """
        params: dict = {"limit": min(max(1, limit), 250)}
        if page_info:
            params = {"limit": params["limit"], "page_info": page_info}
        else:
            if title:
                params["title"] = title
            if status:
                params["status"] = status
            if collection_id:
                params["collection_id"] = collection_id
            if product_type:
                params["product_type"] = product_type

        data, link = await _request_with_link("GET", "products.json", params=params)
        products = []
        for p in data.get("products", []):
            products.append({
                "id": p["id"],
                "title": p.get("title"),
                "status": p.get("status"),
                "vendor": p.get("vendor"),
                "product_type": p.get("product_type"),
                "created_at": p.get("created_at"),
                "updated_at": p.get("updated_at"),
                "variants_count": len(p.get("variants", [])),
                "images_count": len(p.get("images", [])),
                "tags": p.get("tags", ""),
            })
        result = {"products": products}
        result.update(_parse_page_info(link))
        return result

    @mcp.tool()
    async def shopify_get_product(product_id: int) -> dict:
        """Retrieve a specific Shopify product by ID.

        Args:
            product_id: The numeric product ID.

        Returns:
            Full product details including variants and images.
        """
        data = await _request("GET", f"products/{product_id}.json")
        p = data.get("product", {})
        variants = []
        for v in p.get("variants", []):
            variants.append({
                "id": v["id"],
                "title": v.get("title"),
                "price": v.get("price"),
                "sku": v.get("sku"),
                "inventory_quantity": v.get("inventory_quantity"),
                "inventory_item_id": v.get("inventory_item_id"),
                "weight": v.get("weight"),
                "weight_unit": v.get("weight_unit"),
            })
        images = []
        for img in p.get("images", []):
            images.append({
                "id": img["id"],
                "src": img.get("src"),
                "alt": img.get("alt"),
                "position": img.get("position"),
            })
        return {
            "id": p["id"],
            "title": p.get("title"),
            "body_html": p.get("body_html"),
            "vendor": p.get("vendor"),
            "product_type": p.get("product_type"),
            "status": p.get("status"),
            "tags": p.get("tags", ""),
            "created_at": p.get("created_at"),
            "updated_at": p.get("updated_at"),
            "variants": variants,
            "images": images,
        }

    @mcp.tool()
    async def shopify_create_product(
        title: str,
        body_html: Optional[str] = None,
        vendor: Optional[str] = None,
        product_type: Optional[str] = None,
        tags: Optional[str] = None,
        status: str = "draft",
        variants: Optional[list] = None,
        images: Optional[list] = None,
    ) -> dict:
        """Create a new product in the Shopify store.

        Args:
            title: Product title (required).
            body_html: HTML description of the product (optional).
            vendor: Product vendor (optional).
            product_type: Product type/category (optional).
            tags: Comma-separated tags (optional).
            status: Product status: active, archived, draft (default "draft").
            variants: List of variant dicts with keys like price, sku, title, inventory_quantity (optional).
            images: List of image dicts with keys like src, alt (optional).

        Returns:
            Created product with ID, title, status, and variants.
        """
        product: dict = {"title": title, "status": status}
        if body_html is not None:
            product["body_html"] = body_html
        if vendor:
            product["vendor"] = vendor
        if product_type:
            product["product_type"] = product_type
        if tags:
            product["tags"] = tags
        if variants:
            product["variants"] = variants
        if images:
            product["images"] = images

        data = await _request("POST", "products.json", json={"product": product})
        p = data.get("product", {})
        return {
            "id": p["id"],
            "title": p.get("title"),
            "status": p.get("status"),
            "vendor": p.get("vendor"),
            "product_type": p.get("product_type"),
            "variants": [
                {"id": v["id"], "title": v.get("title"), "price": v.get("price"), "sku": v.get("sku")}
                for v in p.get("variants", [])
            ],
            "created_at": p.get("created_at"),
        }

    @mcp.tool()
    async def shopify_update_product(
        product_id: int,
        title: Optional[str] = None,
        body_html: Optional[str] = None,
        vendor: Optional[str] = None,
        product_type: Optional[str] = None,
        tags: Optional[str] = None,
        status: Optional[str] = None,
        variants: Optional[list] = None,
        images: Optional[list] = None,
    ) -> dict:
        """Update an existing Shopify product.

        Args:
            product_id: The numeric product ID (required).
            title: New product title (optional).
            body_html: New HTML description (optional).
            vendor: New vendor (optional).
            product_type: New product type (optional).
            tags: New comma-separated tags (optional).
            status: New status: active, archived, draft (optional).
            variants: Updated list of variant dicts (optional).
            images: Updated list of image dicts (optional).

        Returns:
            Updated product details.
        """
        product: dict = {}
        if title is not None:
            product["title"] = title
        if body_html is not None:
            product["body_html"] = body_html
        if vendor is not None:
            product["vendor"] = vendor
        if product_type is not None:
            product["product_type"] = product_type
        if tags is not None:
            product["tags"] = tags
        if status is not None:
            product["status"] = status
        if variants is not None:
            product["variants"] = variants
        if images is not None:
            product["images"] = images

        if not product:
            return {"status": "no_changes", "product_id": product_id}

        data = await _request("PUT", f"products/{product_id}.json", json={"product": product})
        p = data.get("product", {})
        return {
            "id": p["id"],
            "title": p.get("title"),
            "status": p.get("status"),
            "vendor": p.get("vendor"),
            "product_type": p.get("product_type"),
            "updated_at": p.get("updated_at"),
            "variants": [
                {"id": v["id"], "title": v.get("title"), "price": v.get("price"), "sku": v.get("sku")}
                for v in p.get("variants", [])
            ],
        }

    # --- Orders ---

    @mcp.tool()
    async def shopify_list_orders(
        limit: int = 50,
        status: str = "any",
        financial_status: Optional[str] = None,
        fulfillment_status: Optional[str] = None,
        page_info: Optional[str] = None,
    ) -> dict:
        """List orders from the Shopify store.

        Args:
            limit: Number of orders to return (1-250, default 50).
            status: Order status filter: open, closed, cancelled, any (default "any").
            financial_status: Financial status filter: authorized, pending, paid, partially_paid, refunded, voided, partially_refunded, any, unpaid (optional).
            fulfillment_status: Fulfillment status filter: shipped, partial, unshipped, any, unfulfilled (optional).
            page_info: Cursor for pagination (optional).

        Returns:
            List of orders with pagination cursors.
        """
        params: dict = {"limit": min(max(1, limit), 250)}
        if page_info:
            params = {"limit": params["limit"], "page_info": page_info}
        else:
            params["status"] = status
            if financial_status:
                params["financial_status"] = financial_status
            if fulfillment_status:
                params["fulfillment_status"] = fulfillment_status

        data, link = await _request_with_link("GET", "orders.json", params=params)
        orders = []
        for o in data.get("orders", []):
            orders.append({
                "id": o["id"],
                "order_number": o.get("order_number"),
                "name": o.get("name"),
                "email": o.get("email"),
                "financial_status": o.get("financial_status"),
                "fulfillment_status": o.get("fulfillment_status"),
                "total_price": o.get("total_price"),
                "currency": o.get("currency"),
                "created_at": o.get("created_at"),
                "line_items_count": len(o.get("line_items", [])),
            })
        result = {"orders": orders}
        result.update(_parse_page_info(link))
        return result

    @mcp.tool()
    async def shopify_get_order(order_id: int) -> dict:
        """Retrieve a specific Shopify order by ID.

        Args:
            order_id: The numeric order ID.

        Returns:
            Full order details including line items, customer, and shipping.
        """
        data = await _request("GET", f"orders/{order_id}.json")
        o = data.get("order", {})
        line_items = []
        for li in o.get("line_items", []):
            line_items.append({
                "id": li["id"],
                "title": li.get("title"),
                "quantity": li.get("quantity"),
                "price": li.get("price"),
                "sku": li.get("sku"),
                "variant_id": li.get("variant_id"),
                "product_id": li.get("product_id"),
            })
        customer = None
        if o.get("customer"):
            c = o["customer"]
            customer = {
                "id": c["id"],
                "email": c.get("email"),
                "first_name": c.get("first_name"),
                "last_name": c.get("last_name"),
            }
        shipping_address = None
        if o.get("shipping_address"):
            sa = o["shipping_address"]
            shipping_address = {
                "address1": sa.get("address1"),
                "city": sa.get("city"),
                "province": sa.get("province"),
                "country": sa.get("country"),
                "zip": sa.get("zip"),
            }
        return {
            "id": o["id"],
            "order_number": o.get("order_number"),
            "name": o.get("name"),
            "email": o.get("email"),
            "financial_status": o.get("financial_status"),
            "fulfillment_status": o.get("fulfillment_status"),
            "total_price": o.get("total_price"),
            "subtotal_price": o.get("subtotal_price"),
            "total_tax": o.get("total_tax"),
            "total_discounts": o.get("total_discounts"),
            "currency": o.get("currency"),
            "created_at": o.get("created_at"),
            "updated_at": o.get("updated_at"),
            "cancelled_at": o.get("cancelled_at"),
            "closed_at": o.get("closed_at"),
            "note": o.get("note"),
            "tags": o.get("tags"),
            "line_items": line_items,
            "customer": customer,
            "shipping_address": shipping_address,
            "billing_address": o.get("billing_address"),
        }

    # --- Customers ---

    @mcp.tool()
    async def shopify_list_customers(
        limit: int = 50,
        query: Optional[str] = None,
        page_info: Optional[str] = None,
    ) -> dict:
        """List customers from the Shopify store.

        Args:
            limit: Number of customers to return (1-250, default 50).
            query: Search query to filter customers (e.g. email, name) using Shopify search syntax (optional).
            page_info: Cursor for pagination (optional).

        Returns:
            List of customers with pagination cursors.
        """
        params: dict = {"limit": min(max(1, limit), 250)}
        if page_info:
            params = {"limit": params["limit"], "page_info": page_info}
        elif query:
            data = await _request("GET", "customers/search.json", params={"query": query, "limit": params["limit"]})
            customers = []
            for c in data.get("customers", []):
                customers.append({
                    "id": c["id"],
                    "email": c.get("email"),
                    "first_name": c.get("first_name"),
                    "last_name": c.get("last_name"),
                    "orders_count": c.get("orders_count"),
                    "total_spent": c.get("total_spent"),
                    "created_at": c.get("created_at"),
                })
            return {"customers": customers}

        data, link = await _request_with_link("GET", "customers.json", params=params)
        customers = []
        for c in data.get("customers", []):
            customers.append({
                "id": c["id"],
                "email": c.get("email"),
                "first_name": c.get("first_name"),
                "last_name": c.get("last_name"),
                "orders_count": c.get("orders_count"),
                "total_spent": c.get("total_spent"),
                "created_at": c.get("created_at"),
            })
        result = {"customers": customers}
        result.update(_parse_page_info(link))
        return result

    @mcp.tool()
    async def shopify_get_customer(customer_id: int) -> dict:
        """Retrieve a specific Shopify customer by ID.

        Args:
            customer_id: The numeric customer ID.

        Returns:
            Customer details including addresses and order stats.
        """
        data = await _request("GET", f"customers/{customer_id}.json")
        c = data.get("customer", {})
        addresses = []
        for addr in c.get("addresses", []):
            addresses.append({
                "id": addr.get("id"),
                "address1": addr.get("address1"),
                "city": addr.get("city"),
                "province": addr.get("province"),
                "country": addr.get("country"),
                "zip": addr.get("zip"),
                "default": addr.get("default", False),
            })
        return {
            "id": c["id"],
            "email": c.get("email"),
            "first_name": c.get("first_name"),
            "last_name": c.get("last_name"),
            "phone": c.get("phone"),
            "orders_count": c.get("orders_count"),
            "total_spent": c.get("total_spent"),
            "state": c.get("state"),
            "verified_email": c.get("verified_email"),
            "tax_exempt": c.get("tax_exempt"),
            "tags": c.get("tags", ""),
            "created_at": c.get("created_at"),
            "updated_at": c.get("updated_at"),
            "addresses": addresses,
        }

    @mcp.tool()
    async def shopify_create_customer(
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        tags: Optional[str] = None,
        send_email_invite: bool = False,
    ) -> dict:
        """Create a new customer in the Shopify store.

        Args:
            first_name: Customer first name (optional).
            last_name: Customer last name (optional).
            email: Customer email address (optional).
            phone: Customer phone number (optional).
            tags: Comma-separated tags (optional).
            send_email_invite: Whether to send an email invite (default False).

        Returns:
            Created customer with ID and details.
        """
        customer: dict = {}
        if first_name:
            customer["first_name"] = first_name
        if last_name:
            customer["last_name"] = last_name
        if email:
            customer["email"] = email
        if phone:
            customer["phone"] = phone
        if tags:
            customer["tags"] = tags
        customer["send_email_invite"] = send_email_invite

        data = await _request("POST", "customers.json", json={"customer": customer})
        c = data.get("customer", {})
        return {
            "id": c["id"],
            "email": c.get("email"),
            "first_name": c.get("first_name"),
            "last_name": c.get("last_name"),
            "phone": c.get("phone"),
            "created_at": c.get("created_at"),
        }

    # --- Collections ---

    @mcp.tool()
    async def shopify_list_collections(
        limit: int = 50,
        collection_type: str = "custom",
        page_info: Optional[str] = None,
    ) -> dict:
        """List collections from the Shopify store.

        Args:
            limit: Number of collections to return (1-250, default 50).
            collection_type: Type of collections: "custom" or "smart" (default "custom").
            page_info: Cursor for pagination (optional).

        Returns:
            List of collections with pagination cursors.
        """
        endpoint = "custom_collections.json" if collection_type == "custom" else "smart_collections.json"
        key = "custom_collections" if collection_type == "custom" else "smart_collections"

        params: dict = {"limit": min(max(1, limit), 250)}
        if page_info:
            params = {"limit": params["limit"], "page_info": page_info}

        data, link = await _request_with_link("GET", endpoint, params=params)
        collections = []
        for col in data.get(key, []):
            collections.append({
                "id": col["id"],
                "title": col.get("title"),
                "handle": col.get("handle"),
                "body_html": col.get("body_html"),
                "published_at": col.get("published_at"),
                "updated_at": col.get("updated_at"),
                "sort_order": col.get("sort_order"),
            })
        result = {"collections": collections, "collection_type": collection_type}
        result.update(_parse_page_info(link))
        return result

    # --- Inventory ---

    @mcp.tool()
    async def shopify_get_inventory_levels(
        inventory_item_ids: Optional[str] = None,
        location_ids: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """Get inventory levels for items or locations.

        Args:
            inventory_item_ids: Comma-separated list of inventory item IDs (optional, but one of inventory_item_ids or location_ids is required).
            location_ids: Comma-separated list of location IDs (optional, but one of inventory_item_ids or location_ids is required).
            limit: Number of results to return (1-250, default 50).

        Returns:
            List of inventory levels with item IDs, location IDs, and quantities.
        """
        if not inventory_item_ids and not location_ids:
            return {"error": "At least one of inventory_item_ids or location_ids is required"}

        params: dict = {"limit": min(max(1, limit), 250)}
        if inventory_item_ids:
            params["inventory_item_ids"] = inventory_item_ids
        if location_ids:
            params["location_ids"] = location_ids

        data = await _request("GET", "inventory_levels.json", params=params)
        levels = []
        for lvl in data.get("inventory_levels", []):
            levels.append({
                "inventory_item_id": lvl.get("inventory_item_id"),
                "location_id": lvl.get("location_id"),
                "available": lvl.get("available"),
                "updated_at": lvl.get("updated_at"),
            })
        return {"inventory_levels": levels}
