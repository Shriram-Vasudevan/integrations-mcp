"""Poetry provider using PoetryDB (https://poetrydb.org) — free, no auth required."""

import httpx
from mcp.server.fastmcp import FastMCP

POETRYDB_URL = "https://poetrydb.org"


async def _get(path: str) -> dict | list:
    """Make a GET request to PoetryDB and return the JSON response."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{POETRYDB_URL}{path}")
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register poetry tools with the MCP server."""

    @mcp.tool()
    async def search_poems_by_author(author: str) -> dict:
        """Search for poems by a given author using PoetryDB.

        Args:
            author: The poet's name (or partial name) to search for.

        Returns:
            A list of poems with their titles and first few lines.
        """
        data = await _get(f"/author/{author}")
        if isinstance(data, dict) and data.get("status"):
            return {"error": True, "message": data.get("reason", "Not found")}
        poems = [
            {
                "title": poem.get("title"),
                "author": poem.get("author"),
                "lines": poem.get("lines", [])[:4],
                "linecount": poem.get("linecount"),
            }
            for poem in data
        ]
        return {"count": len(poems), "poems": poems}

    @mcp.tool()
    async def get_poem(title: str, author: str) -> dict:
        """Get the full text of a specific poem by title and author.

        Args:
            title: The title of the poem.
            author: The author of the poem.

        Returns:
            The full poem text including title, author, and all lines.
        """
        data = await _get(f"/title,author/{title};{author}")
        if isinstance(data, dict) and data.get("status"):
            return {"error": True, "message": data.get("reason", "Not found")}
        if not data:
            return {"error": True, "message": "No poem found"}
        poem = data[0]
        return {
            "title": poem.get("title"),
            "author": poem.get("author"),
            "lines": poem.get("lines"),
            "linecount": poem.get("linecount"),
        }

    @mcp.tool()
    async def get_random_poem() -> dict:
        """Get a random poem from PoetryDB.

        Returns:
            A random poem with its title, author, and full text.
        """
        data = await _get("/random")
        if isinstance(data, dict) and data.get("status"):
            return {"error": True, "message": data.get("reason", "Unknown error")}
        poem = data[0] if isinstance(data, list) else data
        return {
            "title": poem.get("title"),
            "author": poem.get("author"),
            "lines": poem.get("lines"),
            "linecount": poem.get("linecount"),
        }
