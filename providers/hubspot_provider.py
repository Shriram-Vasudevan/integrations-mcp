"""HubSpot CRM provider wrapping the HubSpot CRM API v3 using httpx."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.hubapi.com/crm/v3"


def _get_token() -> str:
    """Return the HubSpot access token from env."""
    token = os.environ.get("HUBSPOT_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError(
            "HUBSPOT_ACCESS_TOKEN environment variable is required"
        )
    return token


async def _request(method: str, path: str, **kwargs) -> dict:
    """Make an authenticated request to the HubSpot API."""
    token = _get_token()
    url = f"{BASE_URL}/{path.lstrip('/')}"
    async with httpx.AsyncClient() as client:
        resp = await client.request(
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


def _parse_result(item: dict) -> dict:
    """Extract standard fields from a CRM object result."""
    return {
        "id": item["id"],
        "properties": item.get("properties", {}),
        "created_at": item.get("createdAt", ""),
        "updated_at": item.get("updatedAt", ""),
    }


def register(mcp: FastMCP) -> None:
    """Register HubSpot CRM tools with the MCP server."""

    # --- Contacts ---

    @mcp.tool()
    async def hubspot_list_contacts(
        limit: int = 100,
        after: Optional[str] = None,
        properties: str = "firstname,lastname,email,phone,company",
    ) -> dict:
        """List contacts in HubSpot CRM.

        Args:
            limit: Maximum number of contacts to return (default 100, max 100).
            after: Cursor for pagination (optional).
            properties: Comma-separated list of properties to include.

        Returns:
            List of contacts with requested properties and a paging cursor.
        """
        params: dict = {
            "limit": min(limit, 100),
            "properties": properties,
        }
        if after:
            params["after"] = after
        data = await _request("GET", "objects/contacts", params=params)
        contacts = [_parse_result(c) for c in data.get("results", [])]
        next_after = data.get("paging", {}).get("next", {}).get("after", "")
        return {"contacts": contacts, "next_after": next_after}

    @mcp.tool()
    async def hubspot_get_contact(
        contact_id: str,
        properties: str = "firstname,lastname,email,phone,company,lifecyclestage",
    ) -> dict:
        """Get a single HubSpot contact by ID.

        Args:
            contact_id: The HubSpot contact ID.
            properties: Comma-separated list of properties to include.

        Returns:
            Contact details with requested properties.
        """
        data = await _request(
            "GET",
            f"objects/contacts/{contact_id}",
            params={"properties": properties},
        )
        return _parse_result(data)

    @mcp.tool()
    async def hubspot_create_contact(
        email: str,
        firstname: str = "",
        lastname: str = "",
        phone: str = "",
        company: str = "",
        extra_properties: Optional[dict] = None,
    ) -> dict:
        """Create a new contact in HubSpot CRM.

        Args:
            email: Contact email address (required).
            firstname: First name (optional).
            lastname: Last name (optional).
            phone: Phone number (optional).
            company: Company name (optional).
            extra_properties: Additional properties as key-value pairs (optional).

        Returns:
            Created contact ID and properties.
        """
        props: dict = {"email": email}
        if firstname:
            props["firstname"] = firstname
        if lastname:
            props["lastname"] = lastname
        if phone:
            props["phone"] = phone
        if company:
            props["company"] = company
        if extra_properties:
            props.update(extra_properties)

        data = await _request(
            "POST", "objects/contacts", json={"properties": props}
        )
        return {
            "id": data["id"],
            "properties": data.get("properties", {}),
            "created_at": data.get("createdAt", ""),
        }

    @mcp.tool()
    async def hubspot_update_contact(
        contact_id: str,
        properties: dict,
    ) -> dict:
        """Update an existing HubSpot contact.

        Args:
            contact_id: The HubSpot contact ID.
            properties: Dictionary of properties to update (e.g. {"firstname": "Jane", "phone": "555-1234"}).

        Returns:
            Updated contact ID and properties.
        """
        if not properties:
            return {"status": "no_changes", "contact_id": contact_id}

        data = await _request(
            "PATCH",
            f"objects/contacts/{contact_id}",
            json={"properties": properties},
        )
        return {
            "id": data["id"],
            "properties": data.get("properties", {}),
            "updated_at": data.get("updatedAt", ""),
        }

    @mcp.tool()
    async def hubspot_search_contacts(
        query: str = "",
        filter_property: str = "",
        filter_operator: str = "EQ",
        filter_value: str = "",
        limit: int = 100,
        after: Optional[str] = None,
        properties: str = "firstname,lastname,email,phone,company",
    ) -> dict:
        """Search contacts in HubSpot CRM using a query string or property filter.

        Either provide a text query (searches across default searchable properties)
        or a property filter (filter_property + filter_operator + filter_value).

        Args:
            query: Text to search for across default searchable properties (optional).
            filter_property: Property name to filter on, e.g. "email", "firstname" (optional).
            filter_operator: Filter operator: EQ, NEQ, LT, LTE, GT, GTE, CONTAINS_TOKEN, NOT_CONTAINS_TOKEN (default EQ).
            filter_value: Value to filter against (required if filter_property is set).
            limit: Maximum number of results (default 100, max 100).
            after: Cursor for pagination (optional).
            properties: Comma-separated list of properties to return.

        Returns:
            Matching contacts with requested properties and a paging cursor.
        """
        body: dict = {
            "limit": min(limit, 100),
            "properties": [p.strip() for p in properties.split(",")],
        }
        if query:
            body["query"] = query
        if filter_property and filter_value:
            body["filterGroups"] = [
                {
                    "filters": [
                        {
                            "propertyName": filter_property,
                            "operator": filter_operator,
                            "value": filter_value,
                        }
                    ]
                }
            ]
        if after:
            body["after"] = after

        data = await _request(
            "POST", "objects/contacts/search", json=body
        )
        contacts = [_parse_result(c) for c in data.get("results", [])]
        total = data.get("total", len(contacts))
        next_after = data.get("paging", {}).get("next", {}).get("after", "")
        return {"contacts": contacts, "total": total, "next_after": next_after}

    # --- Companies ---

    @mcp.tool()
    async def hubspot_list_companies(
        limit: int = 100,
        after: Optional[str] = None,
        properties: str = "name,domain,industry,city,state,country",
    ) -> dict:
        """List companies in HubSpot CRM.

        Args:
            limit: Maximum number of companies to return (default 100, max 100).
            after: Cursor for pagination (optional).
            properties: Comma-separated list of properties to include.

        Returns:
            List of companies with requested properties and a paging cursor.
        """
        params: dict = {
            "limit": min(limit, 100),
            "properties": properties,
        }
        if after:
            params["after"] = after
        data = await _request("GET", "objects/companies", params=params)
        companies = [_parse_result(c) for c in data.get("results", [])]
        next_after = data.get("paging", {}).get("next", {}).get("after", "")
        return {"companies": companies, "next_after": next_after}

    @mcp.tool()
    async def hubspot_get_company(
        company_id: str,
        properties: str = "name,domain,industry,city,state,country,numberofemployees",
    ) -> dict:
        """Get a single HubSpot company by ID.

        Args:
            company_id: The HubSpot company ID.
            properties: Comma-separated list of properties to include.

        Returns:
            Company details with requested properties.
        """
        data = await _request(
            "GET",
            f"objects/companies/{company_id}",
            params={"properties": properties},
        )
        return _parse_result(data)

    @mcp.tool()
    async def hubspot_create_company(
        name: str,
        domain: str = "",
        industry: str = "",
        city: str = "",
        state: str = "",
        country: str = "",
        extra_properties: Optional[dict] = None,
    ) -> dict:
        """Create a new company in HubSpot CRM.

        Args:
            name: Company name (required).
            domain: Company website domain (optional).
            industry: Industry (optional).
            city: City (optional).
            state: State/region (optional).
            country: Country (optional).
            extra_properties: Additional properties as key-value pairs (optional).

        Returns:
            Created company ID and properties.
        """
        props: dict = {"name": name}
        if domain:
            props["domain"] = domain
        if industry:
            props["industry"] = industry
        if city:
            props["city"] = city
        if state:
            props["state"] = state
        if country:
            props["country"] = country
        if extra_properties:
            props.update(extra_properties)

        data = await _request(
            "POST", "objects/companies", json={"properties": props}
        )
        return {
            "id": data["id"],
            "properties": data.get("properties", {}),
            "created_at": data.get("createdAt", ""),
        }

    # --- Deals ---

    @mcp.tool()
    async def hubspot_list_deals(
        limit: int = 100,
        after: Optional[str] = None,
        properties: str = "dealname,dealstage,amount,closedate,pipeline",
    ) -> dict:
        """List deals in HubSpot CRM.

        Args:
            limit: Maximum number of deals to return (default 100, max 100).
            after: Cursor for pagination (optional).
            properties: Comma-separated list of properties to include.

        Returns:
            List of deals with requested properties and a paging cursor.
        """
        params: dict = {
            "limit": min(limit, 100),
            "properties": properties,
        }
        if after:
            params["after"] = after
        data = await _request("GET", "objects/deals", params=params)
        deals = [_parse_result(d) for d in data.get("results", [])]
        next_after = data.get("paging", {}).get("next", {}).get("after", "")
        return {"deals": deals, "next_after": next_after}

    @mcp.tool()
    async def hubspot_get_deal(
        deal_id: str,
        properties: str = "dealname,dealstage,amount,closedate,pipeline,hubspot_owner_id",
    ) -> dict:
        """Get a single HubSpot deal by ID.

        Args:
            deal_id: The HubSpot deal ID.
            properties: Comma-separated list of properties to include.

        Returns:
            Deal details with requested properties.
        """
        data = await _request(
            "GET",
            f"objects/deals/{deal_id}",
            params={"properties": properties},
        )
        return _parse_result(data)

    @mcp.tool()
    async def hubspot_create_deal(
        dealname: str,
        dealstage: str = "",
        amount: str = "",
        closedate: str = "",
        pipeline: str = "",
        extra_properties: Optional[dict] = None,
    ) -> dict:
        """Create a new deal in HubSpot CRM.

        Args:
            dealname: Deal name (required).
            dealstage: Deal stage ID (optional).
            amount: Deal amount (optional).
            closedate: Expected close date in YYYY-MM-DD format (optional).
            pipeline: Pipeline ID (optional).
            extra_properties: Additional properties as key-value pairs (optional).

        Returns:
            Created deal ID and properties.
        """
        props: dict = {"dealname": dealname}
        if dealstage:
            props["dealstage"] = dealstage
        if amount:
            props["amount"] = amount
        if closedate:
            props["closedate"] = closedate
        if pipeline:
            props["pipeline"] = pipeline
        if extra_properties:
            props.update(extra_properties)

        data = await _request(
            "POST", "objects/deals", json={"properties": props}
        )
        return {
            "id": data["id"],
            "properties": data.get("properties", {}),
            "created_at": data.get("createdAt", ""),
        }
