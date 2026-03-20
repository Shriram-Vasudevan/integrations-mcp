"""Mixpanel provider wrapping the Mixpanel Data Export and Ingestion APIs."""

import json
import os
import time
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

INGESTION_API_BASE = "https://api.mixpanel.com"
DATA_EXPORT_API_BASE = "https://data.mixpanel.com/api/2.0"
QUERY_API_BASE = "https://mixpanel.com/api/2.0"


def _get_credentials() -> tuple[str, str]:
    """Return Mixpanel service account username and secret from environment."""
    username = os.environ.get("MIXPANEL_SERVICE_ACCOUNT_USERNAME")
    secret = os.environ.get("MIXPANEL_SERVICE_ACCOUNT_SECRET")
    if not username or not secret:
        raise RuntimeError(
            "MIXPANEL_SERVICE_ACCOUNT_USERNAME and MIXPANEL_SERVICE_ACCOUNT_SECRET "
            "environment variables must be set"
        )
    return username, secret


def _get_project_token() -> str:
    """Return the Mixpanel project token from environment."""
    token = os.environ.get("MIXPANEL_PROJECT_TOKEN")
    if not token:
        raise RuntimeError("MIXPANEL_PROJECT_TOKEN environment variable is not set")
    return token


async def _query_request(method: str, path: str, **kwargs) -> dict | list:
    """Make an authenticated request to the Mixpanel query/export APIs."""
    base = DATA_EXPORT_API_BASE if path.startswith("export") else QUERY_API_BASE
    url = f"{base}/{path.lstrip('/')}"
    username, secret = _get_credentials()
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            url,
            auth=(username, secret),
            timeout=60,
            **kwargs,
        )
        resp.raise_for_status()
        return resp.json()


