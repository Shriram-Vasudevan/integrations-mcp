"""GitHub Public API provider — no authentication required (60 req/hr)."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.github.com"
USER_AGENT = "integrations-mcp/0.1.0"


async def _get(path: str, params: dict | None = None) -> dict | list:
    """Make a GET request to the GitHub public API."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{BASE_URL}{path}",
            params=params,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/vnd.github+json",
            },
        )
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register GitHub public API tools with the MCP server."""

    @mcp.tool()
    async def search_repos(query: str, limit: int = 5) -> list[dict]:
        """Search GitHub repositories by keyword.

        Args:
            query: Search query (e.g. "language:python fastapi").
            limit: Maximum number of results to return (1-100, default 5).

        Returns:
            List of repositories with name, description, stars, and URL.
        """
        limit = max(1, min(limit, 100))
        data = await _get("/search/repositories", params={"q": query, "per_page": limit})
        return [
            {
                "name": repo["full_name"],
                "description": repo.get("description", ""),
                "stars": repo["stargazers_count"],
                "url": repo["html_url"],
            }
            for repo in data.get("items", [])
        ]

    @mcp.tool()
    async def get_repo(owner: str, repo: str) -> dict:
        """Get detailed information about a GitHub repository.

        Args:
            owner: Repository owner (user or organization).
            repo: Repository name.

        Returns:
            Repository details including description, stars, forks, language,
            and license.
        """
        data = await _get(f"/repos/{owner}/{repo}")
        return {
            "name": data["full_name"],
            "description": data.get("description", ""),
            "stars": data["stargazers_count"],
            "forks": data["forks_count"],
            "open_issues": data["open_issues_count"],
            "language": data.get("language"),
            "license": (data.get("license") or {}).get("spdx_id"),
            "url": data["html_url"],
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
            "topics": data.get("topics", []),
        }

    @mcp.tool()
    async def get_user(username: str) -> dict:
        """Get public profile information for a GitHub user.

        Args:
            username: GitHub username.

        Returns:
            User profile with name, bio, public repos/gists counts, and
            follower stats.
        """
        data = await _get(f"/users/{username}")
        return {
            "login": data["login"],
            "name": data.get("name"),
            "bio": data.get("bio"),
            "company": data.get("company"),
            "location": data.get("location"),
            "public_repos": data["public_repos"],
            "public_gists": data["public_gists"],
            "followers": data["followers"],
            "following": data["following"],
            "url": data["html_url"],
            "created_at": data["created_at"],
        }
