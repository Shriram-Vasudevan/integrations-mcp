"""Number Facts provider using numbersapi.com — free, no auth required."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "http://numbersapi.com"
VALID_TYPES = ("trivia", "math", "date", "year")


async def _fetch(path: str) -> dict:
    """Fetch a JSON fact from numbersapi.com."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{BASE_URL}/{path}", params={"json": ""})
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register number-facts tools with the MCP server."""

    @mcp.tool()
    async def get_number_fact(number: int, type: str = "trivia") -> dict:
        """Get a fact about a specific number.

        Args:
            number: The number to look up.
            type: Fact type — trivia, math, date, or year.

        Returns:
            A JSON object with the number, fact text, type, and whether it was found.
        """
        if type not in VALID_TYPES:
            return {"error": True, "message": f"Invalid type '{type}'. Must be one of: {', '.join(VALID_TYPES)}"}
        return await _fetch(f"{number}/{type}")

    @mcp.tool()
    async def get_random_fact(type: str = "trivia") -> dict:
        """Get a fact about a random number.

        Args:
            type: Fact type — trivia, math, date, or year.

        Returns:
            A JSON object with the number, fact text, type, and whether it was found.
        """
        if type not in VALID_TYPES:
            return {"error": True, "message": f"Invalid type '{type}'. Must be one of: {', '.join(VALID_TYPES)}"}
        return await _fetch(f"random/{type}")

    @mcp.tool()
    async def get_date_fact(month: int, day: int) -> dict:
        """Get a fact about a calendar date.

        Args:
            month: Month (1-12).
            day: Day of the month (1-31).

        Returns:
            A JSON object with the date fact, number, type, and whether it was found.
        """
        if not (1 <= month <= 12):
            return {"error": True, "message": "Month must be between 1 and 12."}
        if not (1 <= day <= 31):
            return {"error": True, "message": "Day must be between 1 and 31."}
        return await _fetch(f"{month}/{day}/date")
