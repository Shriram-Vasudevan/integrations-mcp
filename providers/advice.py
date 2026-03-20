"""Advice Slip provider — random and searchable life advice."""

import httpx
from mcp.server.fastmcp import FastMCP

ADVICE_BASE_URL = "https://api.adviceslip.com"


def register(mcp: FastMCP) -> None:
    """Register advice tools with the MCP server."""

    @mcp.tool()
    async def get_random_advice() -> dict:
        """Get a random piece of advice from the Advice Slip API.

        Returns:
            The advice id and text.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{ADVICE_BASE_URL}/advice")
            resp.raise_for_status()
            data = resp.json()
        slip = data.get("slip", {})
        return {"id": slip.get("id"), "advice": slip.get("advice")}

    @mcp.tool()
    async def search_advice(query: str) -> dict:
        """Search for advice matching a query term.

        Args:
            query: The search term to find relevant advice.

        Returns:
            A list of matching advice slips with their ids and text.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{ADVICE_BASE_URL}/advice/search/{query}")
            resp.raise_for_status()
            data = resp.json()
        if "message" in data:
            return {"total_results": 0, "results": [], "query": query}
        slips = data.get("slips", [])
        return {
            "total_results": int(data.get("total_results", len(slips))),
            "query": query,
            "results": [
                {"id": s.get("id"), "advice": s.get("advice")} for s in slips
            ],
        }
