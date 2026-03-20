"""Zendesk Support provider wrapping the Zendesk REST API v2.

Auth: ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_API_TOKEN env vars.
Uses Basic auth with {email}/token:{api_token}.
"""

import os
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP

_PAGE_SIZE = 25


def _config() -> tuple[str, tuple[str, str]]:
    """Return (base_url, auth_tuple) from environment variables."""
    subdomain = os.environ.get("ZENDESK_SUBDOMAIN", "")
    email = os.environ.get("ZENDESK_EMAIL", "")
    token = os.environ.get("ZENDESK_API_TOKEN", "")
    if not all([subdomain, email, token]):
        raise RuntimeError(
            "ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, and ZENDESK_API_TOKEN environment variables are required"
        )
    base_url = f"https://{subdomain}.zendesk.com/api/v2"
    auth = (f"{email}/token", token)
    return base_url, auth


def _get(path: str, params: dict | None = None) -> Any:
    base_url, auth = _config()
    resp = requests.get(f"{base_url}{path}", auth=auth, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, json: dict) -> Any:
    base_url, auth = _config()
    resp = requests.post(f"{base_url}{path}", auth=auth, json=json, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _put(path: str, json: dict) -> Any:
    base_url, auth = _config()
    resp = requests.put(f"{base_url}{path}", auth=auth, json=json, timeout=30)
    resp.raise_for_status()
    return resp.json()


def register(mcp: FastMCP) -> None:
    """Register Zendesk tools with the MCP server."""

    @mcp.tool()
    async def zendesk_list_tickets(
        status: str = "",
        page: int = 1,
    ) -> dict:
        """List Zendesk support tickets with optional status filter and pagination.

        Args:
            status: Filter by status (new, open, pending, hold, solved, closed). Leave empty for all.
            page: Page number (default 1, 25 tickets per page).

        Returns:
            Paginated list of tickets with id, subject, status, priority, and timestamps.
        """
        if status:
            # Use the search API for status filtering
            data = _get(
                "/search.json",
                params={
                    "query": f"type:ticket status:{status}",
                    "sort_by": "updated_at",
                    "sort_order": "desc",
                    "page": page,
                    "per_page": _PAGE_SIZE,
                },
            )
            raw_tickets = data.get("results", [])
        else:
            data = _get("/tickets.json", params={"page": page, "per_page": _PAGE_SIZE})
            raw_tickets = data.get("tickets", [])

        tickets = [
            {
                "id": t["id"],
                "subject": t.get("subject"),
                "status": t.get("status"),
                "priority": t.get("priority"),
                "requester_id": t.get("requester_id"),
                "assignee_id": t.get("assignee_id"),
                "tags": t.get("tags", []),
                "created_at": t.get("created_at"),
                "updated_at": t.get("updated_at"),
            }
            for t in raw_tickets
        ]
        return {
            "tickets": tickets,
            "count": data.get("count"),
            "next_page": data.get("next_page"),
            "previous_page": data.get("previous_page"),
        }

    @mcp.tool()
    async def zendesk_get_ticket(ticket_id: int) -> dict:
        """Get full detail of a Zendesk ticket including its comments.

        Args:
            ticket_id: The ticket ID.

        Returns:
            Full ticket details including description, tags, custom fields, and all comments.
        """
        ticket_data = _get(f"/tickets/{ticket_id}.json")
        ticket = ticket_data.get("ticket", ticket_data)

        # Fetch comments for the ticket
        comments_data = _get(
            f"/tickets/{ticket_id}/comments.json",
            params={"per_page": _PAGE_SIZE},
        )
        comments = [
            {
                "id": c["id"],
                "author_id": c["author_id"],
                "body": c["body"],
                "public": c["public"],
                "created_at": c["created_at"],
            }
            for c in comments_data.get("comments", [])
        ]

        ticket["comments"] = comments
        return ticket

    @mcp.tool()
    async def zendesk_create_ticket(
        subject: str,
        body: str,
        priority: str = "normal",
        requester_email: str = "",
    ) -> dict:
        """Create a new Zendesk support ticket.

        Args:
            subject: Ticket subject line.
            body: Ticket description / first comment body.
            priority: One of low, normal, high, urgent (default normal).
            requester_email: Optional requester email address.

        Returns:
            The created ticket object.
        """
        comment: dict[str, Any] = {"body": body}
        ticket: dict[str, Any] = {
            "subject": subject,
            "priority": priority,
            "comment": comment,
        }
        if requester_email:
            ticket["requester"] = {"email": requester_email}
        data = _post("/tickets.json", json={"ticket": ticket})
        return data.get("ticket", data)

    @mcp.tool()
    async def zendesk_update_ticket(
        ticket_id: int,
        status: str = "",
        priority: str = "",
        assignee_id: int | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Update an existing Zendesk ticket.

        Args:
            ticket_id: The ticket ID to update.
            status: New status (new, open, pending, hold, solved, closed). Leave empty to keep current.
            priority: New priority (low, normal, high, urgent). Leave empty to keep current.
            assignee_id: User ID to assign the ticket to. Leave None to keep current.
            tags: Replace tags with this list. Leave None to keep current.

        Returns:
            The updated ticket object.
        """
        ticket: dict[str, Any] = {}
        if status:
            ticket["status"] = status
        if priority:
            ticket["priority"] = priority
        if assignee_id is not None:
            ticket["assignee_id"] = assignee_id
        if tags is not None:
            ticket["tags"] = tags
        if not ticket:
            return {"error": "No fields to update"}
        data = _put(f"/tickets/{ticket_id}.json", json={"ticket": ticket})
        return data.get("ticket", data)

    @mcp.tool()
    async def zendesk_add_comment(
        ticket_id: int,
        body: str,
        public: bool = True,
    ) -> dict:
        """Add a comment to a Zendesk ticket.

        Args:
            ticket_id: The ticket ID.
            body: Comment text.
            public: Whether the comment is public (default True). Set False for internal note.

        Returns:
            The updated ticket object.
        """
        ticket = {"comment": {"body": body, "public": public}}
        data = _put(f"/tickets/{ticket_id}.json", json={"ticket": ticket})
        return data.get("ticket", data)

    @mcp.tool()
    async def zendesk_list_users(
        query: str = "",
        page: int = 1,
    ) -> dict:
        """List Zendesk users with optional search by email or name.

        Args:
            query: Search by name or email. Leave empty to list all users.
            page: Page number (default 1).

        Returns:
            List of users with id, name, email, and role.
        """
        if query:
            data = _get(
                "/users/search.json",
                params={"query": query, "page": page, "per_page": _PAGE_SIZE},
            )
        else:
            data = _get("/users.json", params={"page": page, "per_page": _PAGE_SIZE})

        users = [
            {
                "id": u["id"],
                "name": u.get("name"),
                "email": u.get("email"),
                "role": u.get("role"),
                "active": u.get("active"),
                "created_at": u.get("created_at"),
            }
            for u in data.get("users", [])
        ]
        return {
            "users": users,
            "count": data.get("count"),
            "next_page": data.get("next_page"),
            "previous_page": data.get("previous_page"),
        }

    @mcp.tool()
    async def zendesk_get_user(user_id: int) -> dict:
        """Get a single Zendesk user by ID.

        Args:
            user_id: The user ID.

        Returns:
            Full user details.
        """
        data = _get(f"/users/{user_id}.json")
        return data.get("user", data)

    @mcp.tool()
    async def zendesk_search(
        query: str,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        page: int = 1,
    ) -> dict:
        """Search Zendesk using the unified search API.

        Supports tickets, users, and organizations. Uses Zendesk search syntax.

        Args:
            query: Search query (e.g. 'status:open priority:high', 'type:user email:jane@example.com',
                   'type:organization name:Acme'). Defaults to searching tickets if no type is specified.
            sort_by: Field to sort by (default updated_at).
            sort_order: asc or desc (default desc).
            page: Page number (default 1).

        Returns:
            Matching results with pagination info.
        """
        data = _get(
            "/search.json",
            params={
                "query": query,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "page": page,
                "per_page": _PAGE_SIZE,
            },
        )
        return {
            "results": data.get("results", []),
            "count": data.get("count"),
            "next_page": data.get("next_page"),
            "previous_page": data.get("previous_page"),
        }

    @mcp.tool()
    async def zendesk_list_organizations(page: int = 1) -> dict:
        """List Zendesk organizations with pagination.

        Args:
            page: Page number (default 1).

        Returns:
            List of organizations with id, name, and domain info.
        """
        data = _get(
            "/organizations.json",
            params={"page": page, "per_page": _PAGE_SIZE},
        )
        orgs = [
            {
                "id": o["id"],
                "name": o.get("name"),
                "domain_names": o.get("domain_names", []),
                "created_at": o.get("created_at"),
                "updated_at": o.get("updated_at"),
            }
            for o in data.get("organizations", [])
        ]
        return {
            "organizations": orgs,
            "count": data.get("count"),
            "next_page": data.get("next_page"),
            "previous_page": data.get("previous_page"),
        }
