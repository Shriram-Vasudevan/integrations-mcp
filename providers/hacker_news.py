"""Hacker News provider using the Firebase API (free, no auth)."""

import asyncio

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://hacker-news.firebaseio.com/v0"


async def _get_json(url: str) -> dict | list:
    """Make a GET request and return parsed JSON."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def _fetch_story_ids(endpoint: str, limit: int) -> list[int]:
    """Fetch story IDs from a Firebase endpoint and return up to *limit*."""
    ids = await _get_json(f"{BASE_URL}/{endpoint}.json")
    return ids[: max(1, min(limit, 30))]


async def _fetch_items(item_ids: list[int]) -> list[dict]:
    """Fetch multiple HN items concurrently."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = [client.get(f"{BASE_URL}/item/{iid}.json") for iid in item_ids]
        responses = await asyncio.gather(*tasks)
    items = []
    for resp in responses:
        resp.raise_for_status()
        data = resp.json()
        if data:
            items.append(data)
    return items


def _format_story(item: dict) -> dict:
    """Return a concise dict for a story item."""
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
    """Register Hacker News tools with the MCP server."""

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
    async def get_item(id: int) -> dict:
        """Fetch a single Hacker News item by its ID.

        Works for stories, comments, jobs, polls, and poll options.

        Args:
            id: The HN item ID.

        Returns:
            Full item details including title, URL, score, author, kids, and text.
        """
        item = await _get_json(f"{BASE_URL}/item/{id}.json")
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
