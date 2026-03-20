"""Intercom provider wrapping the Intercom REST API v2.11 using httpx.

Auth: INTERCOM_ACCESS_TOKEN env var (Bearer token).
Docs: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/
"""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.intercom.io"


def _get_token() -> str:
    """Return the Intercom access token from env."""
    token = os.environ.get("INTERCOM_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError(
            "INTERCOM_ACCESS_TOKEN environment variable is required"
        )
    return token


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Intercom-Version": "2.11",
    }


async def _request(method: str, path: str, **kwargs) -> dict:
    """Make an authenticated request to the Intercom API."""
    url = f"{BASE_URL}/{path.lstrip('/')}"
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


def _summarize_contact(c: dict) -> dict:
    """Extract key fields from a contact object."""
    return {
        "id": c.get("id"),
        "type": c.get("role"),
        "external_id": c.get("external_id"),
        "email": c.get("email"),
        "name": c.get("name"),
        "phone": c.get("phone"),
        "created_at": c.get("created_at"),
        "updated_at": c.get("updated_at"),
    }


def _summarize_conversation(conv: dict) -> dict:
    """Extract key fields from a conversation object."""
    source = conv.get("source", {})
    return {
        "id": conv.get("id"),
        "title": conv.get("title"),
        "state": conv.get("state"),
        "open": conv.get("open"),
        "read": conv.get("read"),
        "created_at": conv.get("created_at"),
        "updated_at": conv.get("updated_at"),
        "source_type": source.get("type"),
        "source_subject": source.get("subject"),
    }


def _summarize_company(co: dict) -> dict:
    """Extract key fields from a company object."""
    return {
        "id": co.get("id"),
        "company_id": co.get("company_id"),
        "name": co.get("name"),
        "plan": co.get("plan", {}).get("name") if isinstance(co.get("plan"), dict) else None,
        "user_count": co.get("user_count"),
        "monthly_spend": co.get("monthly_spend"),
        "created_at": co.get("created_at"),
        "updated_at": co.get("updated_at"),
    }


