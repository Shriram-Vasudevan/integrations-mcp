"""Cat Facts provider using catfact.ninja (free, no auth)."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://catfact.ninja"


def register(mcp: FastMCP) -> None:
    """Register cat fact tools with the MCP server."""

    @mcp.tool()
    async def get_cat_fact() -> dict:
        """Get a random cat fact from catfact.ninja.

        Returns:
            A random cat fact and its length.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/fact")
            resp.raise_for_status()
            data = resp.json()
        return {"fact": data["fact"], "length": data["length"]}

    @mcp.tool()
    async def get_cat_facts(limit: int = 5) -> dict:
        """Get multiple random cat facts from catfact.ninja.

        Args:
            limit: Maximum number of cat facts to return (default 5).

        Returns:
            A list of cat facts.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BASE_URL}/facts",
                params={"limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
        return {
            "facts": [
                {"fact": item["fact"], "length": item["length"]}
                for item in data.get("data", [])
            ],
        }

    @mcp.tool()
    async def get_cat_breeds(limit: int = 10) -> dict:
        """Get a list of cat breeds from catfact.ninja.

        Args:
            limit: Maximum number of breeds to return (default 10).

        Returns:
            A list of cat breeds with their details.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BASE_URL}/breeds",
                params={"limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
        return {
            "breeds": [
                {
                    "breed": item.get("breed"),
                    "country": item.get("country"),
                    "origin": item.get("origin"),
                    "coat": item.get("coat"),
                    "pattern": item.get("pattern"),
                }
                for item in data.get("data", [])
            ],
        }
