"""Random user generator using the RandomUser.me API (free, no auth)."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://randomuser.me/api/"


def _format_user(raw: dict) -> dict:
    """Extract structured fields from a RandomUser.me result."""
    name = raw.get("name", {})
    location = raw.get("location", {})
    street = location.get("street", {})
    dob = raw.get("dob", {})
    picture = raw.get("picture", {})
    return {
        "name": {
            "title": name.get("title", ""),
            "first": name.get("first", ""),
            "last": name.get("last", ""),
        },
        "email": raw.get("email", ""),
        "phone": raw.get("phone", ""),
        "address": {
            "street": f"{street.get('number', '')} {street.get('name', '')}".strip(),
            "city": location.get("city", ""),
            "state": location.get("state", ""),
            "country": location.get("country", ""),
            "postcode": str(location.get("postcode", "")),
        },
        "dob": {
            "date": dob.get("date", ""),
            "age": dob.get("age", ""),
        },
        "picture_url": picture.get("large", ""),
    }


async def _fetch_users(
    count: int = 1,
    nationality: str | None = None,
    gender: str | None = None,
    seed: str | None = None,
) -> list[dict]:
    """Fetch random users from the RandomUser.me API."""
    params: dict[str, str] = {"results": str(count)}
    if nationality:
        params["nat"] = nationality.strip().lower()
    if gender and gender.strip().lower() in ("male", "female"):
        params["gender"] = gender.strip().lower()
    if seed:
        params["seed"] = seed.strip()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    return [_format_user(u) for u in data.get("results", [])]


def register(mcp: FastMCP) -> None:
    """Register random user tools with the MCP server."""

    @mcp.tool()
    async def generate_users(
        count: int = 1,
        nationality: str | None = None,
        gender: str | None = None,
    ) -> dict:
        """Generate random user profiles with name, email, phone, address, DOB, and picture URL.

        Args:
            count: Number of users to generate (1-50, default 1).
            nationality: Optional ISO 3166-1 alpha-2 nationality code (e.g. "us", "gb", "de").
            gender: Optional gender filter — "male" or "female".

        Returns:
            Structured user object(s) with name, email, phone, address, DOB, and picture URL.
        """
        clamped = max(1, min(count, 50))
        users = await _fetch_users(count=clamped, nationality=nationality, gender=gender)
        if clamped == 1:
            return users[0] if users else {"error": "No user data returned."}
        return {"count": len(users), "users": users}

    @mcp.tool()
    async def generate_user_seed(seed: str) -> dict:
        """Generate a deterministic random user using a seed value.

        The same seed always returns the same user, useful for reproducible test data.

        Args:
            seed: A seed string for deterministic user generation.

        Returns:
            A structured user object with name, email, phone, address, DOB, and picture URL.
        """
        users = await _fetch_users(count=1, seed=seed)
        if not users:
            return {"error": "No user data returned."}
        return {"seed": seed, "user": users[0]}
