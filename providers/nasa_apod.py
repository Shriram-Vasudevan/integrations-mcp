"""NASA Astronomy Picture of the Day (APOD) provider."""

import os

import httpx
from mcp.server.fastmcp import FastMCP

APOD_URL = "https://api.nasa.gov/planetary/apod"


def _api_key() -> str:
    """Return the NASA API key from env or fall back to DEMO_KEY."""
    return os.environ.get("NASA_API_KEY", "DEMO_KEY")


def register(mcp: FastMCP) -> None:
    """Register NASA APOD tools with the MCP server."""

    @mcp.tool()
    async def get_apod(date: str | None = None) -> dict:
        """Get the NASA Astronomy Picture of the Day.

        Args:
            date: Optional date in YYYY-MM-DD format. Omit for today's picture.

        Returns:
            Title, explanation, image/video URL, media type, and date.
        """
        params: dict = {"api_key": _api_key()}
        if date:
            params["date"] = date
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(APOD_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        return {
            "title": data.get("title"),
            "explanation": data.get("explanation"),
            "url": data.get("url"),
            "media_type": data.get("media_type"),
            "date": data.get("date"),
        }

    @mcp.tool()
    async def get_apod_range(start_date: str, end_date: str) -> list[dict]:
        """Get NASA Astronomy Pictures of the Day for a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            List of APOD entries with title, explanation, URL, media type, and date.
        """
        params: dict = {
            "api_key": _api_key(),
            "start_date": start_date,
            "end_date": end_date,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(APOD_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        if not isinstance(data, list):
            data = [data] if data else []
        return [
            {
                "title": entry.get("title"),
                "explanation": entry.get("explanation"),
                "url": entry.get("url"),
                "media_type": entry.get("media_type"),
                "date": entry.get("date"),
            }
            for entry in data
        ]
