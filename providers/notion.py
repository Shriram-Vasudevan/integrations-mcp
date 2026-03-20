"""Notion provider wrapping the Notion REST API v1 using async httpx.

Requires the NOTION_API_KEY environment variable to be set with a Notion
integration token (Bearer auth).
"""

import json
import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _get_token() -> str:
    """Return the Notion integration token from environment."""
    token = os.environ.get("NOTION_API_KEY")
    if not token:
        raise RuntimeError("NOTION_API_KEY environment variable is not set")
    return token


def _headers() -> dict:
    """Return standard Notion API request headers."""
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


async def _request(method: str, path: str, **kwargs) -> dict:
    """Make an authenticated request to the Notion API."""
    url = f"{API_BASE}/{path.lstrip('/')}"
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            url,
            headers=_headers(),
            timeout=30,
            **kwargs,
        )
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {"status": "ok"}
        return resp.json()


def _extract_title(properties: dict) -> str:
    """Extract the title text from a page's properties."""
    for prop in properties.values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            return "".join(t.get("plain_text", "") for t in title_parts)
    return ""


def _summarize_page(page: dict) -> dict:
    """Return a compact summary of a Notion page object."""
    return {
        "id": page["id"],
        "url": page.get("url", ""),
        "title": _extract_title(page.get("properties", {})),
        "created_time": page.get("created_time", ""),
        "last_edited_time": page.get("last_edited_time", ""),
        "archived": page.get("archived", False),
        "parent_type": page.get("parent", {}).get("type", ""),
    }


def register(mcp: FastMCP) -> None:
    """Register Notion tools with the MCP server."""

    @mcp.tool()
    async def search_pages(
        query: str,
        page_size: int = 10,
        start_cursor: Optional[str] = None,
    ) -> dict:
        """Search for pages and databases in Notion by title or content.

        Args:
            query: Text to search for in page titles and content.
            page_size: Number of results to return (1-100, default 10).
            start_cursor: Pagination cursor for next page of results.

        Returns:
            Matching pages and databases with id, title, url, and timestamps.
        """
        payload: dict = {
            "query": query,
            "page_size": min(max(1, page_size), 100),
        }
        if start_cursor:
            payload["start_cursor"] = start_cursor
        data = await _request("POST", "search", json=payload)
        results = []
        for item in data.get("results", []):
            obj_type = item.get("object", "")
            if obj_type == "database":
                title = "".join(
                    t.get("plain_text", "") for t in item.get("title", [])
                )
            else:
                title = _extract_title(item.get("properties", {}))
            results.append({
                "object": obj_type,
                "id": item["id"],
                "title": title,
                "url": item.get("url", ""),
                "last_edited_time": item.get("last_edited_time", ""),
            })
        return {
            "results": results,
            "has_more": data.get("has_more", False),
            "next_cursor": data.get("next_cursor"),
        }

    @mcp.tool()
    async def get_page(page_id: str) -> dict:
        """Retrieve a Notion page by its ID.

        Args:
            page_id: The ID of the page to retrieve (UUID format, with or without dashes).

        Returns:
            Page details including id, title, url, full properties, and timestamps.
        """
        page = await _request("GET", f"pages/{page_id}")
        result = _summarize_page(page)
        result["properties"] = page.get("properties", {})
        return result

    @mcp.tool()
    async def get_database(database_id: str) -> dict:
        """Retrieve a Notion database and its schema by ID.

        Args:
            database_id: The ID of the database to retrieve (UUID format, with or without dashes).

        Returns:
            Database details including id, title, description, property schema, and timestamps.
        """
        db = await _request("GET", f"databases/{database_id}")
        title_parts = db.get("title", [])
        title = "".join(t.get("plain_text", "") for t in title_parts)
        desc_parts = db.get("description", [])
        description = "".join(t.get("plain_text", "") for t in desc_parts)
        prop_schema = {}
        for name, prop in db.get("properties", {}).items():
            prop_schema[name] = {
                "id": prop.get("id", ""),
                "type": prop.get("type", ""),
            }
        return {
            "id": db["id"],
            "title": title,
            "description": description,
            "url": db.get("url", ""),
            "properties": prop_schema,
            "is_inline": db.get("is_inline", False),
            "created_time": db.get("created_time", ""),
            "last_edited_time": db.get("last_edited_time", ""),
            "archived": db.get("archived", False),
        }

    @mcp.tool()
    async def query_database(
        database_id: str,
        filter_json: Optional[str] = None,
        sorts: Optional[list] = None,
        page_size: int = 10,
        start_cursor: Optional[str] = None,
    ) -> dict:
        """Query a Notion database with optional filters and sorts.

        Args:
            database_id: The ID of the database to query.
            filter_json: JSON string of a Notion filter object to narrow results.
                Example: '{"property": "Status", "select": {"equals": "Done"}}'
            sorts: List of sort objects, e.g. [{"property": "Name", "direction": "ascending"}].
            page_size: Number of results per page (1-100, default 10).
            start_cursor: Pagination cursor for next page.

        Returns:
            List of matching pages with their properties, plus pagination info.
        """
        payload: dict = {
            "page_size": min(max(1, page_size), 100),
        }
        if filter_json:
            payload["filter"] = json.loads(filter_json)
        if sorts:
            payload["sorts"] = sorts
        if start_cursor:
            payload["start_cursor"] = start_cursor
        data = await _request("POST", f"databases/{database_id}/query", json=payload)
        results = []
        for page in data.get("results", []):
            results.append(_summarize_page(page))
        return {
            "results": results,
            "has_more": data.get("has_more", False),
            "next_cursor": data.get("next_cursor"),
        }

    @mcp.tool()
    async def create_page(
        parent_id: str,
        title: str,
        content: Optional[str] = None,
        is_database: bool = False,
        properties: Optional[dict] = None,
    ) -> dict:
        """Create a new page in Notion under a database or another page.

        Args:
            parent_id: The ID of the parent page or database.
            title: Page title text.
            content: Optional plain-text content to add as a paragraph block.
            is_database: Set to True if parent_id is a database ID (default False).
            properties: Additional properties dict for database pages (optional).

        Returns:
            Created page details including id, url, and title.
        """
        payload: dict = {}
        if is_database:
            payload["parent"] = {"database_id": parent_id}
            props = properties or {}
            if "title" not in props and "Name" not in props:
                props["Name"] = {
                    "title": [{"text": {"content": title}}]
                }
            payload["properties"] = props
        else:
            payload["parent"] = {"page_id": parent_id}
            payload["properties"] = {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            }
        if content:
            payload["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    },
                }
            ]
        page = await _request("POST", "pages", json=payload)
        return _summarize_page(page)

    @mcp.tool()
    async def append_blocks(
        page_id: str,
        blocks_json: str,
    ) -> dict:
        """Append blocks to a Notion page or block.

        Args:
            page_id: The ID of the page or block to append children to.
            blocks_json: JSON string of block objects to append. Example:
                '[{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Hello world"}}]}}]'

        Returns:
            List of newly created block summaries.
        """
        children = json.loads(blocks_json)
        if not isinstance(children, list):
            return {"error": True, "message": "blocks_json must be a JSON array of block objects"}
        data = await _request("PATCH", f"blocks/{page_id}/children", json={"children": children})
        results = []
        for block in data.get("results", []):
            results.append({
                "id": block["id"],
                "type": block.get("type", ""),
                "created_time": block.get("created_time", ""),
            })
        return {
            "block_id": page_id,
            "results": results,
        }
