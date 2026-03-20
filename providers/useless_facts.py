"""Useless Facts provider using uselessfacts.jsph.pl (free, no auth)."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://uselessfacts.jsph.pl/api/v2/facts/random"


def register(mcp: FastMCP) -> None:
    """Register useless facts tools with the MCP server."""

    @mcp.tool()
    async def get_random_fact(language: str = "en") -> dict:
        """Get a random useless fact from uselessfacts.jsph.pl.

        Args:
            language: Language for the fact ('en' for English, 'de' for German).

        Returns:
            The fact text, permalink, and source URL.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(BASE_URL, params={"language": language})
            resp.raise_for_status()
            data = resp.json()
        return {
            "text": data["text"],
            "permalink": data["permalink"],
            "source_url": data["source_url"],
        }
