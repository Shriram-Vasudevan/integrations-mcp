"""Open Food Facts provider — product lookup, search, and nutrition data."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://world.openfoodfacts.org"
USER_AGENT = "integrations-mcp/0.1.0"


def _extract_product(product: dict) -> dict:
    """Extract relevant fields from a raw Open Food Facts product object."""
    nutriments = product.get("nutriments", {})
    return {
        "barcode": product.get("code"),
        "name": product.get("product_name"),
        "brand": product.get("brands"),
        "ingredients_text": product.get("ingredients_text"),
        "nutrition_grade": product.get("nutrition_grades"),
        "categories": product.get("categories"),
        "image_url": product.get("image_url"),
        "nutriments": {
            "energy_kcal_100g": nutriments.get("energy-kcal_100g"),
            "fat_100g": nutriments.get("fat_100g"),
            "saturated_fat_100g": nutriments.get("saturated-fat_100g"),
            "carbohydrates_100g": nutriments.get("carbohydrates_100g"),
            "sugars_100g": nutriments.get("sugars_100g"),
            "proteins_100g": nutriments.get("proteins_100g"),
            "salt_100g": nutriments.get("salt_100g"),
            "fiber_100g": nutriments.get("fiber_100g"),
        },
    }


def register(mcp: FastMCP) -> None:
    """Register Open Food Facts tools with the MCP server."""

    @mcp.tool()
    async def get_product(barcode: str) -> dict:
        """Get full product details from Open Food Facts by barcode.

        Args:
            barcode: The product barcode (EAN/UPC).

        Returns:
            Product details including name, brand, ingredients, nutrition grade, and nutriments.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v2/product/{barcode}.json",
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            data = resp.json()
        if data.get("status") == 0:
            return {"error": True, "message": f"No product found for barcode {barcode}."}
        return _extract_product(data.get("product", {}))

    @mcp.tool()
    async def search_products(query: str, limit: int = 10) -> dict:
        """Search for food products on Open Food Facts.

        Args:
            query: Search terms (e.g. "nutella", "organic milk").
            limit: Maximum number of results to return (1-50, default 10).

        Returns:
            A list of matching products with name, brand, nutrition grade, and nutriments.
        """
        limit = max(1, min(limit, 50))
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BASE_URL}/cgi/search.pl",
                params={
                    "search_terms": query,
                    "json": 1,
                    "page_size": limit,
                },
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            data = resp.json()
        products = data.get("products", [])
        if not products:
            return {"products": [], "message": "No products found."}
        return {
            "count": data.get("count", len(products)),
            "products": [_extract_product(p) for p in products],
        }

    @mcp.tool()
    async def get_product_nutrition(barcode: str) -> dict:
        """Get a clean nutrition summary for a product by barcode.

        Returns calories, fat, carbohydrates, protein, and salt per 100g.

        Args:
            barcode: The product barcode (EAN/UPC).

        Returns:
            Nutrition summary per 100g including calories, fat, carbs, protein, and salt.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v2/product/{barcode}.json",
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            data = resp.json()
        if data.get("status") == 0:
            return {"error": True, "message": f"No product found for barcode {barcode}."}
        product = data.get("product", {})
        nutriments = product.get("nutriments", {})
        return {
            "barcode": product.get("code"),
            "name": product.get("product_name"),
            "nutrition_grade": product.get("nutrition_grades"),
            "per_100g": {
                "calories_kcal": nutriments.get("energy-kcal_100g"),
                "fat_g": nutriments.get("fat_100g"),
                "saturated_fat_g": nutriments.get("saturated-fat_100g"),
                "carbohydrates_g": nutriments.get("carbohydrates_100g"),
                "sugars_g": nutriments.get("sugars_100g"),
                "protein_g": nutriments.get("proteins_100g"),
                "salt_g": nutriments.get("salt_100g"),
                "fiber_g": nutriments.get("fiber_100g"),
            },
        }
