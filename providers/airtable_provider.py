"""Airtable provider using the pyairtable SDK.

Exposes MCP tools for managing Airtable bases, tables, and records.
Requires AIRTABLE_API_KEY environment variable.
"""

import asyncio
import os
from functools import partial
from typing import Optional

from mcp.server.fastmcp import FastMCP


def _get_api():
    """Return an authenticated pyairtable Api client."""
    from pyairtable import Api
    key = os.environ.get("AIRTABLE_API_KEY", "")
    if not key:
        raise RuntimeError("AIRTABLE_API_KEY environment variable is required")
    return Api(key)


async def _run_sync(func, *args, **kwargs):
    """Run a synchronous pyairtable call in a thread executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


def register(mcp: FastMCP) -> None:
    """Register Airtable tools with the MCP server."""

    @mcp.tool()
    async def airtable_list_bases() -> dict:
        """List all Airtable bases accessible to the authenticated user.

        Returns:
            List of bases with id, name, and permission level.
        """
        api = _get_api()
        bases = await _run_sync(api.bases)
        return {
            "bases": [
                {
                    "id": b.id,
                    "name": b.name,
                    "permission_level": b.permission_level,
                }
                for b in bases
            ]
        }

    @mcp.tool()
    async def airtable_list_tables(base_id: str) -> dict:
        """List all tables in an Airtable base with their field schemas.

        Args:
            base_id: The base ID (e.g. "appXXXXXXXXXXXXXX").

        Returns:
            List of tables with id, name, description, and fields.
        """
        api = _get_api()
        base = api.base(base_id)
        schema = await _run_sync(base.schema)
        tables = []
        for t in schema.tables:
            fields = []
            for f in t.fields:
                field_info: dict = {
                    "id": f.id,
                    "name": f.name,
                    "type": f.type,
                }
                if f.description:
                    field_info["description"] = f.description
                fields.append(field_info)
            tables.append({
                "id": t.id,
                "name": t.name,
                "description": t.description or "",
                "primary_field_id": t.primary_field_id,
                "fields": fields,
            })
        return {"tables": tables}

    @mcp.tool()
    async def airtable_list_records(
        base_id: str,
        table_name: str,
        max_records: int = 100,
        view: str = "",
        fields: Optional[list[str]] = None,
        formula: str = "",
        sort: Optional[list[str]] = None,
    ) -> dict:
        """List records in an Airtable table with optional filtering and sorting.

        Args:
            base_id: The base ID (e.g. "appXXXXXXXXXXXXXX").
            table_name: Table name or ID.
            max_records: Maximum number of records to return (default 100).
            view: Name or ID of a view to filter by (optional).
            fields: List of field names to include in the response (optional).
            formula: Airtable formula to filter records (e.g. "{Status} = 'Active'") (optional).
            sort: List of field names to sort by. Prefix with "-" for descending (e.g. ["-Created"]) (optional).

        Returns:
            List of records with id, fields, and created_time.
        """
        api = _get_api()
        table = api.table(base_id, table_name)

        kwargs: dict = {"max_records": max_records}
        if view:
            kwargs["view"] = view
        if fields:
            kwargs["fields"] = fields
        if formula:
            kwargs["formula"] = formula
        if sort:
            kwargs["sort"] = sort

        records = await _run_sync(table.all, **kwargs)
        return {
            "records": [
                {
                    "id": r["id"],
                    "fields": r["fields"],
                    "created_time": r["createdTime"],
                }
                for r in records
            ]
        }

    @mcp.tool()
    async def airtable_get_record(
        base_id: str,
        table_name: str,
        record_id: str,
    ) -> dict:
        """Get a single record by ID from an Airtable table.

        Args:
            base_id: The base ID (e.g. "appXXXXXXXXXXXXXX").
            table_name: Table name or ID.
            record_id: The record ID (e.g. "recXXXXXXXXXXXXXX").

        Returns:
            Record with id, fields, and created_time.
        """
        api = _get_api()
        table = api.table(base_id, table_name)
        r = await _run_sync(table.get, record_id)
        return {
            "id": r["id"],
            "fields": r["fields"],
            "created_time": r["createdTime"],
        }

    @mcp.tool()
    async def airtable_create_record(
        base_id: str,
        table_name: str,
        fields: dict,
        typecast: bool = False,
    ) -> dict:
        """Create a new record in an Airtable table.

        Args:
            base_id: The base ID (e.g. "appXXXXXXXXXXXXXX").
            table_name: Table name or ID.
            fields: Dictionary mapping field names to values.
            typecast: If true, Airtable will try to convert string values to the appropriate cell type (default false).

        Returns:
            Created record with id, fields, and created_time.
        """
        api = _get_api()
        table = api.table(base_id, table_name)
        r = await _run_sync(table.create, fields, typecast=typecast)
        return {
            "id": r["id"],
            "fields": r["fields"],
            "created_time": r["createdTime"],
        }

    @mcp.tool()
    async def airtable_update_record(
        base_id: str,
        table_name: str,
        record_id: str,
        fields: dict,
        typecast: bool = False,
    ) -> dict:
        """Update an existing record in an Airtable table (partial update, merges fields).

        Args:
            base_id: The base ID (e.g. "appXXXXXXXXXXXXXX").
            table_name: Table name or ID.
            record_id: The record ID (e.g. "recXXXXXXXXXXXXXX").
            fields: Dictionary of field names to new values (only specified fields are updated).
            typecast: If true, Airtable will try to convert string values to the appropriate cell type (default false).

        Returns:
            Updated record with id, fields, and created_time.
        """
        api = _get_api()
        table = api.table(base_id, table_name)
        r = await _run_sync(table.update, record_id, fields, typecast=typecast)
        return {
            "id": r["id"],
            "fields": r["fields"],
            "created_time": r["createdTime"],
        }

    @mcp.tool()
    async def airtable_delete_record(
        base_id: str,
        table_name: str,
        record_id: str,
    ) -> dict:
        """Delete a record from an Airtable table.

        Args:
            base_id: The base ID (e.g. "appXXXXXXXXXXXXXX").
            table_name: Table name or ID.
            record_id: The record ID (e.g. "recXXXXXXXXXXXXXX").

        Returns:
            Confirmation with the deleted record ID.
        """
        api = _get_api()
        table = api.table(base_id, table_name)
        result = await _run_sync(table.delete, record_id)
        return {
            "id": result.get("id", record_id),
            "deleted": result.get("deleted", True),
        }
