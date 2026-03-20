"""Supabase provider wrapping the Supabase Management & Data REST APIs."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP


# ---------------------------------------------------------------------------
# Auth & config helpers
# ---------------------------------------------------------------------------

def _get_env(name: str) -> str:
    """Return an environment variable or raise with a clear message."""
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"{name} environment variable is not set")
    return val


def _project_url() -> str:
    """Return the Supabase project URL (e.g. https://<ref>.supabase.co)."""
    return _get_env("SUPABASE_URL").rstrip("/")


def _service_role_key() -> str:
    """Return the service-role key used for data-plane (PostgREST) requests."""
    return _get_env("SUPABASE_SERVICE_ROLE_KEY")


def _management_token() -> str:
    """Return the Supabase Management API access token.

    Generate one at https://supabase.com/dashboard/account/tokens
    Required only for management-plane tools (list projects, manage users, etc.).
    """
    return _get_env("SUPABASE_ACCESS_TOKEN")


def _project_ref() -> str:
    """Extract the project ref from the project URL or from a dedicated env var."""
    explicit = os.environ.get("SUPABASE_PROJECT_REF")
    if explicit:
        return explicit
    # Derive from URL: https://<ref>.supabase.co
    url = _project_url()
    host = url.split("//", 1)[-1].split(".")[0]
    return host


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

_MGMT_BASE = "https://api.supabase.com/v1"


def _data_headers() -> dict:
    """Headers for PostgREST / data-plane requests."""
    key = _service_role_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _mgmt_headers() -> dict:
    """Headers for Supabase Management API requests."""
    return {
        "Authorization": f"Bearer {_management_token()}",
        "Content-Type": "application/json",
    }


async def _data_request(method: str, path: str, **kwargs) -> dict | list:
    """Authenticated request against the project's PostgREST / REST API."""
    url = f"{_project_url()}/{path.lstrip('/')}"
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method, url, headers=_data_headers(), timeout=60, **kwargs,
        )
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {"status": "ok"}
        return resp.json()


async def _mgmt_request(method: str, path: str, **kwargs) -> dict | list:
    """Authenticated request against the Supabase Management API."""
    url = f"{_MGMT_BASE}/{path.lstrip('/')}"
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method, url, headers=_mgmt_headers(), timeout=60, **kwargs,
        )
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {"status": "ok"}
        return resp.json()


# ---------------------------------------------------------------------------
# SQL execution via the pg-meta / REST SQL endpoint
# ---------------------------------------------------------------------------

