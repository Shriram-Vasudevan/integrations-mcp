"""Numbers provider using numbersapi.com — free, no auth required."""

import httpx
from mcp.server.fastmcp import FastMCP

NUMBERS_API_URL = "http://numbersapi.com"
VALID_TYPES = ("trivia", "math", "date", "year")


async def _fetch(path: str) -> dict:
    """Fetch a JSON fact from the Numbers API."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{NUMBERS_API_URL}/{path}", params={"json": ""})
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register number-fact tools with the MCP server."""

    @mcp.tool()
    async def get_number_fact(number: int, type: str = "trivia") -> str:
        """Get a fact about a specific number.

        Args:
            number: The number to get a fact about.
            type: Fact type — trivia, math, date, or year.

        Returns:
            A fact about the given number.
        """
        if type not in VALID_TYPES:
            return f"Invalid type '{type}'. Must be one of: {', '.join(VALID_TYPES)}"
        data = await _fetch(f"{number}/{type}")
        return data.get("text", str(data))

    @mcp.tool()
    async def get_random_fact(type: str = "trivia") -> str:
        """Get a fact about a random number.

        Args:
            type: Fact type — trivia, math, date, or year.

        Returns:
            A fact about a random number.
        """
        if type not in VALID_TYPES:
            return f"Invalid type '{type}'. Must be one of: {', '.join(VALID_TYPES)}"
        data = await _fetch(f"random/{type}")
        return data.get("text", str(data))

    @mcp.tool()
    async def get_date_fact(month: int, day: int) -> str:
        """Get a historical fact about a specific date.

        Args:
            month: Month (1-12).
            day: Day of the month (1-31).

        Returns:
            A historical fact about the given date.
        """
        data = await _fetch(f"{month}/{day}/date")
        return data.get("text", str(data))
