"""Random user profile generator using the RandomUser.me API."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://randomuser.me/api/"


def _format_user(raw: dict) -> dict:
    """Extract key fields from a RandomUser.me result."""
    name = raw.get("name", {})
    location = raw.get("location", {})
    picture = raw.get("picture", {})
    login = raw.get("login", {})
    return {
        "name": f"{name.get('first', '')} {name.get('last', '')}".strip(),
        "email": raw.get("email", ""),
        "phone": raw.get("phone", ""),
        "location": {
            "city": location.get("city", ""),
            "country": location.get("country", ""),
        },
        "picture_url": picture.get("large", ""),
        "username": login.get("username", ""),
    }


async def _fetch_users(
    count: int = 1,
    nationality: str | None = None,
    gender: str | None = None,
) -> list[dict]:
    """Fetch random users from the RandomUser.me API."""
    params: dict[str, str] = {"results": str(count)}
    if nationality:
        params["nat"] = nationality.strip().lower()
    if gender and gender.strip().lower() in ("male", "female"):
        params["gender"] = gender.strip().lower()
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
        """Generate random user profiles with name, email, phone, location, picture URL, and username.

        Args:
            count: Number of users to generate (1-50, default 1).
            nationality: Optional ISO 3166-1 alpha-2 nationality code (e.g. "us", "gb", "de").
            gender: Optional gender filter — "male" or "female".

        Returns:
            A list of random user profiles.
        """
        clamped = max(1, min(count, 50))
        users = await _fetch_users(count=clamped, nationality=nationality, gender=gender)
        if clamped == 1:
            return users[0] if users else {"error": "No user data returned."}
        return {"count": len(users), "users": users}
