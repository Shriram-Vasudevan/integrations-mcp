"""PokeAPI provider — Pokémon data via https://pokeapi.co/api/v2/."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://pokeapi.co/api/v2"


async def _get(path: str) -> dict:
    """Make a GET request to the PokeAPI."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{BASE_URL}{path}")
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register Pokémon tools with the MCP server."""

    @mcp.tool()
    async def get_pokemon(name_or_id: str) -> dict:
        """Get detailed information about a Pokémon by name or Pokédex ID.

        Args:
            name_or_id: The Pokémon name (e.g. "pikachu") or Pokédex ID (e.g. "25").

        Returns:
            A dict with the Pokémon's types, stats, abilities, sprites, height,
            weight, and base experience.
        """
        data = await _get(f"/pokemon/{name_or_id.lower().strip()}")
        sprites = data.get("sprites", {})
        return {
            "name": data["name"],
            "id": data["id"],
            "types": [t["type"]["name"] for t in data["types"]],
            "stats": {s["stat"]["name"]: s["base_stat"] for s in data["stats"]},
            "abilities": [a["ability"]["name"] for a in data["abilities"]],
            "sprites": {
                "front_default": sprites.get("front_default"),
                "front_shiny": sprites.get("front_shiny"),
                "back_default": sprites.get("back_default"),
                "back_shiny": sprites.get("back_shiny"),
            },
            "height": data["height"],
            "weight": data["weight"],
            "base_experience": data["base_experience"],
        }

    @mcp.tool()
    async def search_pokemon(query: str) -> dict:
        """Search for Pokémon whose names match a query string.

        Fetches the full list of Pokémon names and filters by substring match.

        Args:
            query: A search string to match against Pokémon names (e.g. "char", "pika").

        Returns:
            A dict with matching Pokémon names and the total number of matches.
        """
        data = await _get("/pokemon?limit=100000&offset=0")
        query_lower = query.lower().strip()
        matches = [
            {"name": p["name"], "url": p["url"]}
            for p in data["results"]
            if query_lower in p["name"]
        ]
        return {
            "query": query,
            "count": len(matches),
            "results": matches,
        }

    @mcp.tool()
    async def get_pokemon_type(type_name: str) -> dict:
        """List all Pokémon of a given type.

        Args:
            type_name: The type name (e.g. "fire", "water", "electric").

        Returns:
            A dict with the type name and a list of all Pokémon that have that type.
        """
        data = await _get(f"/type/{type_name.lower().strip()}")
        return {
            "type": data["name"],
            "id": data["id"],
            "count": len(data["pokemon"]),
            "pokemon": [
                {"name": p["pokemon"]["name"], "slot": p["slot"]}
                for p in data["pokemon"]
            ],
        }
