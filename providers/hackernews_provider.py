"""HackerNews provider using the official Firebase and Algolia APIs."""

import asyncio

import httpx
from mcp.server.fastmcp import FastMCP

HN_API_URL = "https://hacker-news.firebaseio.com/v0"
HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1"


async def _get_json(url: str, params: dict | None = None) -> dict | list:
    """Make a GET request and return parsed JSON."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def _fetch_story_ids(endpoint: str, limit: int) -> list[int]:
    """Fetch story IDs from a Firebase endpoint."""
    ids = await _get_json(f"{HN_API_URL}/{endpoint}.json")
    return ids[: max(1, min(limit, 30))]


async def _fetch_items(item_ids: list[int]) -> list[dict]:
    """Fetch multiple HN items concurrently."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = [client.get(f"{HN_API_URL}/item/{iid}.json") for iid in item_ids]
        responses = await asyncio.gather(*tasks)
    items = []
    for resp in responses:
        resp.raise_for_status()
        data = resp.json()
        if data:
            items.append(data)
    return items


def _format_story(item: dict) -> dict:
    """Format a story item into a clean response dict."""
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "url": item.get("url"),
        "score": item.get("score", 0),
        "by": item.get("by"),
        "time": item.get("time"),
        "descendants": item.get("descendants", 0),
        "type": item.get("type"),
    }


def register(mcp: FastMCP) -> None:
    """Register HackerNews tools with the MCP server."""

    @mcp.tool()
    async def get_top_stories(limit: int = 10) -> dict:
        """Fetch the current top stories from Hacker News.

        Args:
            limit: Number of stories to return (1-30, default 10).

        Returns:
            List of top stories with title, URL, score, author, and comment count.
        """
        ids = await _fetch_story_ids("topstories", limit)
        items = await _fetch_items(ids)
        return {
            "count": len(items),
            "stories": [_format_story(i) for i in items],
        }

    @mcp.tool()
    async def get_story(id: int) -> dict:
        """Fetch a single Hacker News story by its ID.

        Args:
            id: The HN item ID.

        Returns:
            Full story details including title, URL, score, author, comments, and text.
        """
        item = await _get_json(f"{HN_API_URL}/item/{id}.json")
        if not item:
            raise ValueError(f"Item {id} not found.")
        result = _format_story(item)
        result["text"] = item.get("text")
        result["kids"] = item.get("kids", [])
        return result

    @mcp.tool()
    async def get_new_stories(limit: int = 10) -> dict:
        """Fetch the newest stories from Hacker News.

        Args:
            limit: Number of stories to return (1-30, default 10).

        Returns:
            List of newest stories with title, URL, score, author, and comment count.
        """
        ids = await _fetch_story_ids("newstories", limit)
        items = await _fetch_items(ids)
        return {
            "count": len(items),
            "stories": [_format_story(i) for i in items],
        }

    @mcp.tool()
    async def get_best_stories(limit: int = 10) -> dict:
        """Fetch the best stories from Hacker News.

        Args:
            limit: Number of stories to return (1-30, default 10).

        Returns:
            List of best stories with title, URL, score, author, and comment count.
        """
        ids = await _fetch_story_ids("beststories", limit)
        items = await _fetch_items(ids)
        return {
            "count": len(items),
            "stories": [_format_story(i) for i in items],
        }

    @mcp.tool()
    async def get_ask_hn(limit: int = 10) -> dict:
        """Fetch the latest Ask HN stories.

        Args:
            limit: Number of stories to return (1-30, default 10).

        Returns:
            List of Ask HN stories with title, score, author, and comment count.
        """
        ids = await _fetch_story_ids("askstories", limit)
        items = await _fetch_items(ids)
        return {
            "count": len(items),
            "stories": [_format_story(i) for i in items],
        }

    @mcp.tool()
    async def get_show_hn(limit: int = 10) -> dict:
        """Fetch the latest Show HN stories.

        Args:
            limit: Number of stories to return (1-30, default 10).

        Returns:
            List of Show HN stories with title, URL, score, author, and comment count.
        """
        ids = await _fetch_story_ids("showstories", limit)
        items = await _fetch_items(ids)
        return {
            "count": len(items),
            "stories": [_format_story(i) for i in items],
        }

    @mcp.tool()
    async def search_stories(
        query: str,
        page: int = 0,
        hits_per_page: int = 10,
    ) -> dict:
        """Search Hacker News stories via the Algolia search API.

        Args:
            query: Search query string.
            page: Page number for pagination (default 0).
            hits_per_page: Results per page (1-50, default 10).

        Returns:
            Search results with title, URL, points, author, and timestamps.
        """
        hits_per_page = max(1, min(hits_per_page, 50))
        data = await _get_json(
            f"{HN_ALGOLIA_URL}/search",
            params={
                "query": query,
                "tags": "story",
                "page": page,
                "hitsPerPage": hits_per_page,
            },
        )

        hits = []
        for hit in data.get("hits", []):
            hits.append({
                "id": hit.get("objectID"),
                "title": hit.get("title"),
                "url": hit.get("url"),
                "points": hit.get("points"),
                "author": hit.get("author"),
                "created_at": hit.get("created_at"),
                "num_comments": hit.get("num_comments"),
                "story_text": hit.get("story_text"),
            })

        return {
            "query": query,
            "page": page,
            "total_hits": data.get("nbHits", 0),
            "total_pages": data.get("nbPages", 0),
            "hits": hits,
        }

    @mcp.tool()
    async def get_comments(story_id: int, limit: int = 20) -> dict:
        """Fetch comments for a Hacker News story.

        Uses the Algolia API to retrieve comments for the given story.

        Args:
            story_id: The HN story ID to fetch comments for.
            limit: Maximum number of comments to return (1-50, default 20).

        Returns:
            List of comments with author, text, and timestamp.
        """
        limit = max(1, min(limit, 50))
        data = await _get_json(
            f"{HN_ALGOLIA_URL}/search",
            params={
                "tags": f"comment,story_{story_id}",
                "hitsPerPage": limit,
            },
        )

        comments = []
        for hit in data.get("hits", []):
            comments.append({
                "id": hit.get("objectID"),
                "author": hit.get("author"),
                "text": hit.get("comment_text"),
                "created_at": hit.get("created_at"),
                "parent_id": hit.get("parent_id"),
                "points": hit.get("points"),
            })

        return {
            "story_id": story_id,
            "count": len(comments),
            "comments": comments,
        }
