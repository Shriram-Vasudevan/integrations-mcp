"""GitHub Public Search provider — unauthenticated (60 req/hr rate limit)."""

from datetime import datetime, timedelta, timezone

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.github.com"
HEADERS = {
    "User-Agent": "integrations-mcp/0.1.0",
    "Accept": "application/vnd.github+json",
}


async def _get(path: str, params: dict | None = None) -> dict | list:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{BASE_URL}{path}",
            params=params,
            headers=HEADERS,
        )
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register GitHub public search tools with the MCP server."""

    @mcp.tool()
    async def search_repositories(
        query: str,
        sort: str = "stars",
        limit: int = 10,
    ) -> dict:
        """Search GitHub repositories by keyword.

        Args:
            query: Search query (e.g. "fastapi", "language:python web framework").
            sort: Sort field — one of 'stars', 'forks', 'updated' (default 'stars').
            limit: Maximum results to return (1-100, default 10).

        Returns:
            Search results with repository name, description, stars, forks,
            language, and URL.
        """
        limit = max(1, min(limit, 100))
        if sort not in ("stars", "forks", "updated"):
            sort = "stars"
        data = await _get(
            "/search/repositories",
            params={"q": query, "sort": sort, "order": "desc", "per_page": limit},
        )
        return {
            "total_count": data.get("total_count", 0),
            "repositories": [
                {
                    "full_name": repo["full_name"],
                    "description": repo.get("description", ""),
                    "stars": repo["stargazers_count"],
                    "forks": repo["forks_count"],
                    "language": repo.get("language"),
                    "url": repo["html_url"],
                    "topics": repo.get("topics", []),
                }
                for repo in data.get("items", [])
            ],
        }

    @mcp.tool()
    async def get_repository(owner: str, repo: str) -> dict:
        """Get detailed metadata for a GitHub repository.

        Args:
            owner: Repository owner (user or organization).
            repo: Repository name.

        Returns:
            Repository metadata including stars, forks, language, description,
            and topics.
        """
        data = await _get(f"/repos/{owner}/{repo}")
        return {
            "full_name": data["full_name"],
            "description": data.get("description", ""),
            "stars": data["stargazers_count"],
            "forks": data["forks_count"],
            "language": data.get("language"),
            "topics": data.get("topics", []),
            "open_issues": data["open_issues_count"],
            "license": (data.get("license") or {}).get("spdx_id"),
            "default_branch": data.get("default_branch"),
            "url": data["html_url"],
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
            "pushed_at": data.get("pushed_at"),
        }

    @mcp.tool()
    async def search_users(query: str, limit: int = 10) -> dict:
        """Search GitHub users by keyword.

        Args:
            query: Search query (e.g. username, "location:SF language:python").
            limit: Maximum results to return (1-100, default 10).

        Returns:
            Matching users with login, profile URL, and type.
        """
        limit = max(1, min(limit, 100))
        data = await _get(
            "/search/users",
            params={"q": query, "per_page": limit},
        )
        return {
            "total_count": data.get("total_count", 0),
            "users": [
                {
                    "login": user["login"],
                    "url": user["html_url"],
                    "type": user.get("type", "User"),
                    "avatar_url": user.get("avatar_url", ""),
                }
                for user in data.get("items", [])
            ],
        }

    @mcp.tool()
    async def get_trending_repos(language: str | None = None, limit: int = 10) -> dict:
        """Get trending repositories created in the last 30 days, sorted by stars.

        Args:
            language: Optional programming language filter (e.g. "python", "rust").
            limit: Maximum results to return (1-25, default 10).

        Returns:
            Recently created repositories gaining the most stars.
        """
        limit = max(1, min(limit, 25))
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        query = f"created:>{cutoff}"
        if language:
            query += f" language:{language}"
        data = await _get(
            "/search/repositories",
            params={"q": query, "sort": "stars", "order": "desc", "per_page": limit},
        )
        return {
            "period": f"since {cutoff}",
            "language": language,
            "repositories": [
                {
                    "full_name": repo["full_name"],
                    "description": repo.get("description", ""),
                    "stars": repo["stargazers_count"],
                    "forks": repo["forks_count"],
                    "language": repo.get("language"),
                    "url": repo["html_url"],
                    "created_at": repo["created_at"],
                    "topics": repo.get("topics", []),
                }
                for repo in data.get("items", [])
            ],
        }
