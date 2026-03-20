"""Dad jokes provider using icanhazdadjoke.com (free, no auth)."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://icanhazdadjoke.com"
HEADERS = {"Accept": "application/json"}


def register(mcp: FastMCP) -> None:
    """Register dad joke tools with the MCP server."""

    @mcp.tool()
    async def get_dad_joke() -> dict:
        """Get a random dad joke from icanhazdadjoke.com.

        Returns:
            The joke id and joke text.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(BASE_URL, headers=HEADERS)
            resp.raise_for_status()
            data = resp.json()
        return {"id": data["id"], "joke": data["joke"]}

    @mcp.tool()
    async def search_dad_jokes(term: str, limit: int = 5) -> dict:
        """Search for dad jokes matching a term on icanhazdadjoke.com.

        Args:
            term: The search term to find matching jokes.
            limit: Maximum number of jokes to return (default 5).

        Returns:
            A list of matching jokes with their ids and text.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BASE_URL}/search",
                headers=HEADERS,
                params={"term": term, "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
        return {
            "total_jokes": data.get("total_jokes", 0),
            "jokes": [
                {"id": j["id"], "joke": j["joke"]}
                for j in data.get("results", [])
            ],
        }
