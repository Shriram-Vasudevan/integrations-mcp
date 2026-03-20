"""Salesforce provider wrapping the Salesforce REST API."""

import os
from typing import Optional

import requests
from mcp.server.fastmcp import FastMCP

# Cached auth session: (instance_url, access_token)
_auth_cache: dict = {}


def _authenticate() -> tuple[str, str]:
    """Authenticate via OAuth2 username-password flow and return (instance_url, access_token)."""
    if _auth_cache.get("access_token"):
        return _auth_cache["instance_url"], _auth_cache["access_token"]

    client_id = os.environ.get("SALESFORCE_CLIENT_ID", "")
    client_secret = os.environ.get("SALESFORCE_CLIENT_SECRET", "")
    username = os.environ.get("SALESFORCE_USERNAME", "")
    password = os.environ.get("SALESFORCE_PASSWORD", "")
    security_token = os.environ.get("SALESFORCE_SECURITY_TOKEN", "")

    if not all([client_id, client_secret, username, password]):
        raise RuntimeError(
            "Salesforce credentials required: SALESFORCE_CLIENT_ID, "
            "SALESFORCE_CLIENT_SECRET, SALESFORCE_USERNAME, SALESFORCE_PASSWORD. "
            "Optionally set SALESFORCE_SECURITY_TOKEN."
        )

    # Salesforce OAuth2 password flow requires token appended to password
    password_with_token = password + security_token

    login_url = os.environ.get(
        "SALESFORCE_LOGIN_URL", "https://login.salesforce.com"
    )
    resp = requests.post(
        f"{login_url}/services/oauth2/token",
        data={
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password_with_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    _auth_cache["instance_url"] = data["instance_url"]
    _auth_cache["access_token"] = data["access_token"]
    return data["instance_url"], data["access_token"]


API_VERSION = "v60.0"


def _request(method: str, path: str, **kwargs) -> dict:
    """Make an authenticated request to the Salesforce REST API."""
    instance_url, token = _authenticate()
    url = f"{instance_url}/services/data/{API_VERSION}/{path.lstrip('/')}"
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
    # If unauthorized, clear cache and retry once
    if resp.status_code == 401:
        _auth_cache.clear()
        instance_url, token = _authenticate()
        url = f"{instance_url}/services/data/{API_VERSION}/{path.lstrip('/')}"
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
    """Register Salesforce tools with the MCP server."""

    @mcp.tool()
    def salesforce_query(query: str) -> dict:
        """Execute a SOQL query against Salesforce.

        Args:
            query: A valid SOQL query string (e.g. "SELECT Id, Name FROM Account LIMIT 10").

        Returns:
            Query results with total size and list of records.
        """
        data = _request("GET", "query", params={"q": query})
        records = []
        for r in data.get("records", []):
            record = {k: v for k, v in r.items() if k != "attributes"}
            records.append(record)
        return {
            "total_size": data.get("totalSize", 0),
            "done": data.get("done", True),
            "records": records,
        }

    @mcp.tool()
    def salesforce_get_record(
        object_type: str,
        record_id: str,
        fields: Optional[str] = None,
    ) -> dict:
        """Fetch a single Salesforce record by ID and object type.

        Args:
            object_type: The API name of the SObject (e.g. "Account", "Contact").
            record_id: The 15 or 18-character Salesforce record ID.
            fields: Comma-separated list of fields to retrieve (optional, returns all if omitted).

        Returns:
            Record data as key-value pairs.
        """
        path = f"sobjects/{object_type}/{record_id}"
        params = {}
        if fields:
            params["fields"] = fields
        data = _request("GET", path, params=params if params else None)
        return {k: v for k, v in data.items() if k != "attributes"}

    @mcp.tool()
    def salesforce_create_record(
        object_type: str,
        fields: dict,
    ) -> dict:
        """Create a new record in Salesforce.

        Args:
            object_type: The API name of the SObject (e.g. "Account", "Contact", "Lead").
            fields: Dictionary of field names to values (e.g. {"Name": "Acme Corp", "Industry": "Technology"}).

        Returns:
            The created record's ID and success status.
        """
        data = _request("POST", f"sobjects/{object_type}", json=fields)
        return {
            "id": data.get("id"),
            "success": data.get("success", True),
        }

    @mcp.tool()
    def salesforce_update_record(
        object_type: str,
        record_id: str,
        fields: dict,
    ) -> dict:
        """Update an existing Salesforce record.

        Args:
            object_type: The API name of the SObject (e.g. "Account", "Contact").
            record_id: The 15 or 18-character Salesforce record ID.
            fields: Dictionary of field names to updated values (e.g. {"Phone": "555-1234"}).

        Returns:
            Status confirmation.
        """
        if not fields:
            return {"status": "no_changes", "record_id": record_id}
        _request("PATCH", f"sobjects/{object_type}/{record_id}", json=fields)
        return {"status": "ok", "record_id": record_id}

    @mcp.tool()
    def salesforce_delete_record(
        object_type: str,
        record_id: str,
    ) -> dict:
        """Delete a Salesforce record.

        Args:
            object_type: The API name of the SObject (e.g. "Account", "Contact").
            record_id: The 15 or 18-character Salesforce record ID.

        Returns:
            Status confirmation.
        """
        _request("DELETE", f"sobjects/{object_type}/{record_id}")
        return {"status": "ok", "record_id": record_id}

    @mcp.tool()
    def salesforce_list_objects() -> dict:
        """List all available SObjects in the Salesforce org.

        Returns:
            List of SObject names, labels, and key properties (queryable, createable, etc.).
        """
        data = _request("GET", "sobjects")
        objects = []
        for obj in data.get("sobjects", []):
            objects.append({
                "name": obj.get("name"),
                "label": obj.get("label"),
                "queryable": obj.get("queryable", False),
                "createable": obj.get("createable", False),
                "updateable": obj.get("updateable", False),
                "deletable": obj.get("deletable", False),
                "custom": obj.get("custom", False),
            })
        return {"objects": objects, "total": len(objects)}

    @mcp.tool()
    def salesforce_describe_object(object_type: str) -> dict:
        """Describe the metadata and fields for a Salesforce SObject.

        Args:
            object_type: The API name of the SObject (e.g. "Account", "Contact", "Lead").

        Returns:
            Object metadata including label, fields with name/type/attributes, and record type info.
        """
        data = _request("GET", f"sobjects/{object_type}/describe")
        fields = []
        for f in data.get("fields", []):
            fields.append({
                "name": f.get("name"),
                "label": f.get("label"),
                "type": f.get("type"),
                "length": f.get("length"),
                "nillable": f.get("nillable", False),
                "createable": f.get("createable", False),
                "updateable": f.get("updateable", False),
                "unique": f.get("unique", False),
                "external_id": f.get("externalId", False),
            })
        record_types = []
        for rt in data.get("recordTypeInfos", []):
            record_types.append({
                "name": rt.get("name"),
                "record_type_id": rt.get("recordTypeId"),
                "available": rt.get("available", False),
                "default": rt.get("defaultRecordTypeMapping", False),
            })
        return {
            "object_type": object_type,
            "label": data.get("label", ""),
            "label_plural": data.get("labelPlural", ""),
            "queryable": data.get("queryable", False),
            "createable": data.get("createable", False),
            "updateable": data.get("updateable", False),
            "deletable": data.get("deletable", False),
            "fields": fields,
            "record_types": record_types,
            "total_fields": len(fields),
        }

    @mcp.tool()
    def salesforce_search(search: str) -> dict:
        """Execute a SOSL search across Salesforce objects.

        Args:
            search: A valid SOSL search string (e.g. "FIND {Acme} IN ALL FIELDS RETURNING Account(Id, Name), Contact(Id, Name)").

        Returns:
            Search results grouped by SObject type.
        """
        data = _request("GET", "search", params={"q": search})
        results = []
        for r in data.get("searchRecords", []):
            record = {k: v for k, v in r.items() if k != "attributes"}
            record["_sobject_type"] = r.get("attributes", {}).get("type", "")
            results.append(record)
        return {"results": results, "total": len(results)}
