"""Joke provider using JokeAPI v2 (safe mode only)."""

import httpx
from mcp.server.fastmcp import FastMCP

JOKEAPI_URL = "https://v2.jokeapi.dev"
SAFE_FLAGS = "nsfw,religious,political,racist,sexist,explicit"
CATEGORIES = ["Programming", "Misc", "Dark", "Pun", "Spooky", "Christmas"]


async def _fetch_joke(category: str, joke_type: str | None) -> dict:
    """Fetch a joke from JokeAPI with safe-mode blacklist flags."""
    params: dict[str, str] = {"blacklistFlags": SAFE_FLAGS}
    if joke_type in ("single", "twopart"):
        params["type"] = joke_type
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{JOKEAPI_URL}/joke/{category}", params=params)
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register joke tools with the MCP server."""

    @mcp.tool()
    async def get_joke(category: str = "Any", joke_type: str | None = None) -> dict:
        """Get a random joke from JokeAPI (safe mode).

        Args:
            category: Joke category — Any, Programming, Misc, Dark, Pun, Spooky, or Christmas.
            joke_type: Optional filter — "single" for one-liners, "twopart" for setup/delivery.

        Returns:
            The joke with its category, type, content, and content flags.
        """
        data = await _fetch_joke(category, joke_type)
        if data.get("error"):
            return {"error": True, "message": data.get("message", "Unknown error")}
        result: dict = {
            "category": data.get("category"),
            "type": data.get("type"),
        }
        if data.get("type") == "single":
            result["joke"] = data.get("joke")
        else:
            result["setup"] = data.get("setup")
            result["delivery"] = data.get("delivery")
        result["flags"] = data.get("flags", {})
        result["id"] = data.get("id")
        return result

    @mcp.tool()
    async def get_joke_categories() -> dict:
        """List available joke categories from JokeAPI.

        Returns:
            A list of valid category names that can be passed to get_joke.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{JOKEAPI_URL}/categories")
            resp.raise_for_status()
            data = resp.json()
        if data.get("error"):
            return {"error": True, "message": data.get("message", "Unknown error")}
        return {
            "categories": data.get("categories", CATEGORIES),
            "category_aliases": data.get("categoryAliases", {}),
        }
