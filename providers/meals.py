"""TheMealDB provider — search, lookup, and random meal recipes."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://www.themealdb.com/api/json/v1/1"


def _parse_meal(meal: dict) -> dict:
    """Extract relevant fields from a raw MealDB meal object."""
    ingredients = []
    for i in range(1, 21):
        ingredient = (meal.get(f"strIngredient{i}") or "").strip()
        measure = (meal.get(f"strMeasure{i}") or "").strip()
        if ingredient:
            ingredients.append(f"{measure} {ingredient}".strip())
    return {
        "id": meal.get("idMeal"),
        "name": meal.get("strMeal"),
        "category": meal.get("strCategory"),
        "area": meal.get("strArea"),
        "instructions": meal.get("strInstructions"),
        "ingredients": ingredients,
        "thumbnail": meal.get("strMealThumb"),
    }


def register(mcp: FastMCP) -> None:
    """Register TheMealDB tools with the MCP server."""

    @mcp.tool()
    async def search_meals(query: str) -> dict:
        """Search for meals by name.

        Args:
            query: The meal name (or partial name) to search for.

        Returns:
            A list of matching meals with name, category, instructions, and ingredients.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/search.php", params={"s": query})
            resp.raise_for_status()
            data = resp.json()
        meals = data.get("meals")
        if not meals:
            return {"meals": [], "message": "No meals found."}
        return {"meals": [_parse_meal(m) for m in meals]}

    @mcp.tool()
    async def get_meal(id: str) -> dict:
        """Look up a meal by its MealDB ID.

        Args:
            id: The MealDB meal ID.

        Returns:
            The meal details including name, category, instructions, and ingredients.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/lookup.php", params={"i": id})
            resp.raise_for_status()
            data = resp.json()
        meals = data.get("meals")
        if not meals:
            return {"error": True, "message": f"No meal found with id {id}."}
        return _parse_meal(meals[0])

    @mcp.tool()
    async def get_random_meal() -> dict:
        """Get a random meal recipe.

        Returns:
            A random meal with name, category, instructions, and ingredients.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/random.php")
            resp.raise_for_status()
            data = resp.json()
        meals = data.get("meals")
        if not meals:
            return {"error": True, "message": "No meal returned."}
        return _parse_meal(meals[0])

    @mcp.tool()
    async def list_meal_categories() -> dict:
        """List all available meal categories.

        Returns:
            A list of meal categories with name, description, and thumbnail.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/categories.php")
            resp.raise_for_status()
            data = resp.json()
        categories = data.get("categories", [])
        return {
            "categories": [
                {
                    "id": c.get("idCategory"),
                    "name": c.get("strCategory"),
                    "description": c.get("strCategoryDescription"),
                    "thumbnail": c.get("strCategoryThumb"),
                }
                for c in categories
            ]
        }