async def _execute_sql(query: str) -> dict | list:
    """Execute arbitrary SQL via the Supabase REST SQL endpoint.

    Uses POST /rest/v1/rpc  with a thin server-side function, or the
    Management API's /v1/projects/{ref}/database/query endpoint.
    """
    ref = _project_ref()
    return await _mgmt_request(
        "POST",
        f"projects/{ref}/database/query",
        json={"query": query},
    )


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register(mcp: FastMCP) -> None:
    """Register Supabase tools with the MCP server."""

    # ------------------------------------------------------------------
    # SQL tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def supabase_execute_sql(query: str) -> dict | list:
        """Execute a SQL query against the Supabase Postgres database.

        Uses the Management API database/query endpoint so any valid SQL
        (SELECT, INSERT, CREATE TABLE, etc.) can be run.

        Requires SUPABASE_ACCESS_TOKEN and SUPABASE_URL (or SUPABASE_PROJECT_REF).

        Args:
            query: The SQL statement to execute.

        Returns:
            Query results as a list of row objects, or status info.
        """
        return await _execute_sql(query)

    @mcp.tool()
    async def supabase_list_tables(schema: str = "public") -> dict | list:
        """List all tables in a Supabase Postgres schema.

        Args:
            schema: The database schema to list tables from (default "public").

        Returns:
            List of tables with name, schema, row-count estimate, and size.
        """
        sql = f"""
            SELECT
                schemaname   AS schema,
                tablename    AS name,
                hasindexes   AS has_indexes,
                hasrules     AS has_rules,
                hastriggers  AS has_triggers
            FROM pg_catalog.pg_tables
            WHERE schemaname = '{schema}'
            ORDER BY tablename;
        """
        return await _execute_sql(sql)

    @mcp.tool()
    async def supabase_describe_table(
        table: str,
        schema: str = "public",
    ) -> dict | list:
        """Describe the columns of a table in the Supabase database.

        Args:
            table: The table name.
            schema: The schema the table belongs to (default "public").

        Returns:
            Column definitions including name, type, nullable, and default.
        """
        sql = f"""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = '{schema}'
              AND table_name   = '{table}'
            ORDER BY ordinal_position;
        """
        return await _execute_sql(sql)

    # ------------------------------------------------------------------
    # PostgREST data-access tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def supabase_select_rows(
        table: str,
        select: str = "*",
        filters: Optional[str] = None,
        limit: int = 100,
    ) -> dict | list:
        """Read rows from a Supabase table via the PostgREST API.

        Args:
            table: The table name (must be in the exposed schema).
            select: Comma-separated column list or \"*\" (default).
            filters: PostgREST filter query string, e.g. "age=gt.18&active=eq.true". Optional.
            limit: Maximum number of rows to return (default 100).

        Returns:
            List of matching rows.
        """
        params = {"select": select, "limit": str(limit)}
        if filters:
            for part in filters.split("&"):
                key, _, value = part.partition("=")
                params[key] = value
        return await _data_request("GET", f"rest/v1/{table}", params=params)

    @mcp.tool()
    async def supabase_insert_rows(
        table: str,
        rows: list[dict],
    ) -> dict | list:
        """Insert one or more rows into a Supabase table via PostgREST.

        Args:
            table: The target table name.
            rows: A list of row objects to insert.

        Returns:
            The inserted rows (with generated columns populated).
        """
        return await _data_request("POST", f"rest/v1/{table}", json=rows)

    # ------------------------------------------------------------------
    # User / Auth management (Management API)
    # ------------------------------------------------------------------

    @mcp.tool()
    async def supabase_list_users(
        page: int = 1,
        per_page: int = 50,
    ) -> dict | list:
        """List auth users in the Supabase project.

        Args:
            page: Page number (1-based, default 1).
            per_page: Users per page (default 50, max 1000).

        Returns:
            Paginated list of auth users with id, email, phone, created_at, etc.
        """
        ref = _project_ref()
        return await _mgmt_request(
            "GET",
            f"projects/{ref}/auth/users",
            params={"page": page, "per_page": per_page},
        )

    @mcp.tool()
    async def supabase_get_user(user_id: str) -> dict:
        """Get details of a single auth user by ID.

        Args:
            user_id: The UUID of the user.

        Returns:
            User object with id, email, phone, metadata, created_at, etc.
        """
        ref = _project_ref()
        return await _mgmt_request("GET", f"projects/{ref}/auth/users/{user_id}")

    @mcp.tool()
    async def supabase_create_user(
        email: str,
        password: str,
        email_confirm: bool = True,
        user_metadata: Optional[dict] = None,
    ) -> dict:
        """Create a new auth user in the Supabase project.

        Args:
            email: The user's email address.
            password: The user's password.
            email_confirm: Auto-confirm the email (default True).
            user_metadata: Optional metadata dict to attach to the user.

        Returns:
            The created user object.
        """
        ref = _project_ref()
        body: dict = {
            "email": email,
            "password": password,
            "email_confirm": email_confirm,
        }
        if user_metadata:
            body["user_metadata"] = user_metadata
        return await _mgmt_request("POST", f"projects/{ref}/auth/users", json=body)

    @mcp.tool()
    async def supabase_update_user(
        user_id: str,
        email: Optional[str] = None,
        password: Optional[str] = None,
        user_metadata: Optional[dict] = None,
        ban_duration: Optional[str] = None,
    ) -> dict:
        """Update an existing auth user.

        Args:
            user_id: The UUID of the user to update.
            email: New email address. Optional.
            password: New password. Optional.
            user_metadata: Metadata to merge into the user record. Optional.
            ban_duration: Ban duration (e.g. "24h", "none" to unban). Optional.

        Returns:
            The updated user object.
        """
        ref = _project_ref()
        body: dict = {}
        if email is not None:
            body["email"] = email
        if password is not None:
            body["password"] = password
        if user_metadata is not None:
            body["user_metadata"] = user_metadata
        if ban_duration is not None:
            body["ban_duration"] = ban_duration
        return await _mgmt_request("PUT", f"projects/{ref}/auth/users/{user_id}", json=body)

    @mcp.tool()
    async def supabase_delete_user(user_id: str) -> dict:
        """Delete an auth user from the Supabase project.

        Args:
            user_id: The UUID of the user to delete.

        Returns:
            Confirmation status.
        """
        ref = _project_ref()
        return await _mgmt_request("DELETE", f"projects/{ref}/auth/users/{user_id}")

    # ------------------------------------------------------------------
    # Project info (Management API)
    # ------------------------------------------------------------------

    @mcp.tool()
    async def supabase_list_projects() -> list:
        """List all Supabase projects accessible with the current access token.

        Returns:
            List of projects with id, name, region, status, and database info.
        """
        return await _mgmt_request("GET", "projects")
