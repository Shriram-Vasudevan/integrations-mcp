"""Name analysis provider using the free Agify, Genderize, and Nationalize APIs — no auth required."""

import asyncio

import httpx
from mcp.server.fastmcp import FastMCP

AGIFY_URL = "https://api.agify.io"
GENDERIZE_URL = "https://api.genderize.io"
NATIONALIZE_URL = "https://api.nationalize.io"


def register(mcp: FastMCP) -> None:
    """Register name analysis tools with the MCP server."""

    @mcp.tool()
    async def predict_age(name: str) -> dict:
        """Predict the age of a person based on their first name.

        Args:
            name: A first name to analyze.

        Returns:
            Predicted age and the sample count used for the prediction.
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
    async def predict_gender(name: str) -> dict:
        """Predict the gender of a person based on their first name.

        Args:
            name: A first name to analyze.

        Returns:
            Predicted gender and the probability of the prediction.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(GENDERIZE_URL, params={"name": name})
            resp.raise_for_status()
            data = resp.json()

        return {
            "name": data.get("name"),
            "gender": data.get("gender"),
            "probability": data.get("probability"),
            "sample_count": data.get("count"),
        }

    @mcp.tool()
    async def predict_nationality(name: str) -> dict:
        """Predict the nationality of a person based on their first name.

        Args:
            name: A first name to analyze.

        Returns:
            Top 3 predicted countries with their probabilities.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(NATIONALIZE_URL, params={"name": name})
            resp.raise_for_status()
            data = resp.json()

        countries = data.get("country", [])[:3]
        return {
            "name": data.get("name"),
            "top_countries": [
                {"country_id": c.get("country_id"), "probability": c.get("probability")}
                for c in countries
            ],
        }

    @mcp.tool()
    async def analyze_name(name: str) -> dict:
        """Perform a full name analysis combining age, gender, and nationality predictions.

        Args:
            name: A first name to analyze.

        Returns:
            Combined results from age, gender, and nationality predictions.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            age_resp, gender_resp, nat_resp = await asyncio.gather(
                client.get(AGIFY_URL, params={"name": name}),
                client.get(GENDERIZE_URL, params={"name": name}),
                client.get(NATIONALIZE_URL, params={"name": name}),
            )

        age_resp.raise_for_status()
        gender_resp.raise_for_status()
        nat_resp.raise_for_status()

        age_data = age_resp.json()
        gender_data = gender_resp.json()
        nat_data = nat_resp.json()

        countries = nat_data.get("country", [])[:3]

        return {
            "name": name,
            "age": {
                "predicted_age": age_data.get("age"),
                "sample_count": age_data.get("count"),
            },
            "gender": {
                "gender": gender_data.get("gender"),
                "probability": gender_data.get("probability"),
                "sample_count": gender_data.get("count"),
            },
            "nationality": {
                "top_countries": [
                    {"country_id": c.get("country_id"), "probability": c.get("probability")}
                    for c in countries
                ],
            },
        }
