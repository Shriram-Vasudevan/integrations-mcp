"""Snowflake provider wrapping the Snowflake SQL REST API (/api/v2/statements)."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP


def _get_account() -> str:
    """Return the Snowflake account identifier from environment."""
    val = os.environ.get("SNOWFLAKE_ACCOUNT")
    if not val:
        raise RuntimeError("SNOWFLAKE_ACCOUNT environment variable is not set")
    return val


def _get_user() -> str:
    """Return the Snowflake username from environment."""
    val = os.environ.get("SNOWFLAKE_USER")
    if not val:
        raise RuntimeError("SNOWFLAKE_USER environment variable is not set")
    return val


def _get_password() -> str:
    """Return the Snowflake password from environment."""
    val = os.environ.get("SNOWFLAKE_PASSWORD")
    if not val:
        raise RuntimeError("SNOWFLAKE_PASSWORD environment variable is not set")
    return val


def _base_url() -> str:
    """Return the Snowflake SQL REST API base URL."""
    account = _get_account()
    return f"https://{account}.snowflakecomputing.com"


def _headers() -> dict:
    """Return standard Snowflake authentication headers."""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
    }


def _auth() -> httpx.BasicAuth:
    """Return Basic auth credentials."""
    return httpx.BasicAuth(_get_user(), _get_password())


async def _request(method: str, path: str, **kwargs) -> dict:
    """Make an authenticated request to the Snowflake REST API."""
    url = f"{_base_url()}/{path.lstrip('/')}"
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            url,
            headers=_headers(),
            auth=_auth(),
            timeout=60,
            **kwargs,
        )
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {"status": "ok"}
        return resp.json()


async def _execute_sql(statement: str, database: Optional[str] = None,
                       schema: Optional[str] = None,
                       warehouse: Optional[str] = None,
                       timeout: int = 60) -> dict:
    """Submit a SQL statement via the Snowflake SQL REST API."""
    body: dict = {
        "statement": statement,
        "timeout": timeout,
    }
    if database:
        body["database"] = database
    if schema:
        body["schema"] = schema
    if warehouse:
        body["warehouse"] = warehouse
    return await _request("POST", "api/v2/statements", json=body)


def register(mcp: FastMCP) -> None:
    """Register Snowflake tools with the MCP server."""

    @mcp.tool()
    async def snowflake_execute_query(
        query: str,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        warehouse: Optional[str] = None,
        timeout: int = 60,
    ) -> dict:
        """Execute a SQL query against Snowflake and return the results.

        Args:
            query: The SQL statement to execute.
            database: The database context for the query. Optional.
            schema: The schema context for the query. Optional.
            warehouse: The warehouse to use for execution. Optional.
            timeout: Query timeout in seconds (default 60).

        Returns:
            Query results including columns, data rows, and statement handle.
        """
        return await _execute_sql(query, database=database, schema=schema,
                                  warehouse=warehouse, timeout=timeout)

    @mcp.tool()
    async def snowflake_list_databases() -> dict:
        """List all databases accessible to the current user in Snowflake.

        Returns:
            List of databases with name, owner, and other metadata.
        """
        return await _execute_sql("SHOW DATABASES")

    @mcp.tool()
    async def snowflake_list_schemas(database: str) -> dict:
        """List all schemas in a Snowflake database.

        Args:
            database: The database name to list schemas from.

        Returns:
            List of schemas with name, owner, and other metadata.
        """
        return await _execute_sql(f"SHOW SCHEMAS IN DATABASE \"{database}\"",
                                  database=database)

    @mcp.tool()
    async def snowflake_list_tables(
        database: str,
        schema: str,
    ) -> dict:
        """List all tables in a Snowflake database and schema.

        Args:
            database: The database name.
            schema: The schema name.

        Returns:
            List of tables with name, kind, owner, rows, bytes, and other metadata.
        """
        return await _execute_sql(
            f"SHOW TABLES IN \"{database}\".\"{schema}\"",
            database=database,
            schema=schema,
        )

    @mcp.tool()
    async def snowflake_describe_table(
        database: str,
        schema: str,
        table: str,
    ) -> dict:
        """Describe the columns and structure of a Snowflake table.

        Args:
            database: The database name.
            schema: The schema name.
            table: The table name.

        Returns:
            Column definitions including name, type, nullable, default, primary key, and comment.
        """
        return await _execute_sql(
            f"DESCRIBE TABLE \"{database}\".\"{schema}\".\"{table}\"",
            database=database,
            schema=schema,
        )

    @mcp.tool()
    async def snowflake_get_query_status(statement_handle: str) -> dict:
        """Check the status of an asynchronous Snowflake query.

        Args:
            statement_handle: The statement handle returned from a previous query submission.

        Returns:
            Query status including state (e.g. RUNNING, SUCCEEDED, FAILED) and result data if complete.
        """
        return await _request("GET", f"api/v2/statements/{statement_handle}")

    @mcp.tool()
    async def snowflake_list_warehouses() -> dict:
        """List all warehouses accessible to the current user in Snowflake.

        Returns:
            List of warehouses with name, state, size, type, and other configuration details.
        """
        return await _execute_sql("SHOW WAREHOUSES")

    @mcp.tool()
    async def snowflake_get_query_history(
        limit: int = 50,
        warehouse: Optional[str] = None,
    ) -> dict:
        """Get recent query history from Snowflake.

        Args:
            limit: Maximum number of queries to return (default 50).
            warehouse: Filter by warehouse name. Optional.

        Returns:
            Recent queries with query ID, SQL text, status, duration, warehouse, and user.
        """
        where = f" WHERE WAREHOUSE_NAME = '{warehouse}'" if warehouse else ""
        sql = (
            f"SELECT QUERY_ID, QUERY_TEXT, DATABASE_NAME, SCHEMA_NAME, "
            f"WAREHOUSE_NAME, USER_NAME, EXECUTION_STATUS, "
            f"START_TIME, END_TIME, TOTAL_ELAPSED_TIME "
            f"FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY()) "
            f"{where}"
            f"ORDER BY START_TIME DESC LIMIT {limit}"
        )
        return await _execute_sql(sql)