def register(mcp: FastMCP) -> None:
    """Register Intercom tools with the MCP server."""

    # --- Contacts ---

    @mcp.tool()
    async def intercom_list_contacts(
        page: int = 1,
        per_page: int = 50,
    ) -> dict:
        """List contacts in Intercom with pagination.

        Args:
            page: Page number (default 1).
            per_page: Results per page (default 50, max 150).

        Returns:
            Paginated list of contacts with id, email, name, phone, and timestamps.
        """
        params = {
            "page": page,
            "per_page": min(per_page, 150),
        }
        data = await _request("GET", "contacts", params=params)
        contacts = [_summarize_contact(c) for c in data.get("data", [])]
        pages = data.get("pages", {})
        return {
            "contacts": contacts,
            "total_count": pages.get("total_count"),
            "page": pages.get("page"),
            "per_page": pages.get("per_page"),
            "total_pages": pages.get("total_pages"),
        }

    @mcp.tool()
    async def intercom_get_contact(contact_id: str) -> dict:
        """Get a single Intercom contact by ID.

        Args:
            contact_id: The Intercom contact ID.

        Returns:
            Full contact details.
        """
        data = await _request("GET", f"contacts/{contact_id}")
        return _summarize_contact(data)

    @mcp.tool()
    async def intercom_create_contact(
        role: str = "user",
        email: str = "",
        name: str = "",
        phone: str = "",
        external_id: str = "",
        custom_attributes: Optional[dict] = None,
    ) -> dict:
        """Create a new contact in Intercom.

        Args:
            role: Contact role - 'user' or 'lead' (default 'user').
            email: Email address.
            name: Full name.
            phone: Phone number.
            external_id: Your external identifier for this contact.
            custom_attributes: Additional custom attributes as key-value pairs.

        Returns:
            Created contact details.
        """
        body: dict = {"role": role}
        if email:
            body["email"] = email
        if name:
            body["name"] = name
        if phone:
            body["phone"] = phone
        if external_id:
            body["external_id"] = external_id
        if custom_attributes:
            body["custom_attributes"] = custom_attributes
        data = await _request("POST", "contacts", json=body)
        return _summarize_contact(data)

    @mcp.tool()
    async def intercom_update_contact(
        contact_id: str,
        email: str = "",
        name: str = "",
        phone: str = "",
        role: str = "",
        custom_attributes: Optional[dict] = None,
    ) -> dict:
        """Update an existing Intercom contact.

        Args:
            contact_id: The Intercom contact ID.
            email: New email address (leave empty to keep current).
            name: New name (leave empty to keep current).
            phone: New phone number (leave empty to keep current).
            role: New role - 'user' or 'lead' (leave empty to keep current).
            custom_attributes: Custom attributes to set or update.

        Returns:
            Updated contact details.
        """
        body: dict = {}
        if email:
            body["email"] = email
        if name:
            body["name"] = name
        if phone:
            body["phone"] = phone
        if role:
            body["role"] = role
        if custom_attributes:
            body["custom_attributes"] = custom_attributes
        if not body:
            return {"status": "no_changes", "contact_id": contact_id}
        data = await _request("PUT", f"contacts/{contact_id}", json=body)
        return _summarize_contact(data)

    @mcp.tool()
    async def intercom_search_contacts(
        email: str = "",
        name: str = "",
    ) -> dict:
        """Search Intercom contacts by email or name.

        Args:
            email: Search by exact email match.
            name: Search by name (contains match).

        Returns:
            List of matching contacts.
        """
        filters = []
        if email:
            filters.append({
                "field": "email",
                "operator": "=",
                "value": email,
            })
        if name:
            filters.append({
                "field": "name",
                "operator": "~",
                "value": name,
            })
        if not filters:
            return {"error": "Provide at least one of email or name to search."}

        if len(filters) == 1:
            query = {"filter": filters[0]}
        else:
            query = {
                "operator": "AND",
                "value": filters,
            }

        body = {"query": query}
        data = await _request("POST", "contacts/search", json=body)
        contacts = [_summarize_contact(c) for c in data.get("data", [])]
        pages = data.get("pages", {})
        return {
            "contacts": contacts,
            "total_count": pages.get("total_count"),
        }

    # --- Conversations ---

    @mcp.tool()
    async def intercom_list_conversations(
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        """List conversations in Intercom with pagination.

        Args:
            page: Page number (default 1).
            per_page: Results per page (default 20, max 150).

        Returns:
            Paginated list of conversations.
        """
        params = {
            "page": page,
            "per_page": min(per_page, 150),
        }
        data = await _request("GET", "conversations", params=params)
        conversations = [_summarize_conversation(c) for c in data.get("conversations", [])]
        pages = data.get("pages", {})
        return {
            "conversations": conversations,
            "total_count": pages.get("total_count"),
            "page": pages.get("page"),
            "per_page": pages.get("per_page"),
            "total_pages": pages.get("total_pages"),
        }

    @mcp.tool()
    async def intercom_get_conversation(conversation_id: str) -> dict:
        """Get full details of an Intercom conversation including messages.

        Args:
            conversation_id: The Intercom conversation ID.

        Returns:
            Full conversation details with source, contacts, and conversation parts.
        """
        data = await _request("GET", f"conversations/{conversation_id}")
        source = data.get("source", {})
        parts = data.get("conversation_parts", {}).get("conversation_parts", [])
        messages = [
            {
                "id": p.get("id"),
                "part_type": p.get("part_type"),
                "body": p.get("body"),
                "author_type": p.get("author", {}).get("type"),
                "author_id": p.get("author", {}).get("id"),
                "created_at": p.get("created_at"),
            }
            for p in parts
        ]
        return {
            "id": data.get("id"),
            "title": data.get("title"),
            "state": data.get("state"),
            "open": data.get("open"),
            "read": data.get("read"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "source_subject": source.get("subject"),
            "source_body": source.get("body"),
            "source_author": source.get("author", {}),
            "messages": messages,
        }

    @mcp.tool()
    async def intercom_reply_to_conversation(
        conversation_id: str,
        body: str,
        message_type: str = "comment",
        admin_id: str = "",
        attachment_urls: Optional[list[str]] = None,
    ) -> dict:
        """Reply to an Intercom conversation.

        Args:
            conversation_id: The conversation ID to reply to.
            body: The reply message body (HTML supported).
            message_type: Type of reply - 'comment' (default) or 'note' (internal).
            admin_id: The admin ID sending the reply (required for admin replies).
            attachment_urls: Optional list of attachment URLs.

        Returns:
            The conversation after the reply.
        """
        reply: dict = {
            "message_type": message_type,
            "type": "admin",
            "body": body,
        }
        if admin_id:
            reply["admin_id"] = admin_id
        if attachment_urls:
            reply["attachment_urls"] = attachment_urls
        data = await _request(
            "POST",
            f"conversations/{conversation_id}/reply",
            json=reply,
        )
        return _summarize_conversation(data)

    # --- Companies ---

    @mcp.tool()
    async def intercom_list_companies(
        page: int = 1,
        per_page: int = 50,
        order: str = "desc",
    ) -> dict:
        """List companies in Intercom with pagination.

        Args:
            page: Page number (default 1).
            per_page: Results per page (default 50, max 150).
            order: Sort order - 'asc' or 'desc' (default 'desc').

        Returns:
            Paginated list of companies.
        """
        params = {
            "page": page,
            "per_page": min(per_page, 150),
            "order": order,
        }
        data = await _request("GET", "companies", params=params)
        companies = [_summarize_company(c) for c in data.get("data", [])]
        pages = data.get("pages", {})
        return {
            "companies": companies,
            "total_count": pages.get("total_count"),
            "page": pages.get("page"),
            "per_page": pages.get("per_page"),
            "total_pages": pages.get("total_pages"),
        }

    @mcp.tool()
    async def intercom_get_company(company_id: str) -> dict:
        """Get a single Intercom company by ID.

        Args:
            company_id: The Intercom company ID.

        Returns:
            Full company details.
        """
        data = await _request("GET", f"companies/{company_id}")
        return _summarize_company(data)
