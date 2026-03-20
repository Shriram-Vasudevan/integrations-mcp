"""Monday.com provider using the Monday.com GraphQL API v2."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

MONDAY_API_URL = "https://api.monday.com/v2"


def _get_api_key() -> str:
    key = os.environ.get("MONDAY_API_KEY")
    if not key:
        raise RuntimeError("MONDAY_API_KEY environment variable is not set")
    return key


async def _graphql(query: str, variables: Optional[dict] = None) -> dict:
    """Execute a GraphQL request against the Monday.com API."""
    headers = {
        "Authorization": _get_api_key(),
        "Content-Type": "application/json",
        "API-Version": "2024-01",
    }
    payload: dict = {"query": query}
    if variables:
        payload["variables"] = variables

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            MONDAY_API_URL, json=payload, headers=headers, timeout=30.0
        )
        resp.raise_for_status()
        body = resp.json()

    if "errors" in body:
        raise RuntimeError(f"Monday.com API errors: {body['errors']}")
    return body.get("data", {})


def register(mcp: FastMCP) -> None:
    """Register Monday.com tools with the MCP server."""

    @mcp.tool()
    async def monday_list_boards(
        limit: int = 25,
        page: int = 1,
        board_kind: Optional[str] = None,
    ) -> dict:
        """List boards in your Monday.com workspace.

        Args:
            limit: Number of boards to return (1-100, default 25).
            page: Page number for pagination (default 1).
            board_kind: Filter by board kind: public, private, or share (optional).

        Returns:
            List of boards with id, name, state, and board_kind.
        """
        limit = max(1, min(limit, 100))
        kind_filter = f', board_kind: {board_kind}' if board_kind else ""
        query = """
        query {
          boards(limit: %d, page: %d%s) {
            id
            name
            description
            state
            board_kind
            workspace { id name }
            columns { id title type }
            groups { id title }
            owners { id name }
          }
        }
        """ % (limit, page, kind_filter)
        data = await _graphql(query)
        boards = []
        for b in data.get("boards", []):
            boards.append({
                "id": b["id"],
                "name": b.get("name"),
                "description": b.get("description"),
                "state": b.get("state"),
                "board_kind": b.get("board_kind"),
                "workspace": b.get("workspace"),
                "column_count": len(b.get("columns", [])),
                "group_count": len(b.get("groups", [])),
                "owners": [{"id": o["id"], "name": o.get("name")} for o in b.get("owners", [])],
            })
        return {"boards": boards}

    @mcp.tool()
    async def monday_get_board(board_id: str) -> dict:
        """Get detailed information about a specific Monday.com board.

        Args:
            board_id: The board ID (required).

        Returns:
            Board details including columns, groups, owners, and item count.
        """
        query = """
        query {
          boards(ids: [%s]) {
            id
            name
            description
            state
            board_kind
            workspace { id name }
            permissions
            columns { id title type description settings_str }
            groups { id title color position }
            owners { id name email }
            items_count
          }
        }
        """ % board_id
        data = await _graphql(query)
        boards = data.get("boards", [])
        if not boards:
            raise ValueError(f"Board not found: {board_id}")
        b = boards[0]
        return {
            "id": b["id"],
            "name": b.get("name"),
            "description": b.get("description"),
            "state": b.get("state"),
            "board_kind": b.get("board_kind"),
            "workspace": b.get("workspace"),
            "permissions": b.get("permissions"),
            "columns": b.get("columns", []),
            "groups": b.get("groups", []),
            "owners": b.get("owners", []),
            "items_count": b.get("items_count"),
        }

    @mcp.tool()
    async def monday_list_items(
        board_id: str,
        limit: int = 25,
        page: int = 1,
        group_id: Optional[str] = None,
    ) -> dict:
        """List items on a Monday.com board.

        Args:
            board_id: The board ID to list items from (required).
            limit: Number of items to return (1-100, default 25).
            page: Page number for pagination (default 1).
            group_id: Filter items by group ID (optional).

        Returns:
            List of items with id, name, group, column values, and timestamps.
        """
        limit = max(1, min(limit, 100))
        if group_id:
            query = """
            query {
              boards(ids: [%s]) {
                groups(ids: ["%s"]) {
                  id
                  title
                  items_page(limit: %d) {
                    items {
                      id
                      name
                      state
                      group { id title }
                      column_values { id text type value }
                      created_at
                      updated_at
                    }
                  }
                }
              }
            }
            """ % (board_id, group_id, limit)
            data = await _graphql(query)
            boards = data.get("boards", [])
            if not boards:
                return {"items": []}
            groups = boards[0].get("groups", [])
            if not groups:
                return {"items": []}
            raw_items = groups[0].get("items_page", {}).get("items", [])
        else:
            query = """
            query {
              boards(ids: [%s]) {
                items_page(limit: %d) {
                  items {
                    id
                    name
                    state
                    group { id title }
                    column_values { id text type value }
                    created_at
                    updated_at
                  }
                }
              }
            }
            """ % (board_id, limit)
            data = await _graphql(query)
            boards = data.get("boards", [])
            if not boards:
                return {"items": []}
            raw_items = boards[0].get("items_page", {}).get("items", [])

        items = []
        for item in raw_items:
            col_vals = []
            for cv in item.get("column_values", []):
                if cv.get("text"):
                    col_vals.append({
                        "id": cv["id"],
                        "type": cv.get("type"),
                        "text": cv.get("text"),
                    })
            items.append({
                "id": item["id"],
                "name": item.get("name"),
                "state": item.get("state"),
                "group": item.get("group"),
                "column_values": col_vals,
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            })
        return {"items": items}

    @mcp.tool()
    async def monday_get_item(item_id: str) -> dict:
        """Get detailed information about a specific Monday.com item.

        Args:
            item_id: The item ID (required).

        Returns:
            Item details including column values, subitems, updates, and subscribers.
        """
        query = """
        query {
          items(ids: [%s]) {
            id
            name
            state
            board { id name }
            group { id title }
            column_values { id title text type value }
            subitems {
              id
              name
              column_values { id text type }
            }
            updates(limit: 5) {
              id
              body
              text_body
              creator { id name }
              created_at
            }
            subscribers { id name email }
            created_at
            updated_at
          }
        }
        """ % item_id
        data = await _graphql(query)
        items = data.get("items", [])
        if not items:
            raise ValueError(f"Item not found: {item_id}")
        item = items[0]
        return {
            "id": item["id"],
            "name": item.get("name"),
            "state": item.get("state"),
            "board": item.get("board"),
            "group": item.get("group"),
            "column_values": item.get("column_values", []),
            "subitems": item.get("subitems", []),
            "updates": item.get("updates", []),
            "subscribers": item.get("subscribers", []),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }

    @mcp.tool()
    async def monday_create_item(
        board_id: str,
        item_name: str,
        group_id: Optional[str] = None,
        column_values: Optional[str] = None,
    ) -> dict:
        """Create a new item on a Monday.com board.

        Args:
            board_id: The board ID to create the item on (required).
            item_name: Name of the new item (required).
            group_id: Group ID to place the item in (optional, uses first group if omitted).
            column_values: JSON string of column values, e.g. '{"status": {"label": "Done"}, "date": {"date": "2024-01-15"}}' (optional).

        Returns:
            The created item with id, name, and board info.
        """
        variables: dict = {
            "boardId": int(board_id),
            "itemName": item_name,
        }
        group_arg = ""
        col_arg = ""

        if group_id:
            variables["groupId"] = group_id
            group_arg = ", $groupId: String!"

        if column_values:
            variables["columnValues"] = column_values
            col_arg = ", $columnValues: JSON!"

        mutation = """
        mutation($boardId: ID!, $itemName: String!%s%s) {
          create_item(board_id: $boardId, item_name: $itemName%s%s) {
            id
            name
            state
            board { id name }
            group { id title }
            column_values { id text type }
            created_at
          }
        }
        """ % (
            group_arg,
            col_arg,
            ", group_id: $groupId" if group_id else "",
            ", column_values: $columnValues" if column_values else "",
        )
        data = await _graphql(mutation, variables)
        item = data.get("create_item", {})
        return {
            "id": item.get("id"),
            "name": item.get("name"),
            "state": item.get("state"),
            "board": item.get("board"),
            "group": item.get("group"),
            "column_values": item.get("column_values", []),
            "created_at": item.get("created_at"),
        }

    @mcp.tool()
    async def monday_update_item(
        board_id: str,
        item_id: str,
        column_values: str,
    ) -> dict:
        """Update column values of an existing Monday.com item.

        Args:
            board_id: The board ID the item belongs to (required).
            item_id: The item ID to update (required).
            column_values: JSON string of column values to update, e.g. '{"status": {"label": "Working on it"}, "text0": "Updated text"}' (required).

        Returns:
            The updated item with id, name, and new column values.
        """
        mutation = """
        mutation($boardId: ID!, $itemId: ID!, $columnValues: JSON!) {
          change_multiple_column_values(
            board_id: $boardId,
            item_id: $itemId,
            column_values: $columnValues
          ) {
            id
            name
            column_values { id title text type value }
            updated_at
          }
        }
        """
        variables = {
            "boardId": int(board_id),
            "itemId": int(item_id),
            "columnValues": column_values,
        }
        data = await _graphql(mutation, variables)
        item = data.get("change_multiple_column_values", {})
        return {
            "id": item.get("id"),
            "name": item.get("name"),
            "column_values": item.get("column_values", []),
            "updated_at": item.get("updated_at"),
        }

    @mcp.tool()
    async def monday_list_groups(board_id: str) -> dict:
        """List all groups on a Monday.com board.

        Args:
            board_id: The board ID (required).

        Returns:
            List of groups with id, title, color, and position.
        """
        query = """
        query {
          boards(ids: [%s]) {
            groups {
              id
              title
              color
              position
            }
          }
        }
        """ % board_id
        data = await _graphql(query)
        boards = data.get("boards", [])
        if not boards:
            raise ValueError(f"Board not found: {board_id}")
        return {"groups": boards[0].get("groups", [])}

    @mcp.tool()
    async def monday_create_update(
        item_id: str,
        body: str,
    ) -> dict:
        """Add an update (comment) to a Monday.com item.

        Args:
            item_id: The item ID to add the update to (required).
            body: The update text/body in HTML or plain text (required).

        Returns:
            The created update with id, body, creator, and timestamp.
        """
        mutation = """
        mutation($itemId: ID!, $body: String!) {
          create_update(item_id: $itemId, body: $body) {
            id
            body
            text_body
            creator { id name }
            created_at
          }
        }
        """
        variables = {"itemId": int(item_id), "body": body}
        data = await _graphql(mutation, variables)
        update = data.get("create_update", {})
        return {
            "id": update.get("id"),
            "body": update.get("body"),
            "text_body": update.get("text_body"),
            "creator": update.get("creator"),
            "created_at": update.get("created_at"),
        }
