"""Name analysis provider using Agify.io and Nationalize.io APIs."""

import httpx
from mcp.server.fastmcp import FastMCP

AGIFY_URL = "https://api.agify.io"
NATIONALIZE_URL = "https://api.nationalize.io"


def register(mcp: FastMCP) -> None:
    """Register name analysis tools with the MCP server."""

    @mcp.tool()
    async def predict_age_from_name(name: str) -> dict:
        """Predict the age of a person based on their first name using the Agify.io API.

        Args:
            name: A first name to analyze (e.g. "michael", "maria").

        Returns:
            The predicted age and the number of data samples used for the prediction.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(AGIFY_URL, params={"name": name})
            resp.raise_for_status()
            data = resp.json()
        return {
            "name": data.get("name"),
            "predicted_age": data.get("age"),
            "sample_count": data.get("count"),
        }

    @mcp.tool()
    async def predict_nationality_from_name(name: str) -> dict:
        """Predict the nationality of a person based on their first name using the Nationalize.io API.

        Args:
            name: A first name to analyze (e.g. "michael", "maria").

        Returns:
            The top 3 most likely nationalities with their probabilities.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(NATIONALIZE_URL, params={"name": name})
            resp.raise_for_status()
            data = resp.json()
        countries = data.get("country", [])[:3]
        return {
            "name": data.get("name"),
            "top_nationalities": [
                {
                    "country_id": c.get("country_id"),
                    "probability": round(c.get("probability", 0), 4),
                }
                for c in countries
            ],
        }
