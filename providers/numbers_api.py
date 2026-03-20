"""Numbers API provider — fun facts about numbers and dates.

Uses http://numbersapi.com (no authentication required).
"""

import httpx
from mcp.server.fastmcp import FastMCP

NUMBERS_API_URL = "http://numbersapi.com"
VALID_TYPES = ("trivia", "math", "date", "year")


async def _fetch(path: str) -> dict:
    """Fetch a fact from the Numbers API and return structured output."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{NUMBERS_API_URL}/{path}",
            params={"json": ""},
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register Numbers API tools with the MCP server."""

    @mcp.tool()
    async def get_number_fact(number: int, type: str = "trivia") -> dict:
        """Get a fact about a specific number.

        Args:
            number: The number to get a fact about.
            type: Type of fact — trivia, math, date, or year.

        Returns:
            A dict with the number, type, fact text, and whether the number was found.
        """
        if type not in VALID_TYPES:
            return {"error": True, "message": f"Invalid type '{type}'. Must be one of: {', '.join(VALID_TYPES)}"}
        return await _fetch(f"{number}/{type}")

    @mcp.tool()
    async def get_date_fact(month: int, day: int) -> dict:
        """Get a fact about a date (month/day).

        Args:
            month: Month (1-12).
            day: Day of the month (1-31).

        Returns:
            A dict with the date, fact text, and whether the date was found.
        """
        return await _fetch(f"{month}/{day}/date")

    @mcp.tool()
    async def get_random_fact(type: str = "trivia") -> dict:
        """Get a random number fact.

        Args:
            type: Type of fact — trivia, math, date, or year.

        Returns:
            A dict with a random number, type, fact text, and whether it was found.
        """
        if type not in VALID_TYPES:
            return {"error": True, "message": f"Invalid type '{type}'. Must be one of: {', '.join(VALID_TYPES)}"}
        return await _fetch(f"random/{type}")
