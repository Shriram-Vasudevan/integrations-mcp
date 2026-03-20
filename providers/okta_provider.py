"""Okta provider wrapping the Okta Management API using httpx."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP


def _get_domain() -> str:
    """Return the Okta domain from environment (e.g. mycompany.okta.com)."""
    domain = os.environ.get("OKTA_DOMAIN")
    if not domain:
        raise RuntimeError("OKTA_DOMAIN environment variable is not set")
    return domain.rstrip("/")


def _get_token() -> str:
    """Return the Okta API token from environment."""
    token = os.environ.get("OKTA_API_TOKEN")
    if not token:
        raise RuntimeError("OKTA_API_TOKEN environment variable is not set")
    return token


def _base_url() -> str:
    return f"https://{_get_domain()}/api/v1"


async def _request(method: str, path: str, **kwargs) -> dict | list:
    """Make an authenticated request to the Okta Management API."""
    url = f"{_base_url()}/{path.lstrip('/')}"
    headers = {
        "Authorization": f"SSWS {_get_token()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            url,
            headers=headers,
            timeout=30,
            **kwargs,
        )
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {"status": "ok"}
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register Okta tools with the MCP server."""

    @mcp.tool()
    async def okta_list_users(
        limit: int = 25,
        search: Optional[str] = None,
        after: Optional[str] = None,
    ) -> dict:
        """List Okta users with optional search and pagination.

        Args:
            limit: Number of users to return (1-200, default 25).
            search: Okta search expression (e.g. 'profile.email eq "user@example.com"' or 'status eq "ACTIVE"'). Uses the Okta search query language.
            after: Pagination cursor returned from a previous request (optional).

        Returns:
            List of users with id, status, profile, and timestamps.
        """
        params: dict = {"limit": min(max(1, limit), 200)}
        if search:
            params["search"] = search
        if after:
            params["after"] = after
        data = await _request("GET", "users", params=params)
        users = []
        for u in data if isinstance(data, list) else []:
            profile = u.get("profile", {})
            users.append({
                "id": u["id"],
                "status": u.get("status"),
                "firstName": profile.get("firstName"),
                "lastName": profile.get("lastName"),
                "email": profile.get("email"),
                "login": profile.get("login"),
                "created": u.get("created"),
                "lastLogin": u.get("lastLogin"),
                "lastUpdated": u.get("lastUpdated"),
            })
        return {"users": users}

    @mcp.tool()
    async def okta_get_user(user_id: str) -> dict:
        """Retrieve a specific Okta user by ID or login.

        Args:
            user_id: The user ID (e.g. "00u1ab2cd3") or login/email.

        Returns:
            User details including profile, status, and timestamps.
        """
        u = await _request("GET", f"users/{user_id}")
        profile = u.get("profile", {}) if isinstance(u, dict) else {}
        return {
            "id": u["id"],
            "status": u.get("status"),
            "profile": {
                "firstName": profile.get("firstName"),
                "lastName": profile.get("lastName"),
                "email": profile.get("email"),
                "login": profile.get("login"),
                "mobilePhone": profile.get("mobilePhone"),
                "secondEmail": profile.get("secondEmail"),
                "displayName": profile.get("displayName"),
                "title": profile.get("title"),
                "department": profile.get("department"),
                "organization": profile.get("organization"),
            },
            "created": u.get("created"),
            "activated": u.get("activated"),
            "lastLogin": u.get("lastLogin"),
            "lastUpdated": u.get("lastUpdated"),
            "statusChanged": u.get("statusChanged"),
            "passwordChanged": u.get("passwordChanged"),
        }

    @mcp.tool()
    async def okta_create_user(
        first_name: str,
        last_name: str,
        email: str,
        login: str,
        activate: bool = True,
        mobile_phone: Optional[str] = None,
        title: Optional[str] = None,
        department: Optional[str] = None,
    ) -> dict:
        """Create a new Okta user.

        Args:
            first_name: User's first name.
            last_name: User's last name.
            email: User's primary email address.
            login: User's login (usually email).
            activate: Whether to activate the user immediately (default True). If True, user receives activation email.
            mobile_phone: User's mobile phone number (optional).
            title: User's job title (optional).
            department: User's department (optional).

        Returns:
            The newly created user with id, status, and profile.
        """
        profile: dict = {
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "login": login,
        }
        if mobile_phone:
            profile["mobilePhone"] = mobile_phone
        if title:
            profile["title"] = title
        if department:
            profile["department"] = department

        params = {"activate": str(activate).lower()}
        u = await _request("POST", "users", params=params, json={"profile": profile})
        p = u.get("profile", {}) if isinstance(u, dict) else {}
        return {
            "id": u["id"],
            "status": u.get("status"),
            "profile": {
                "firstName": p.get("firstName"),
                "lastName": p.get("lastName"),
                "email": p.get("email"),
                "login": p.get("login"),
            },
            "created": u.get("created"),
        }

    @mcp.tool()
    async def okta_update_user(
        user_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        login: Optional[str] = None,
        mobile_phone: Optional[str] = None,
        title: Optional[str] = None,
        department: Optional[str] = None,
    ) -> dict:
        """Update an existing Okta user's profile. Only provided fields are updated.

        Args:
            user_id: The user ID to update.
            first_name: Updated first name (optional).
            last_name: Updated last name (optional).
            email: Updated email (optional).
            login: Updated login (optional).
            mobile_phone: Updated mobile phone (optional).
            title: Updated job title (optional).
            department: Updated department (optional).

        Returns:
            Updated user with id, status, and profile.
        """
        profile: dict = {}
        if first_name is not None:
            profile["firstName"] = first_name
        if last_name is not None:
            profile["lastName"] = last_name
        if email is not None:
            profile["email"] = email
        if login is not None:
            profile["login"] = login
        if mobile_phone is not None:
            profile["mobilePhone"] = mobile_phone
        if title is not None:
            profile["title"] = title
        if department is not None:
            profile["department"] = department

        u = await _request("POST", f"users/{user_id}", json={"profile": profile})
        p = u.get("profile", {}) if isinstance(u, dict) else {}
        return {
            "id": u["id"],
            "status": u.get("status"),
            "profile": {
                "firstName": p.get("firstName"),
                "lastName": p.get("lastName"),
                "email": p.get("email"),
                "login": p.get("login"),
                "mobilePhone": p.get("mobilePhone"),
                "title": p.get("title"),
                "department": p.get("department"),
            },
            "lastUpdated": u.get("lastUpdated"),
        }

    @mcp.tool()
    async def okta_deactivate_user(user_id: str) -> dict:
        """Deactivate an Okta user. This transitions the user to DEPROVISIONED status.

        Args:
            user_id: The user ID to deactivate.

        Returns:
            Confirmation of deactivation.
        """
        await _request("POST", f"users/{user_id}/lifecycle/deactivate")
        return {"status": "deactivated", "user_id": user_id}

    @mcp.tool()
    async def okta_list_groups(
        limit: int = 25,
        q: Optional[str] = None,
        after: Optional[str] = None,
    ) -> dict:
        """List Okta groups with optional search.

        Args:
            limit: Number of groups to return (1-200, default 25).
            q: Search query that matches group name prefix (optional).
            after: Pagination cursor from a previous request (optional).

        Returns:
            List of groups with id, name, description, and type.
        """
        params: dict = {"limit": min(max(1, limit), 200)}
        if q:
            params["q"] = q
        if after:
            params["after"] = after
        data = await _request("GET", "groups", params=params)
        groups = []
        for g in data if isinstance(data, list) else []:
            profile = g.get("profile", {})
            groups.append({
                "id": g["id"],
                "name": profile.get("name"),
                "description": profile.get("description"),
                "type": g.get("type"),
                "created": g.get("created"),
                "lastUpdated": g.get("lastUpdated"),
                "lastMembershipUpdated": g.get("lastMembershipUpdated"),
            })
        return {"groups": groups}

    @mcp.tool()
    async def okta_get_group(group_id: str) -> dict:
        """Retrieve a specific Okta group by ID.

        Args:
            group_id: The group ID (e.g. "00g1ab2cd3").

        Returns:
            Group details including name, description, type, and timestamps.
        """
        g = await _request("GET", f"groups/{group_id}")
        profile = g.get("profile", {}) if isinstance(g, dict) else {}
        return {
            "id": g["id"],
            "name": profile.get("name"),
            "description": profile.get("description"),
            "type": g.get("type"),
            "created": g.get("created"),
            "lastUpdated": g.get("lastUpdated"),
            "lastMembershipUpdated": g.get("lastMembershipUpdated"),
        }

    @mcp.tool()
    async def okta_list_group_members(
        group_id: str,
        limit: int = 25,
        after: Optional[str] = None,
    ) -> dict:
        """List members of a specific Okta group.

        Args:
            group_id: The group ID to list members for.
            limit: Number of members to return (1-200, default 25).
            after: Pagination cursor from a previous request (optional).

        Returns:
            List of group members with id, status, and profile info.
        """
        params: dict = {"limit": min(max(1, limit), 200)}
        if after:
            params["after"] = after
        data = await _request("GET", f"groups/{group_id}/users", params=params)
        members = []
        for u in data if isinstance(data, list) else []:
            profile = u.get("profile", {})
            members.append({
                "id": u["id"],
                "status": u.get("status"),
                "firstName": profile.get("firstName"),
                "lastName": profile.get("lastName"),
                "email": profile.get("email"),
                "login": profile.get("login"),
            })
        return {"group_id": group_id, "members": members}

    @mcp.tool()
    async def okta_list_apps(
        limit: int = 25,
        q: Optional[str] = None,
        after: Optional[str] = None,
    ) -> dict:
        """List Okta applications with optional search.

        Args:
            limit: Number of apps to return (1-200, default 25).
            q: Search query that matches app name or label prefix (optional).
            after: Pagination cursor from a previous request (optional).

        Returns:
            List of applications with id, name, label, status, and sign-on mode.
        """
        params: dict = {"limit": min(max(1, limit), 200)}
        if q:
            params["q"] = q
        if after:
            params["after"] = after
        data = await _request("GET", "apps", params=params)
        apps = []
        for a in data if isinstance(data, list) else []:
            apps.append({
                "id": a["id"],
                "name": a.get("name"),
                "label": a.get("label"),
                "status": a.get("status"),
                "signOnMode": a.get("signOnMode"),
                "created": a.get("created"),
                "lastUpdated": a.get("lastUpdated"),
            })
        return {"apps": apps}

    @mcp.tool()
    async def okta_get_app(app_id: str) -> dict:
        """Retrieve a specific Okta application by ID.

        Args:
            app_id: The application ID (e.g. "0oa1ab2cd3").

        Returns:
            Application details including name, label, status, sign-on mode, and settings.
        """
        a = await _request("GET", f"apps/{app_id}")
        settings = a.get("settings", {}) if isinstance(a, dict) else {}
        return {
            "id": a["id"],
            "name": a.get("name"),
            "label": a.get("label"),
            "status": a.get("status"),
            "signOnMode": a.get("signOnMode"),
            "created": a.get("created"),
            "lastUpdated": a.get("lastUpdated"),
            "accessibility": a.get("accessibility", {}),
            "visibility": a.get("visibility", {}),
            "features": a.get("features", []),
            "settings": {
                "app": settings.get("app", {}),
                "signOn": settings.get("signOn", {}),
            },
        }
