"""Sentry provider wrapping the Sentry Web API (sentry.io/api/0/)."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

API_BASE = "https://sentry.io/api/0"


def _get_auth_token() -> str:
    """Return the Sentry auth token from environment."""
    token = os.environ.get("SENTRY_AUTH_TOKEN")
    if not token:
        raise RuntimeError("SENTRY_AUTH_TOKEN environment variable is not set")
    return token


def _headers() -> dict:
    """Return standard Sentry authentication headers."""
    return {
        "Authorization": f"Bearer {_get_auth_token()}",
        "Content-Type": "application/json",
    }


async def _request(method: str, path: str, **kwargs) -> dict:
    """Make an authenticated request to the Sentry API."""
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
        data = resp.json()
        # Sentry list endpoints return JSON arrays; wrap them for consistency.
        if isinstance(data, list):
            return {"results": data}
        return data


def register(mcp: FastMCP) -> None:
    """Register Sentry tools with the MCP server."""

    # ── Projects ─────────────────────────────────────────────────────

    @mcp.tool()
    async def sentry_list_projects(
        organization_slug: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> dict:
        """List Sentry projects accessible to the authenticated token.

        Args:
            organization_slug: Filter projects by organization slug. If omitted, lists projects across all organizations the token can access.
            cursor: Pagination cursor from a previous response (optional).

        Returns:
            List of projects with slug, name, id, platform, organization, and date created.
        """
        params: dict = {}
        if cursor:
            params["cursor"] = cursor

        if organization_slug:
            data = await _request(
                "GET", f"organizations/{organization_slug}/projects/", params=params
            )
        else:
            data = await _request("GET", "projects/", params=params)

        projects = []
        for p in data.get("results", [data] if "slug" in data else []):
            org = p.get("organization", {})
            projects.append({
                "id": p.get("id", ""),
                "slug": p.get("slug", ""),
                "name": p.get("name", ""),
                "platform": p.get("platform"),
                "status": p.get("status", ""),
                "organization_slug": org.get("slug", ""),
                "organization_name": org.get("name", ""),
                "date_created": p.get("dateCreated", ""),
            })
        return {"projects": projects, "count": len(projects)}

    @mcp.tool()
    async def sentry_get_project(
        organization_slug: str,
        project_slug: str,
    ) -> dict:
        """Get details of a specific Sentry project.

        Args:
            organization_slug: The organization slug (e.g. "my-org").
            project_slug: The project slug (e.g. "my-project").

        Returns:
            Project details including name, platform, team, stats, and configuration.
        """
        data = await _request(
            "GET", f"projects/{organization_slug}/{project_slug}/"
        )
        org = data.get("organization", {})
        return {
            "id": data.get("id", ""),
            "slug": data.get("slug", ""),
            "name": data.get("name", ""),
            "platform": data.get("platform"),
            "status": data.get("status", ""),
            "organization_slug": org.get("slug", ""),
            "organization_name": org.get("name", ""),
            "date_created": data.get("dateCreated", ""),
            "first_event": data.get("firstEvent"),
            "has_access": data.get("hasAccess", False),
            "features": data.get("features", []),
        }

    # ── Issues ───────────────────────────────────────────────────────

    @mcp.tool()
    async def sentry_list_issues(
        organization_slug: str,
        project_slug: str,
        query: Optional[str] = None,
        sort: str = "date",
        limit: int = 25,
        cursor: Optional[str] = None,
    ) -> dict:
        """List recent issues for a Sentry project.

        Args:
            organization_slug: The organization slug.
            project_slug: The project slug.
            query: Sentry search query to filter issues (e.g. "is:unresolved level:error"). Optional.
            sort: Sort order: "date" (most recent), "new" (newest created), "priority", "freq" (most frequent), or "user" (most users). Default "date".
            limit: Max number of issues to return (default 25, max 100).
            cursor: Pagination cursor from a previous response (optional).

        Returns:
            List of issues with id, title, level, status, count, first/last seen, and assignee.
        """
        params: dict = {
            "sort": sort,
            "limit": min(limit, 100),
            "project": project_slug,
        }
        if query:
            params["query"] = query
        if cursor:
            params["cursor"] = cursor

        data = await _request(
            "GET", f"projects/{organization_slug}/{project_slug}/issues/", params=params
        )

        issues = []
        for issue in data.get("results", []):
            assignee = issue.get("assignedTo")
            issues.append({
                "id": issue.get("id", ""),
                "short_id": issue.get("shortId", ""),
                "title": issue.get("title", ""),
                "culprit": issue.get("culprit", ""),
                "level": issue.get("level", ""),
                "status": issue.get("status", ""),
                "count": issue.get("count", "0"),
                "user_count": issue.get("userCount", 0),
                "first_seen": issue.get("firstSeen", ""),
                "last_seen": issue.get("lastSeen", ""),
                "assignee_name": assignee.get("name", "") if assignee else None,
                "assignee_email": assignee.get("email", "") if assignee else None,
                "permalink": issue.get("permalink", ""),
            })
        return {"issues": issues, "count": len(issues)}

    @mcp.tool()
    async def sentry_get_issue(issue_id: str) -> dict:
        """Get details of a specific Sentry issue by ID.

        Args:
            issue_id: The numeric issue ID (e.g. "1234567890").

        Returns:
            Full issue details including title, metadata, stats, tags, and assignee.
        """
        data = await _request("GET", f"issues/{issue_id}/")
        assignee = data.get("assignedTo")
        stats = data.get("stats", {})
        return {
            "id": data.get("id", ""),
            "short_id": data.get("shortId", ""),
            "title": data.get("title", ""),
            "culprit": data.get("culprit", ""),
            "level": data.get("level", ""),
            "status": data.get("status", ""),
            "type": data.get("type", ""),
            "count": data.get("count", "0"),
            "user_count": data.get("userCount", 0),
            "first_seen": data.get("firstSeen", ""),
            "last_seen": data.get("lastSeen", ""),
            "assignee_name": assignee.get("name", "") if assignee else None,
            "assignee_email": assignee.get("email", "") if assignee else None,
            "metadata": data.get("metadata", {}),
            "stats_24h": stats.get("24h", []),
            "permalink": data.get("permalink", ""),
            "project": {
                "id": data.get("project", {}).get("id", ""),
                "slug": data.get("project", {}).get("slug", ""),
                "name": data.get("project", {}).get("name", ""),
            },
        }

    # ── Events ───────────────────────────────────────────────────────

    @mcp.tool()
    async def sentry_list_issue_events(
        issue_id: str,
        limit: int = 25,
        cursor: Optional[str] = None,
    ) -> dict:
        """List events for a specific Sentry issue.

        Args:
            issue_id: The numeric issue ID.
            limit: Max number of events to return (default 25, max 100).
            cursor: Pagination cursor from a previous response (optional).

        Returns:
            List of events with id, timestamp, message, tags, and user info.
        """
        params: dict = {"limit": min(limit, 100)}
        if cursor:
            params["cursor"] = cursor

        data = await _request("GET", f"issues/{issue_id}/events/", params=params)

        events = []
        for ev in data.get("results", []):
            user = ev.get("user", {}) or {}
            events.append({
                "event_id": ev.get("eventID", ""),
                "id": ev.get("id", ""),
                "title": ev.get("title", ""),
                "message": ev.get("message", ""),
                "date_created": ev.get("dateCreated", ""),
                "platform": ev.get("platform", ""),
                "user_id": user.get("id"),
                "user_email": user.get("email"),
                "user_ip": user.get("ip_address"),
                "tags": {
                    t.get("key", ""): t.get("value", "")
                    for t in ev.get("tags", [])
                },
            })
        return {"events": events, "count": len(events)}

    @mcp.tool()
    async def sentry_get_event(
        organization_slug: str,
        project_slug: str,
        event_id: str,
    ) -> dict:
        """Get full details of a specific Sentry event.

        Args:
            organization_slug: The organization slug.
            project_slug: The project slug.
            event_id: The event ID (e.g. "abc123def456...").

        Returns:
            Full event details including exception stacktrace, breadcrumbs, context, tags, and user info.
        """
        data = await _request(
            "GET",
            f"projects/{organization_slug}/{project_slug}/events/{event_id}/",
        )
        user = data.get("user", {}) or {}
        sdk = data.get("sdk", {}) or {}
        contexts = data.get("contexts", {}) or {}

        # Extract exception info if present
        exception_info = []
        for entry in data.get("entries", []):
            if entry.get("type") == "exception":
                for exc in entry.get("data", {}).get("values", []):
                    frames = []
                    stacktrace = exc.get("stacktrace", {}) or {}
                    for frame in stacktrace.get("frames", []):
                        frames.append({
                            "filename": frame.get("filename", ""),
                            "function": frame.get("function", ""),
                            "lineno": frame.get("lineNo"),
                            "colno": frame.get("colNo"),
                            "context_line": frame.get("contextLine", ""),
                            "in_app": frame.get("inApp", False),
                        })
                    exception_info.append({
                        "type": exc.get("type", ""),
                        "value": exc.get("value", ""),
                        "mechanism": exc.get("mechanism", {}),
                        "frames": frames,
                    })

        # Extract breadcrumbs if present
        breadcrumbs = []
        for entry in data.get("entries", []):
            if entry.get("type") == "breadcrumbs":
                for crumb in entry.get("data", {}).get("values", [])[-20:]:
                    breadcrumbs.append({
                        "category": crumb.get("category", ""),
                        "type": crumb.get("type", ""),
                        "message": crumb.get("message", ""),
                        "level": crumb.get("level", ""),
                        "timestamp": crumb.get("timestamp", ""),
                        "data": crumb.get("data", {}),
                    })

        return {
            "event_id": data.get("eventID", ""),
            "title": data.get("title", ""),
            "message": data.get("message", ""),
            "platform": data.get("platform", ""),
            "date_created": data.get("dateCreated", ""),
            "date_received": data.get("dateReceived", ""),
            "user": {
                "id": user.get("id"),
                "email": user.get("email"),
                "username": user.get("username"),
                "ip_address": user.get("ip_address"),
            },
            "sdk": {
                "name": sdk.get("name", ""),
                "version": sdk.get("version", ""),
            },
            "contexts": {
                "os": contexts.get("os", {}),
                "browser": contexts.get("browser", {}),
                "runtime": contexts.get("runtime", {}),
                "device": contexts.get("device", {}),
            },
            "tags": {
                t.get("key", ""): t.get("value", "")
                for t in data.get("tags", [])
            },
            "exceptions": exception_info,
            "breadcrumbs": breadcrumbs,
        }
