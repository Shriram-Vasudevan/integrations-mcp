"""Quotes provider using the Quotable API (https://api.quotable.io)."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.quotable.io"


def _format_quote(data: dict) -> dict:
    return {
        "content": data.get("content"),
        "author": data.get("author"),
        "tags": data.get("tags", []),
    }


def register(mcp: FastMCP) -> None:
    """Register quote tools with the MCP server."""

    @mcp.tool()
    async def get_random_quote(
        tags: str | None = None, author: str | None = None
    ) -> dict:
        """Get a random inspirational quote.

        Args:
            tags: Optional comma-separated tag names to filter by (e.g. "love,happiness").
            author: Optional author slug to filter by (e.g. "albert-einstein").

        Returns:
            A quote with its content, author, and tags.
        """
        params: dict[str, str] = {}
        if tags:
            params["tags"] = tags
        if author:
            params["author"] = author
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/random", params=params)
            resp.raise_for_status()
            data = resp.json()
        return _format_quote(data)

    @mcp.tool()
    async def list_quote_tags() -> dict:
        """List all available quote tags with their quote counts.

        Returns:
            A list of tags, each with its name and the number of quotes in that tag.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/tags")
            resp.raise_for_status()
            data = resp.json()
        return {
            "tags": [
                {"name": t.get("name"), "quote_count": t.get("quoteCount")}
                for t in data
            ]
        }

    @mcp.tool()
    async def search_quotes(query: str, limit: int = 5) -> dict:
        """Search for quotes matching a query string.

        Args:
            query: The search term to find relevant quotes.
            limit: Maximum number of quotes to return (default 5).

        Returns:
            A list of matching quotes with content, author, and tags.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BASE_URL}/search/quotes",
                params={"query": query, "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
        results = data.get("results", [])
        return {
            "results": [_format_quote(q) for q in results],
            "total_count": data.get("totalCount", len(results)),
        }
