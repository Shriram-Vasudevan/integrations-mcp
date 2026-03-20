"""Notion provider wrapping the Notion API v1 (api.notion.com/v1)."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _headers() -> dict:
    """Return standard Notion authentication headers."""
    token = os.environ.get("NOTION_API_KEY")
    if not token:
        raise RuntimeError("NOTION_API_KEY environment variable is not set")
    return {
        "Authorization": f"Bearer {token}",
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
    async def notion_append_block_children(
        block_id: str,
        children: list,
    ) -> dict:
        """Append paragraph, heading, or todo blocks to a Notion page or block.

        Args:
            block_id: The ID of the page or block to append children to.
            children: List of block objects to append. Common types:
                - Paragraph: {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Hello"}}]}}
                - Heading: {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Title"}}]}}
                - To-do: {"object": "block", "type": "to_do", "to_do": {"rich_text": [{"type": "text", "text": {"content": "Task"}}], "checked": false}}
                - Bulleted list: {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": "Item"}}]}}

        Returns:
            List of newly created block summaries.
        """
        data = await _request("PATCH", f"blocks/{block_id}/children", json={"children": children})
        results = []
        for block in data.get("results", []):
            results.append({
                "id": block["id"],
                "type": block.get("type", ""),
                "created_time": block.get("created_time", ""),
            })
        return {
            "block_id": block_id,
            "results": results,
        }

    @mcp.tool()
    async def notion_create_page(
        parent_database_id: Optional[str] = None,
        parent_page_id: Optional[str] = None,
        title: str = "",
        properties: Optional[dict] = None,
        children: Optional[list] = None,
    ) -> dict:
        """Create a new page in Notion under a database or another page.

        Args:
            parent_database_id: Database ID to create the page in (provide this OR parent_page_id).
            parent_page_id: Page ID to create a sub-page under (provide this OR parent_database_id).
            title: Page title text. Used when creating under a page parent.
            properties: Page properties dict matching the parent database schema. For database parents, include title in properties.
            children: List of block objects to add as page content.

        Returns:
            Created page details including id, url, and title.
        """
        payload: dict = {}
        if parent_database_id:
            payload["parent"] = {"database_id": parent_database_id}
            payload["properties"] = properties or {}
        elif parent_page_id:
            payload["parent"] = {"page_id": parent_page_id}
            payload["properties"] = {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            }
        else:
            raise ValueError("Either parent_database_id or parent_page_id is required")
        if children:
            payload["children"] = children
        page = await _request("POST", "pages", json=payload)
        return _summarize_page(page)

    @mcp.tool()
    async def notion_get_block_children(
        block_id: str,
        page_size: int = 50,
        start_cursor: Optional[str] = None,
    ) -> dict:
        """List child blocks of a Notion page or block.

        Args:
            block_id: The ID of the block or page whose children to retrieve.
            page_size: Number of blocks to return (1-100, default 50).
            start_cursor: Pagination cursor for next page.

        Returns:
            List of child blocks with their type and content, plus pagination info.
        """
        params: dict = {"page_size": min(max(1, page_size), 100)}
        if start_cursor:
            params["start_cursor"] = start_cursor
        data = await _request("GET", f"blocks/{block_id}/children", params=params)
        blocks = []
        for block in data.get("results", []):
            block_type = block.get("type", "")
            block_data = {
                "id": block["id"],
                "type": block_type,
                "has_children": block.get("has_children", False),
                "created_time": block.get("created_time", ""),
            }
            if block_type in block:
                type_content = block[block_type]
                if "rich_text" in type_content:
                    block_data["text"] = "".join(
                        t.get("plain_text", "")
                        for t in type_content["rich_text"]
                    )
                if "checked" in type_content:
                    block_data["checked"] = type_content["checked"]
                if "url" in type_content:
                    block_data["url"] = type_content["url"]
            blocks.append(block_data)
        return {
            "block_id": block_id,
            "results": blocks,
            "has_more": data.get("has_more", False),
            "next_cursor": data.get("next_cursor"),
        }

    @mcp.tool()
    async def notion_get_page(page_id: str) -> dict:
        """Retrieve a Notion page by its ID.

        Args:
            page_id: The ID of the page to retrieve (UUID format, with or without dashes).

        Returns:
            Page details including id, title, url, properties, and timestamps.
        """
        page = await _request("GET", f"pages/{page_id}")
        result = _summarize_page(page)
        result["properties"] = page.get("properties", {})
        return result

    @mcp.tool()
    async def notion_list_databases(
        page_size: int = 10,
        start_cursor: Optional[str] = None,
    ) -> dict:
        """List databases shared with the Notion integration.

        Args:
            page_size: Number of results to return (1-100, default 10).
            start_cursor: Pagination cursor for next page of results.

        Returns:
            List of databases with id, title, description, properties schema, and timestamps.
        """
        payload: dict = {
            "filter": {"value": "database", "property": "object"},
            "page_size": min(max(1, page_size), 100),
        }
        if start_cursor:
            payload["start_cursor"] = start_cursor
        data = await _request("POST", "search", json=payload)
        results = []
        for db in data.get("results", []):
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
            results.append({
                "id": db["id"],
                "title": title,
                "description": description,
                "url": db.get("url", ""),
                "properties": prop_schema,
                "created_time": db.get("created_time", ""),
                "last_edited_time": db.get("last_edited_time", ""),
                "archived": db.get("archived", False),
            })
        return {
            "results": results,
            "has_more": data.get("has_more", False),
            "next_cursor": data.get("next_cursor"),
        }

    @mcp.tool()
    async def notion_list_pages(
        page_size: int = 10,
        start_cursor: Optional[str] = None,
    ) -> dict:
        """List pages shared with the Notion integration.

        Args:
            page_size: Number of results to return (1-100, default 10).
            start_cursor: Pagination cursor for next page of results.

        Returns:
            List of pages with id, title, url, and timestamps.
        """
        payload: dict = {
            "filter": {"value": "page", "property": "object"},
            "page_size": min(max(1, page_size), 100),
        }
        if start_cursor:
            payload["start_cursor"] = start_cursor
        data = await _request("POST", "search", json=payload)
        results = []
        for page in data.get("results", []):
            results.append(_summarize_page(page))
        return {
            "results": results,
            "has_more": data.get("has_more", False),
            "next_cursor": data.get("next_cursor"),
        }

    @mcp.tool()
    async def notion_query_database(
        database_id: str,
        filter: Optional[dict] = None,
        sorts: Optional[list] = None,
        page_size: int = 10,
        start_cursor: Optional[str] = None,
    ) -> dict:
        """Query a Notion database with optional filters and sorts.

        Args:
            database_id: The ID of the database to query.
            filter: Notion filter object to narrow results (see Notion API filter docs).
            sorts: List of sort objects, e.g. [{"property": "Name", "direction": "ascending"}].
            page_size: Number of results per page (1-100, default 10).
            start_cursor: Pagination cursor for next page.

        Returns:
            List of matching pages with their properties, plus pagination info.
        """
        payload: dict = {
            "page_size": min(max(1, page_size), 100),
        }
        if filter:
            payload["filter"] = filter
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
    async def notion_search(
        query: str,
        page_size: int = 10,
        start_cursor: Optional[str] = None,
        filter_object_type: Optional[str] = None,
    ) -> dict:
        """Search for pages and databases in Notion by query.

        Args:
            query: Text to search for in page titles and content.
            page_size: Number of results to return (1-100, default 10).
            start_cursor: Pagination cursor for next page of results.
            filter_object_type: Filter by "page" or "database" (optional).

        Returns:
            Matching pages/databases with id, title, url, and timestamps.
        """
        payload: dict = {
            "query": query,
            "page_size": min(max(1, page_size), 100),
        }
        if start_cursor:
            payload["start_cursor"] = start_cursor
        if filter_object_type in ("page", "database"):
            payload["filter"] = {"value": filter_object_type, "property": "object"}
        data = await _request("POST", "search", json=payload)
        results = []
        for item in data.get("results", []):
            results.append({
                "object": item.get("object", ""),
                "id": item["id"],
                "title": _extract_title(item.get("properties", {}))
                or (
                    "".join(
                        t.get("plain_text", "")
                        for t in item.get("title", [])
                    )
                    if item.get("object") == "database"
                    else ""
                ),
                "url": item.get("url", ""),
                "last_edited_time": item.get("last_edited_time", ""),
            })
        return {
            "results": results,
            "has_more": data.get("has_more", False),
            "next_cursor": data.get("next_cursor"),
        }

    @mcp.tool()
    async def notion_update_page(
        page_id: str,
        properties: Optional[dict] = None,
        archived: Optional[bool] = None,
    ) -> dict:
        """Update properties of an existing Notion page.

        Args:
            page_id: The ID of the page to update.
            properties: Dict of properties to update, matching the page's schema.
            archived: Set to True to archive the page, False to unarchive.

        Returns:
            Updated page details including id, title, url, and timestamps.
        """
        payload: dict = {}
        if properties is not None:
            payload["properties"] = properties
        if archived is not None:
            payload["archived"] = archived
        page = await _request("PATCH", f"pages/{page_id}", json=payload)
        return _summarize_page(page)
