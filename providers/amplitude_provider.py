"""Amplitude provider wrapping the Amplitude Analytics API (amplitude.com/api/2)."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

API_BASE = "https://amplitude.com"


def _get_credentials() -> tuple[str, str]:
    """Return Amplitude API key and secret key from environment."""
    api_key = os.environ.get("AMPLITUDE_API_KEY")
    secret_key = os.environ.get("AMPLITUDE_SECRET_KEY")
    if not api_key or not secret_key:
        raise RuntimeError(
            "AMPLITUDE_API_KEY and AMPLITUDE_SECRET_KEY environment variables must be set"
        )
    return api_key, secret_key


async def _request(method: str, path: str, **kwargs) -> dict:
    """Make an authenticated request to the Amplitude API using HTTP Basic auth."""
    url = f"{API_BASE}/{path.lstrip('/')}"
    api_key, secret_key = _get_credentials()
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            url,
            auth=(api_key, secret_key),
            timeout=60,
            **kwargs,
        )
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register Amplitude tools with the MCP server."""

    # ── Dashboard Metrics ────────────────────────────────────────────

    @mcp.tool()
    async def amplitude_get_event_counts(
        event_type: str,
        start: str,
        end: str,
        interval: int = 1,
        group_by: Optional[str] = None,
    ) -> dict:
        """Get event counts from Amplitude for a specific event type over a date range.

        Uses the Amplitude Segmentation API to count occurrences of a given event.

        Args:
            event_type: The event name to count (e.g. "Sign Up", "Purchase").
            start: Start date in YYYYMMDD format (e.g. "20240101").
            end: End date in YYYYMMDD format (e.g. "20240131").
            interval: Time interval: 1 (daily), 7 (weekly), 30 (monthly). Default 1.
            group_by: Property to group results by (optional, e.g. "platform").

        Returns:
            Event count data with series values bucketed by the specified interval.
        """
        e = {"event_type": event_type}
        if group_by:
            e["group_by"] = [{"type": "user", "value": group_by}]
        params: dict = {
            "e": _json_encode(e),
            "start": start,
            "end": end,
            "i": interval,
            "m": "totals",
        }
        return await _request("GET", "api/2/events/segmentation", params=params)

    @mcp.tool()
    async def amplitude_get_active_users(
        start: str,
        end: str,
        interval: int = 1,
    ) -> dict:
        """Get active user counts from Amplitude over a date range.

        Args:
            start: Start date in YYYYMMDD format (e.g. "20240101").
            end: End date in YYYYMMDD format (e.g. "20240131").
            interval: Time interval: 1 (daily), 7 (weekly), 30 (monthly). Default 1.

        Returns:
            Active user counts bucketed by the specified interval, including DAU/WAU/MAU.
        """
        params: dict = {"start": start, "end": end, "i": interval}
        return await _request("GET", "api/2/users", params=params)

    @mcp.tool()
    async def amplitude_get_new_users(
        start: str,
        end: str,
        interval: int = 1,
    ) -> dict:
        """Get new user counts from Amplitude over a date range.

        Args:
            start: Start date in YYYYMMDD format (e.g. "20240101").
            end: End date in YYYYMMDD format (e.g. "20240131").
            interval: Time interval: 1 (daily), 7 (weekly), 30 (monthly). Default 1.

        Returns:
            New user counts bucketed by the specified interval.
        """
        params: dict = {"start": start, "end": end, "i": interval}
        return await _request("GET", "api/2/new", params=params)

    @mcp.tool()
    async def amplitude_get_revenue(
        start: str,
        end: str,
        interval: int = 1,
        metric: str = "revenue",
    ) -> dict:
        """Get revenue metrics from Amplitude over a date range.

        Args:
            start: Start date in YYYYMMDD format (e.g. "20240101").
            end: End date in YYYYMMDD format (e.g. "20240131").
            interval: Time interval: 1 (daily), 7 (weekly), 30 (monthly). Default 1.
            metric: Revenue metric type: "revenue", "arpau" (avg revenue per active user),
                "arpu" (avg revenue per user), or "paying" (paying user count). Default "revenue".

        Returns:
            Revenue data bucketed by the specified interval with totals and per-period values.
        """
        params: dict = {"start": start, "end": end, "i": interval, "m": metric}
        return await _request("GET", "api/2/revenue/day", params=params)

    # ── Segmentation ─────────────────────────────────────────────────

    @mcp.tool()
    async def amplitude_run_segmentation(
        event_type: str,
        start: str,
        end: str,
        metric: str = "uniques",
        interval: int = 1,
        segment_property: Optional[str] = None,
        filters: Optional[list[dict]] = None,
    ) -> dict:
        """Run a segmentation query on Amplitude event data with optional filters and grouping.

        Args:
            event_type: The event name to analyze (e.g. "Complete Purchase").
            start: Start date in YYYYMMDD format (e.g. "20240101").
            end: End date in YYYYMMDD format (e.g. "20240131").
            metric: Metric to compute: "uniques" (unique users), "totals" (event count),
                "avg" (avg per user), "pctdau" (% of DAU). Default "uniques".
            interval: Time interval: 1 (daily), 7 (weekly), 30 (monthly). Default 1.
            segment_property: User property to segment by (optional, e.g. "country").
            filters: List of filter objects (optional). Each filter is a dict with keys:
                "subprop_type" ("user" or "event"), "subprop_key" (property name),
                "subprop_op" (operator like "is", "is not", "contains"),
                "subprop_value" (list of values).

        Returns:
            Segmentation results with series data, optionally broken down by segment.
        """
        e: dict = {"event_type": event_type}
        if filters:
            e["filters"] = filters
        if segment_property:
            e["group_by"] = [{"type": "user", "value": segment_property}]
        params: dict = {
            "e": _json_encode(e),
            "start": start,
            "end": end,
            "m": metric,
            "i": interval,
        }
        return await _request("GET", "api/2/events/segmentation", params=params)

    # ── Cohorts ──────────────────────────────────────────────────────

    @mcp.tool()
    async def amplitude_list_cohorts() -> dict:
        """List all cohorts defined in Amplitude.

        Returns:
            List of cohorts with id, name, description, size, and definition details.
        """
        return await _request("GET", "api/3/cohorts")

    @mcp.tool()
    async def amplitude_get_cohort_users(
        cohort_id: str,
        props: int = 0,
        limit: int = 1000,
    ) -> dict:
        """Get the list of user IDs (and optionally properties) in an Amplitude cohort.

        Args:
            cohort_id: The ID of the cohort to retrieve users from.
            props: Whether to include user properties: 0 (no) or 1 (yes). Default 0.
            limit: Maximum number of users to return (default 1000).

        Returns:
            List of user IDs belonging to the cohort, optionally with their properties.
        """
        params: dict = {"props": props, "limit": limit}
        return await _request("GET", f"api/3/cohorts/{cohort_id}/users", params=params)

    # ── Funnels ──────────────────────────────────────────────────────

    @mcp.tool()
    async def amplitude_get_funnel(
        funnel_id: str,
        start: str,
        end: str,
        interval: int = 1,
        segment_property: Optional[str] = None,
    ) -> dict:
        """Get funnel analysis results from Amplitude for a saved funnel.

        Args:
            funnel_id: The ID of the saved funnel to query.
            start: Start date in YYYYMMDD format (e.g. "20240101").
            end: End date in YYYYMMDD format (e.g. "20240131").
            interval: Time interval: 1 (daily), 7 (weekly), 30 (monthly). Default 1.
            segment_property: User property to segment funnel results by (optional).

        Returns:
            Funnel step-by-step data with conversion counts and rates for each step.
        """
        params: dict = {
            "fs": funnel_id,
            "start": start,
            "end": end,
            "i": interval,
        }
        if segment_property:
            params["s"] = _json_encode(
                [{"prop": "gp:" + segment_property, "op": "is", "values": []}]
            )
        return await _request("GET", "api/2/funnels", params=params)


def _json_encode(obj) -> str:
    """JSON-encode a value for use as a query parameter."""
    import json

    return json.dumps(obj, separators=(",", ":"))
