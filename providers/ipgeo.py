"""IP geolocation provider using ipapi.co (free tier, no auth required)."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://ipapi.co"

_FIELDS = ("ip", "city", "region", "country_name", "latitude", "longitude", "timezone", "org")


def _format(data: dict) -> dict:
    """Extract a consistent response dict from ipapi.co data."""
    return {
        "ip": data.get("ip"),
        "city": data.get("city"),
        "region": data.get("region"),
        "country": data.get("country_name"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "timezone": data.get("timezone"),
        "org": data.get("org"),
    }


def _extract_error(data: dict) -> str | None:
    """Return an error message if the API response indicates failure."""
    if data.get("error"):
        return data.get("reason", "Unknown error")
    return None


def register(mcp: FastMCP) -> None:
    """Register IP geolocation tools with the MCP server."""

    @mcp.tool()
    async def get_my_ip_info() -> dict:
        """Get geolocation info for the caller's own public IP address.

        Uses the free ipapi.co service (no API key required).

        Returns:
            IP address, city, region, country, latitude, longitude, timezone, and org/ISP.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BASE_URL}/json/")
            resp.raise_for_status()
            data = resp.json()

        error = _extract_error(data)
        if error:
            return {"error": error}
        return _format(data)

    @mcp.tool()
    async def get_ip_info(ip: str) -> dict:
        """Get geolocation info for a specific IP address.

        Uses the free ipapi.co service (no API key required).

        Args:
            ip: IPv4 or IPv6 address to look up.

        Returns:
            IP address, city, region, country, latitude, longitude, timezone, and org/ISP.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BASE_URL}/{ip}/json/")
            resp.raise_for_status()
            data = resp.json()

        error = _extract_error(data)
        if error:
            return {"error": error, "ip": ip}
        return _format(data)
