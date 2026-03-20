"""Wikipedia provider using the Wikipedia REST API (no key required)."""

from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://en.wikipedia.org/api/rest_v1"
USER_AGENT = "integrations-mcp/0.1.0 (MCP provider; no-contact)"


def register(mcp: FastMCP) -> None:
    """Register Wikipedia tools with the MCP server."""

    @mcp.tool()
    async def search_wikipedia(query: str, limit: int = 5) -> dict[str, Any]:
        """Search Wikipedia articles by keyword.

        Args:
            query: Search term or phrase.
            limit: Maximum number of results (1-50, default 5).

        Returns:
            Search results with page titles and snippets.
        """
        limit = max(1, min(limit, 50))
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{BASE_URL}/search/page",
                params={"q": query, "limit": limit},
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for page in data.get("pages", []):
            results.append({
                "title": page.get("title"),
                "key": page.get("key"),
                "description": page.get("description"),
                "snippet": page.get("excerpt"),
            })

        return {
            "query": query,
            "result_count": len(results),
            "results": results,
        }

    @mcp.tool()
    async def get_wikipedia_article(title: str) -> dict[str, Any]:
        """Get the summary/extract of a Wikipedia article.

        Args:
            title: Article title (e.g. "Python (programming language)").
                   Spaces are accepted and will be converted automatically.

        Returns:
            Article extract with title, description, summary text, and URL.
        """
        encoded = title.replace(" ", "_")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{BASE_URL}/page/summary/{encoded}",
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
            if resp.status_code == 404:
                return {"error": f"No Wikipedia article found for '{title}'."}
            resp.raise_for_status()
            data = resp.json()

        result: dict[str, Any] = {
            "title": data.get("title"),
            "description": data.get("description"),
            "extract": data.get("extract"),
            "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
        }
        thumbnail = data.get("thumbnail")
        if thumbnail:
            result["thumbnail_url"] = thumbnail.get("source")
        return result
