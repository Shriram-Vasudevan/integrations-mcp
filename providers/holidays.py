"""Public Holiday provider using the free Nager.Date API — no auth required."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://date.nager.at/api/v3"


def register(mcp: FastMCP) -> None:
    """Register public holiday tools with the MCP server."""

    @mcp.tool()
    async def get_public_holidays(year: int, country_code: str) -> dict:
        """Get public holidays for a given year and country.

        Args:
            year: The year to retrieve holidays for (e.g. 2026).
            country_code: ISO 3166-1 alpha-2 country code (e.g. "US", "DE", "GB").

        Returns:
            List of public holidays with name, date, local name, and scope.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/PublicHolidays/{year}/{country_code}")
            resp.raise_for_status()
            data = resp.json()

        holidays = [
            {
                "date": h["date"],
                "name": h["name"],
                "localName": h["localName"],
                "global": h.get("global", False),
                "type": "Global" if h.get("global", False) else "Regional",
            }
            for h in data
        ]

        return {
            "year": year,
            "country_code": country_code,
            "total": len(holidays),
            "holidays": holidays,
        }

    @mcp.tool()
    async def list_available_countries() -> dict:
        """List all countries supported by the public holidays API.

        Returns:
            List of available countries with their code and name.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/AvailableCountries")
            resp.raise_for_status()
            data = resp.json()

        countries = [
            {"countryCode": c["countryCode"], "name": c["name"]}
            for c in data
        ]

        return {
            "total": len(countries),
            "countries": countries,
        }
