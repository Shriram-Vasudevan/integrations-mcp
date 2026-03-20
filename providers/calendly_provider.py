"""Calendly provider wrapping the Calendly API v2 (api.calendly.com)."""

import os
from typing import Optional

import requests
from mcp.server.fastmcp import FastMCP

CALENDLY_API_BASE = "https://api.calendly.com"


def _get_token() -> str:
    """Return the Calendly access token from environment."""
    token = os.environ.get("CALENDLY_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError(
            "CALENDLY_ACCESS_TOKEN environment variable is required"
        )
    return token


def _request(method: str, path: str, **kwargs) -> dict:
    """Make an authenticated request to the Calendly API."""
    token = _get_token()
    url = f"{CALENDLY_API_BASE}/{path.lstrip('/')}"
    resp = requests.request(
        method,
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=30,
        **kwargs,
    )
    resp.raise_for_status()
    if resp.status_code == 204 or not resp.content:
        return {"status": "ok"}
    return resp.json()


def register(mcp: FastMCP) -> None:
    """Register Calendly tools with the MCP server."""

    @mcp.tool()
    def calendly_get_current_user() -> dict:
        """Get the current authenticated Calendly user.

        Returns:
            User details including uri, name, email, scheduling_url, and timezone.
        """
        data = _request("GET", "users/me")
        user = data.get("resource", {})
        return {
            "uri": user.get("uri", ""),
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "scheduling_url": user.get("scheduling_url", ""),
            "timezone": user.get("timezone", ""),
            "slug": user.get("slug", ""),
            "avatar_url": user.get("avatar_url"),
            "created_at": user.get("created_at", ""),
            "updated_at": user.get("updated_at", ""),
            "current_organization": user.get("current_organization", ""),
        }

    @mcp.tool()
    def calendly_list_event_types(
        user_uri: str,
        active: Optional[bool] = None,
        count: int = 20,
        page_token: Optional[str] = None,
        sort: Optional[str] = None,
    ) -> dict:
        """List event types for a Calendly user.

        Args:
            user_uri: The URI of the user whose event types to list (e.g. from get_current_user).
            active: Filter by active status (optional).
            count: Number of results to return (1-100, default 20).
            page_token: Token for pagination (optional).
            sort: Sort order, e.g. "name:asc" or "name:desc" (optional).

        Returns:
            List of event types with id, name, duration, scheduling_url, and more.
        """
        params: dict = {
            "user": user_uri,
            "count": min(max(1, count), 100),
        }
        if active is not None:
            params["active"] = active
        if page_token:
            params["page_token"] = page_token
        if sort:
            params["sort"] = sort
        data = _request("GET", "event_types", params=params)
        event_types = []
        for et in data.get("collection", []):
            event_types.append({
                "uri": et.get("uri", ""),
                "name": et.get("name", ""),
                "slug": et.get("slug", ""),
                "active": et.get("active", False),
                "duration": et.get("duration"),
                "kind": et.get("kind", ""),
                "type": et.get("type", ""),
                "color": et.get("color", ""),
                "scheduling_url": et.get("scheduling_url", ""),
                "description_plain": et.get("description_plain", ""),
                "created_at": et.get("created_at", ""),
                "updated_at": et.get("updated_at", ""),
            })
        pagination = data.get("pagination", {})
        return {
            "event_types": event_types,
            "next_page_token": pagination.get("next_page_token"),
        }

    @mcp.tool()
    def calendly_list_scheduled_events(
        user_uri: str,
        status: Optional[str] = None,
        min_start_time: Optional[str] = None,
        max_start_time: Optional[str] = None,
        count: int = 20,
        page_token: Optional[str] = None,
        sort: Optional[str] = None,
    ) -> dict:
        """List scheduled events for a Calendly user.

        Args:
            user_uri: The URI of the user whose events to list.
            status: Filter by status: "active" or "canceled" (optional).
            min_start_time: Lower bound for event start time in ISO 8601 format (optional).
            max_start_time: Upper bound for event start time in ISO 8601 format (optional).
            count: Number of results to return (1-100, default 20).
            page_token: Token for pagination (optional).
            sort: Sort order, e.g. "start_time:asc" or "start_time:desc" (optional).

        Returns:
            List of scheduled events with uri, name, status, start/end times, and location.
        """
        params: dict = {
            "user": user_uri,
            "count": min(max(1, count), 100),
        }
        if status:
            params["status"] = status
        if min_start_time:
            params["min_start_time"] = min_start_time
        if max_start_time:
            params["max_start_time"] = max_start_time
        if page_token:
            params["page_token"] = page_token
        if sort:
            params["sort"] = sort
        data = _request("GET", "scheduled_events", params=params)
        events = []
        for ev in data.get("collection", []):
            events.append({
                "uri": ev.get("uri", ""),
                "name": ev.get("name", ""),
                "status": ev.get("status", ""),
                "start_time": ev.get("start_time", ""),
                "end_time": ev.get("end_time", ""),
                "event_type": ev.get("event_type", ""),
                "location": ev.get("location"),
                "created_at": ev.get("created_at", ""),
                "updated_at": ev.get("updated_at", ""),
                "cancellation": ev.get("cancellation"),
            })
        pagination = data.get("pagination", {})
        return {
            "events": events,
            "next_page_token": pagination.get("next_page_token"),
        }

    @mcp.tool()
    def calendly_get_event(event_uuid: str) -> dict:
        """Get details of a specific scheduled event.

        Args:
            event_uuid: The UUID of the scheduled event (the last segment of the event URI).

        Returns:
            Event details including name, status, start/end times, location, and invitees counter.
        """
        data = _request("GET", f"scheduled_events/{event_uuid}")
        ev = data.get("resource", {})
        return {
            "uri": ev.get("uri", ""),
            "name": ev.get("name", ""),
            "status": ev.get("status", ""),
            "start_time": ev.get("start_time", ""),
            "end_time": ev.get("end_time", ""),
            "event_type": ev.get("event_type", ""),
            "location": ev.get("location"),
            "invitees_counter": ev.get("invitees_counter"),
            "created_at": ev.get("created_at", ""),
            "updated_at": ev.get("updated_at", ""),
            "event_memberships": ev.get("event_memberships", []),
            "cancellation": ev.get("cancellation"),
        }

    @mcp.tool()
    def calendly_cancel_event(
        event_uuid: str,
        reason: Optional[str] = None,
    ) -> dict:
        """Cancel a scheduled Calendly event.

        Args:
            event_uuid: The UUID of the scheduled event to cancel.
            reason: Reason for cancellation (optional).

        Returns:
            Cancellation details including canceler name and reason.
        """
        payload: dict = {}
        if reason:
            payload["reason"] = reason
        data = _request("POST", f"scheduled_events/{event_uuid}/cancellation", json=payload)
        resource = data.get("resource", {})
        return {
            "canceled_by": resource.get("canceled_by", ""),
            "reason": resource.get("reason", ""),
            "canceler_type": resource.get("canceler_type", ""),
            "created_at": resource.get("created_at", ""),
        }

    @mcp.tool()
    def calendly_list_invitees(
        event_uuid: str,
        status: Optional[str] = None,
        count: int = 20,
        page_token: Optional[str] = None,
        sort: Optional[str] = None,
    ) -> dict:
        """List invitees for a scheduled Calendly event.

        Args:
            event_uuid: The UUID of the scheduled event.
            status: Filter by status: "active" or "canceled" (optional).
            count: Number of results to return (1-100, default 20).
            page_token: Token for pagination (optional).
            sort: Sort order, e.g. "created_at:asc" (optional).

        Returns:
            List of invitees with name, email, status, and tracking info.
        """
        params: dict = {"count": min(max(1, count), 100)}
        if status:
            params["status"] = status
        if page_token:
            params["page_token"] = page_token
        if sort:
            params["sort"] = sort
        data = _request("GET", f"scheduled_events/{event_uuid}/invitees", params=params)
        invitees = []
        for inv in data.get("collection", []):
            invitees.append({
                "uri": inv.get("uri", ""),
                "name": inv.get("name", ""),
                "email": inv.get("email", ""),
                "status": inv.get("status", ""),
                "timezone": inv.get("timezone", ""),
                "created_at": inv.get("created_at", ""),
                "updated_at": inv.get("updated_at", ""),
                "questions_and_answers": inv.get("questions_and_answers", []),
                "tracking": inv.get("tracking"),
                "cancellation": inv.get("cancellation"),
                "reschedule_url": inv.get("reschedule_url", ""),
                "cancel_url": inv.get("cancel_url", ""),
            })
        pagination = data.get("pagination", {})
        return {
            "invitees": invitees,
            "next_page_token": pagination.get("next_page_token"),
        }

    @mcp.tool()
    def calendly_create_scheduling_link(
        owner_uri: str,
        max_event_count: int = 1,
        owner_type: str = "EventType",
    ) -> dict:
        """Create a single-use scheduling link for a Calendly event type.

        Args:
            owner_uri: The URI of the event type to create a link for.
            max_event_count: Maximum number of events that can be scheduled using this link (default 1).
            owner_type: Type of the owner, typically "EventType" (default "EventType").

        Returns:
            Scheduling link details including booking_url and owner info.
        """
        payload = {
            "max_event_count": max_event_count,
            "owner": owner_uri,
            "owner_type": owner_type,
        }
        data = _request("POST", "scheduling_links", json=payload)
        resource = data.get("resource", {})
        return {
            "booking_url": resource.get("booking_url", ""),
            "owner": resource.get("owner", ""),
            "owner_type": resource.get("owner_type", ""),
        }

    @mcp.tool()
    def calendly_list_organization_memberships(
        organization_uri: str,
        count: int = 20,
        page_token: Optional[str] = None,
        email: Optional[str] = None,
    ) -> dict:
        """List organization memberships in Calendly.

        Args:
            organization_uri: The URI of the organization.
            count: Number of results to return (1-100, default 20).
            page_token: Token for pagination (optional).
            email: Filter by member email (optional).

        Returns:
            List of organization memberships with user details and role.
        """
        params: dict = {
            "organization": organization_uri,
            "count": min(max(1, count), 100),
        }
        if page_token:
            params["page_token"] = page_token
        if email:
            params["email"] = email
        data = _request("GET", "organization_memberships", params=params)
        memberships = []
        for m in data.get("collection", []):
            user = m.get("user", {})
            memberships.append({
                "uri": m.get("uri", ""),
                "role": m.get("role", ""),
                "user_uri": user.get("uri", ""),
                "user_name": user.get("name", ""),
                "user_email": user.get("email", ""),
                "created_at": m.get("created_at", ""),
                "updated_at": m.get("updated_at", ""),
            })
        pagination = data.get("pagination", {})
        return {
            "memberships": memberships,
            "next_page_token": pagination.get("next_page_token"),
        }

    @mcp.tool()
    def calendly_remove_invitee(invitee_uuid: str) -> dict:
        """Remove (delete) an invitee's data from a Calendly event.

        Args:
            invitee_uuid: The UUID of the invitee to remove.

        Returns:
            Confirmation of removal.
        """
        return _request("DELETE", f"invitee_no_shows/{invitee_uuid}")