async def _ingestion_request(endpoint: str, payload: list | dict) -> dict:
    """Send data to the Mixpanel Ingestion API."""
    url = f"{INGESTION_API_BASE}/{endpoint.lstrip('/')}"
    data = payload if isinstance(payload, list) else [payload]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers={"Content-Type": "application/json", "Accept": "text/plain"},
            content=json.dumps(data),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register Mixpanel tools with the MCP server."""

    @mcp.tool()
    async def mixpanel_query_events(
        from_date: str,
        to_date: str,
        event: Optional[list[str]] = None,
        limit: int = 1000,
    ) -> dict:
        """Query raw events from Mixpanel for a date range with optional event name filter.

        Uses the Data Export API to retrieve raw event data.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.
            event: List of event names to filter by (optional, e.g. ["Signed Up", "Page View"]).
            limit: Maximum number of events to return (default 1000).

        Returns:
            List of raw event objects with event name and properties, plus total count.
        """
        params: dict = {"from_date": from_date, "to_date": to_date}
        if event:
            params["event"] = json.dumps(event)

        username, secret = _get_credentials()
        url = f"{DATA_EXPORT_API_BASE}/export"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                auth=(username, secret),
                params=params,
                timeout=60,
            )
            resp.raise_for_status()

        events = []
        for line in resp.text.strip().split("\n"):
            if line:
                events.append(json.loads(line))
                if len(events) >= limit:
                    break
        return {"events": events, "count": len(events)}

    @mcp.tool()
    async def mixpanel_get_event_properties(
        event: str,
        name: str,
        from_date: str,
        to_date: str,
        type: str = "general",
        unit: str = "day",
        limit: int = 255,
        values_limit: int = 255,
    ) -> dict:
        """Get property values and their frequency for a specific event property.

        Uses the Mixpanel Events Properties API to retrieve the breakdown of
        values for a given property on a given event.

        Args:
            event: The event name (e.g. "Signed Up").
            name: The property name to analyze (e.g. "plan" or "$browser").
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.
            type: Count type: general (total) or unique (unique users) (default "general").
            unit: Time unit: minute, hour, day, week, month (default "day").
            limit: Max number of property values to return (default 255).
            values_limit: Max number of values per property (default 255).

        Returns:
            Property value breakdown with counts bucketed by time unit.
        """
        params: dict = {
            "event": event,
            "name": name,
            "from_date": from_date,
            "to_date": to_date,
            "type": type,
            "unit": unit,
            "limit": limit,
            "values_limit": values_limit,
        }
        return await _query_request("GET", "events/properties", params=params)

    @mcp.tool()
    async def mixpanel_get_top_events(
        type: str = "general",
        limit: int = 10,
    ) -> dict:
        """Get the top events in your Mixpanel project by volume.

        Args:
            type: Count type: general (total) or unique (unique users) (default "general").
            limit: Number of top events to return (default 10).

        Returns:
            List of top events with names and counts, ordered by volume.
        """
        params: dict = {"type": type, "limit": limit}
        return await _query_request("GET", "events/top", params=params)

    @mcp.tool()
    async def mixpanel_user_profiles(
        where: Optional[str] = None,
        output_properties: Optional[list[str]] = None,
        page: int = 0,
        page_size: int = 100,
    ) -> dict:
        """Query user profiles from Mixpanel Engage API with optional filters.

        Args:
            where: Filter expression for profiles (optional, e.g. 'properties["$city"] == "San Francisco"').
            output_properties: List of profile property names to include in output (optional).
            page: Page number for pagination (default 0).
            page_size: Number of profiles per page (default 100, max 1000).

        Returns:
            List of user profiles with distinct_id and requested properties.
        """
        params: dict = {
            "page": page,
            "page_size": min(page_size, 1000),
        }
        if where:
            params["where"] = where
        if output_properties:
            params["output_properties"] = json.dumps(output_properties)
        return await _query_request("GET", "engage", params=params)

    @mcp.tool()
    async def mixpanel_get_user_profile(
        distinct_id: str,
    ) -> dict:
        """Get a single user profile by distinct_id from Mixpanel.

        Args:
            distinct_id: The unique user identifier to look up.

        Returns:
            User profile with distinct_id and all stored properties.
        """
        where = f'properties["$distinct_id"] == "{distinct_id}"'
        params: dict = {
            "where": where,
        }
        result = await _query_request("GET", "engage", params=params)
        results = result.get("results", [])
        if not results:
            return {"error": "Profile not found", "distinct_id": distinct_id}
        return results[0]

    @mcp.tool()
    async def mixpanel_track_event(
        event: str,
        distinct_id: str,
        properties: Optional[dict] = None,
    ) -> dict:
        """Track a single event in Mixpanel via the Ingestion API.

        Args:
            event: The event name (e.g. "Signed Up", "Page View").
            distinct_id: Unique identifier for the user.
            properties: Additional event properties (optional).

        Returns:
            Ingestion API response confirming the event was accepted.
        """
        token = _get_project_token()
        event_data = {
            "event": event,
            "properties": {
                "token": token,
                "distinct_id": distinct_id,
                "time": int(time.time()),
                **(properties or {}),
            },
        }
        return await _ingestion_request("track", [event_data])

    @mcp.tool()
    async def mixpanel_get_funnels(
        funnel_id: int,
        from_date: str,
        to_date: str,
        unit: str = "day",
        on: Optional[str] = None,
        where: Optional[str] = None,
        limit: int = 255,
    ) -> dict:
        """Query funnel analysis data from Mixpanel.

        Args:
            funnel_id: The ID of the funnel to query.
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.
            unit: Time unit: day, week, or month (default "day").
            on: Property to segment/breakdown by (optional, e.g. 'properties["$browser"]').
            where: Filter expression (optional, e.g. 'properties["plan"] == "premium"').
            limit: Max number of segmentation values (default 255).

        Returns:
            Funnel step-by-step conversion data with counts and rates.
        """
        params: dict = {
            "funnel_id": funnel_id,
            "from_date": from_date,
            "to_date": to_date,
            "unit": unit,
            "limit": limit,
        }
        if on:
            params["on"] = on
        if where:
            params["where"] = where
        return await _query_request("GET", "funnels", params=params)

    @mcp.tool()
    async def mixpanel_get_retention(
        from_date: str,
        to_date: str,
        retention_type: str = "birth",
        born_event: Optional[str] = None,
        event: Optional[str] = None,
        unit: str = "day",
        interval_count: int = 1,
        on: Optional[str] = None,
        where: Optional[str] = None,
    ) -> dict:
        """Query retention data from Mixpanel.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.
            retention_type: Type of retention: "birth" (first time) or "compounded" (default "birth").
            born_event: The birth event for retention analysis (optional, defaults to all events).
            event: The return event to measure retention against (optional, defaults to all events).
            unit: Time unit: day, week, or month (default "day").
            interval_count: Number of units per interval (default 1).
            on: Property to segment by (optional).
            where: Filter expression (optional).

        Returns:
            Retention data with cohort counts and percentages over time intervals.
        """
        params: dict = {
            "from_date": from_date,
            "to_date": to_date,
            "retention_type": retention_type,
            "unit": unit,
            "interval_count": interval_count,
        }
        if born_event:
            params["born_event"] = born_event
        if event:
            params["event"] = event
        if on:
            params["on"] = on
        if where:
            params["where"] = where
        return await _query_request("GET", "retention", params=params)

    @mcp.tool()
    async def mixpanel_query_segmentation(
        event: str,
        from_date: str,
        to_date: str,
        on: Optional[str] = None,
        unit: str = "day",
        type: str = "general",
        where: Optional[str] = None,
        limit: int = 255,
    ) -> dict:
        """Query Mixpanel Segmentation API for event analytics with optional property breakdown.

        Args:
            event: Event name to analyze.
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.
            on: Property to segment/breakdown by (optional, e.g. 'properties["$browser"]').
            unit: Time unit for grouping: minute, hour, day, week, month (default "day").
            type: Query type: general, unique, or average (default "general").
            where: Filter expression (optional, e.g. 'properties["plan"] == "premium"').
            limit: Max number of segmentation values (default 255).

        Returns:
            Segmentation data with date-bucketed event counts, optionally broken down by property.
        """
        params: dict = {
            "event": event,
            "from_date": from_date,
            "to_date": to_date,
            "unit": unit,
            "type": type,
            "limit": limit,
        }
        if on:
            params["on"] = on
        if where:
            params["where"] = where
        return await _query_request("GET", "segmentation", params=params)

    @mcp.tool()
    async def mixpanel_query_revenue(
        from_date: str,
        to_date: str,
        unit: str = "day",
        type: str = "amount",
    ) -> dict:
        """Query revenue data from Mixpanel.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.
            unit: Time unit: day, week, or month (default "day").
            type: Revenue metric type: amount, count, or paying_users (default "amount").

        Returns:
            Revenue data bucketed by the specified time unit.
        """
        params: dict = {
            "from_date": from_date,
            "to_date": to_date,
            "unit": unit,
            "type": type,
        }
        return await _query_request("GET", "engage/revenue", params=params)
