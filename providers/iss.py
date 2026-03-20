"""ISS Tracker provider using Open Notify API."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "http://api.open-notify.org"


def register(mcp: FastMCP) -> None:
    """Register ISS tracking tools with the MCP server."""

    @mcp.tool()
    async def get_iss_location() -> dict:
        """Get the current location of the International Space Station.

        Returns:
            Current ISS latitude, longitude, and Unix timestamp.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/iss-now.json")
            resp.raise_for_status()
            data = resp.json()
        position = data["iss_position"]
        return {
            "latitude": float(position["latitude"]),
            "longitude": float(position["longitude"]),
            "timestamp": data["timestamp"],
        }

    @mcp.tool()
    async def get_people_in_space() -> dict:
        """List all astronauts currently in space and which craft they are on.

        Returns:
            Number of people in space and a list of astronauts with their craft.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/astros.json")
            resp.raise_for_status()
            data = resp.json()
        return {
            "number": data["number"],
            "people": [
                {"name": p["name"], "craft": p["craft"]}
                for p in data["people"]
            ],
        }

    @mcp.tool()
    async def get_iss_pass_times(lat: float, lon: float, n: int = 5) -> dict:
        """Predict upcoming ISS passes over a given location.

        Args:
            lat: Latitude of the location (-80 to 80).
            lon: Longitude of the location (-180 to 180).
            n: Number of passes to predict (1-100, default 5).

        Returns:
            List of predicted ISS pass times with duration and risetime.
        """
        n = max(1, min(n, 100))
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BASE_URL}/iss-pass.json",
                params={"lat": lat, "lon": lon, "n": n},
            )
            resp.raise_for_status()
            data = resp.json()
        passes = data.get("response", [])
        return {
            "latitude": lat,
            "longitude": lon,
            "passes": [
                {
                    "risetime": p["risetime"],
                    "duration_seconds": p["duration"],
                }
                for p in passes
            ],
        }
