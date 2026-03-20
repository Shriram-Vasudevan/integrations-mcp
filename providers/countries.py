"""REST Countries provider using the restcountries.com v3.1 API."""

import time
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://restcountries.com/v3.1"
CACHE_TTL = 3600  # 1 hour in seconds
USER_AGENT = "integrations-mcp/0.1.0"

# In-memory cache: key -> (timestamp, data)
_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    """Return cached value if it exists and hasn't expired."""
    entry = _cache.get(key)
    if entry is None:
        return None
    ts, data = entry
    if time.monotonic() - ts > CACHE_TTL:
        del _cache[key]
        return None
    return data


def _cache_set(key: str, data: Any) -> None:
    _cache[key] = (time.monotonic(), data)


async def _get(path: str) -> list[dict]:
    """Make a GET request to the REST Countries API with caching."""
    cached = _cache_get(path)
    if cached is not None:
        return cached
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{BASE_URL}{path}",
            headers={"User-Agent": USER_AGENT},
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
    _cache_set(path, data)
    return data


def _summarize(country: dict) -> dict:
    """Extract key fields from a country record."""
    currencies = country.get("currencies", {})
    currency_list = [
        {"code": code, "name": info.get("name", ""), "symbol": info.get("symbol", "")}
        for code, info in currencies.items()
    ]
    languages = country.get("languages", {})
    flags = country.get("flags", {})
    name_data = country.get("name", {})
    return {
        "name": name_data.get("common", ""),
        "official_name": name_data.get("official", ""),
        "cca2": country.get("cca2", ""),
        "cca3": country.get("cca3", ""),
        "capital": country.get("capital", []),
        "region": country.get("region", ""),
        "subregion": country.get("subregion", ""),
        "population": country.get("population", 0),
        "area_km2": country.get("area", 0),
        "currencies": currency_list,
        "languages": languages,
        "flag_emoji": country.get("flag", ""),
        "flags": {"png": flags.get("png", ""), "svg": flags.get("svg", "")},
        "timezones": country.get("timezones", []),
        "borders": country.get("borders", []),
        "latlng": country.get("latlng", []),
    }


def register(mcp: FastMCP) -> None:
    """Register REST Countries tools with the MCP server."""

    @mcp.tool()
    async def get_country(name: str) -> dict:
        """Get detailed information about a country by name.

        Args:
            name: Country common name (e.g. "France", "United States").

        Returns:
            Country details including capital, population, region, flag URLs,
            currencies, and languages.
        """
        value = name.strip()
        # Try exact match first, then partial
        results = await _get(f"/name/{value}?fullText=true")
        if not results:
            results = await _get(f"/name/{value}")
        if not results:
            return {"error": f"No country found for '{name}'."}
        return _summarize(results[0])

    @mcp.tool()
    async def get_country_by_code(code: str) -> dict:
        """Get detailed information about a country by ISO 3166 alpha-2 or alpha-3 code.

        Args:
            code: ISO 3166-1 alpha-2 (e.g. "FR") or alpha-3 (e.g. "FRA") country code.

        Returns:
            Country details including capital, population, region, flag URLs,
            currencies, and languages.
        """
        value = code.strip().upper()
        if not (len(value) in (2, 3) and value.isalpha()):
            return {"error": f"Invalid ISO code '{code}'. Must be 2 or 3 letters."}
        results = await _get(f"/alpha/{value}")
        if not results:
            return {"error": f"No country found for code '{code}'."}
        return _summarize(results[0])

    @mcp.tool()
    async def list_countries_by_region(region: str) -> list[dict]:
        """List all countries in a given region.

        Args:
            region: Region name — one of Africa, Americas, Asia, Europe, Oceania.

        Returns:
            List of countries in the region with summary information.
        """
        results = await _get(f"/region/{region.strip().lower()}")
        if not results:
            return []
        return [_summarize(c) for c in results]

    @mcp.tool()
    async def search_countries(query: str) -> list[dict]:
        """Search for countries by partial name.

        Args:
            query: Partial or full country name to search for.

        Returns:
            List of matching countries with summary information.
        """
        results = await _get(f"/name/{query.strip()}")
        if not results:
            return []
        return [_summarize(c) for c in results]

    @mcp.tool()
    async def get_countries_by_language(language: str) -> list[dict]:
        """Get all countries that speak a given language.

        Args:
            language: Language name (e.g. "Spanish", "French", "Arabic").

        Returns:
            List of countries where the language is official/spoken.
        """
        results = await _get(f"/lang/{language.strip().lower()}")
        if not results:
            return []
        return [_summarize(c) for c in results]

    @mcp.tool()
    async def compare_countries(country1: str, country2: str) -> dict:
        """Compare two countries side by side.

        Args:
            country1: First country name or ISO code.
            country2: Second country name or ISO code.

        Returns:
            Side-by-side comparison of both countries with key metrics.
        """
        c1 = await get_country(country1)
        c2 = await get_country(country2)

        if "error" in c1 or "error" in c2:
            return {
                "error": "Could not find one or both countries.",
                "country1_result": c1,
                "country2_result": c2,
            }

        pop1 = c1["population"]
        pop2 = c2["population"]
        area1 = c1["area_km2"]
        area2 = c2["area_km2"]

        return {
            "country1": c1,
            "country2": c2,
            "comparison": {
                "population_ratio": round(pop1 / pop2, 2) if pop2 else None,
                "area_ratio": round(area1 / area2, 2) if area2 else None,
                "same_region": c1["region"] == c2["region"],
                "shared_borders": bool(
                    set(c1.get("borders", [])) & set(c2.get("borders", []))
                )
                if c1.get("borders") and c2.get("borders")
                else False,
                "shared_languages": sorted(
                    set(c1["languages"].values()) & set(c2["languages"].values())
                ),
            },
        }
