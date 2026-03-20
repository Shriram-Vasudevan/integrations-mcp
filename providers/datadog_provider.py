"""Datadog provider using the official datadog-api-client SDK.

Requires DD_API_KEY and DD_APP_KEY environment variables.
"""

import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# SDK configuration helper
# ---------------------------------------------------------------------------


def _get_configuration():
    """Build a datadog_api_client Configuration from environment variables."""
    from datadog_api_client import Configuration

    api_key = os.environ.get("DD_API_KEY")
    app_key = os.environ.get("DD_APP_KEY")
    if not api_key:
        raise RuntimeError("DD_API_KEY environment variable is not set")
    if not app_key:
        raise RuntimeError("DD_APP_KEY environment variable is not set")

    configuration = Configuration()
    configuration.api_key["apiKeyAuth"] = api_key
    configuration.api_key["appKeyAuth"] = app_key
    # Allow overriding the site (e.g. datadoghq.eu)
    site = os.environ.get("DD_SITE")
    if site:
        configuration.server_variables["site"] = site
    return configuration


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def register(mcp: FastMCP) -> None:
    """Register Datadog tools with the MCP server."""

    # ── Monitors ──────────────────────────────────────────────────────

    @mcp.tool()
    async def datadog_list_monitors(
        query: Optional[str] = None,
        page: int = 0,
        page_size: int = 50,
    ) -> dict:
        """List Datadog monitors with optional query filter.

        Args:
            query: Monitor query filter string (e.g. "type:metric status:alert"). Optional.
            page: Page number for pagination (default 0).
            page_size: Number of monitors per page (default 50).

        Returns:
            List of monitors with id, name, type, status, query, and tags.
        """
        from datadog_api_client import ApiClient
        from datadog_api_client.v1.api.monitors_api import MonitorsApi

        with ApiClient(_get_configuration()) as api_client:
            api = MonitorsApi(api_client)
            kwargs = {"page": page, "page_size": page_size}
            if query:
                kwargs["query"] = query
            monitors = api.list_monitors(**kwargs)
            return {
                "monitors": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "type": str(m.type.value) if hasattr(m.type, "value") else str(m.type),
                        "query": m.query,
                        "status": str(m.overall_state.value) if hasattr(m.overall_state, "value") else str(m.overall_state),
                        "tags": list(m.tags) if m.tags else [],
                        "message": m.message,
                    }
                    for m in monitors
                ]
            }

    @mcp.tool()
    async def datadog_get_monitor(
        monitor_id: int,
        group_states: Optional[str] = None,
    ) -> dict:
        """Get details of a specific Datadog monitor by ID.

        Args:
            monitor_id: The ID of the monitor to retrieve.
            group_states: Comma-separated group states to include (e.g. "alert,warn,no data"). Optional.

        Returns:
            Full monitor definition including query, thresholds, status, and message.
        """
        from datadog_api_client import ApiClient
        from datadog_api_client.v1.api.monitors_api import MonitorsApi

        with ApiClient(_get_configuration()) as api_client:
            api = MonitorsApi(api_client)
            kwargs = {"monitor_id": monitor_id}
            if group_states:
                kwargs["group_states"] = group_states
            m = api.get_monitor(**kwargs)
            return {
                "id": m.id,
                "name": m.name,
                "type": str(m.type.value) if hasattr(m.type, "value") else str(m.type),
                "query": m.query,
                "status": str(m.overall_state.value) if hasattr(m.overall_state, "value") else str(m.overall_state),
                "message": m.message,
                "tags": list(m.tags) if m.tags else [],
                "options": m.options.to_dict() if hasattr(m, "options") and m.options else {},
                "created": str(m.created) if m.created else None,
                "modified": str(m.modified) if m.modified else None,
            }

    # ── Metrics ───────────────────────────────────────────────────────

    @mcp.tool()
    async def datadog_query_metrics(
        query: str,
        from_ts: int,
        to_ts: int,
    ) -> dict:
        """Query Datadog metric timeseries data.

        Args:
            query: Metrics query string (e.g. "avg:system.cpu.user{host:myhost}").
            from_ts: Start time as a UNIX epoch timestamp (seconds).
            to_ts: End time as a UNIX epoch timestamp (seconds).

        Returns:
            Timeseries data with pointlists, scope, and metric metadata.
        """
        from datadog_api_client import ApiClient
        from datadog_api_client.v1.api.metrics_api import MetricsApi

        with ApiClient(_get_configuration()) as api_client:
            api = MetricsApi(api_client)
            result = api.query_metrics(
                _from=from_ts,
                to=to_ts,
                query=query,
            )
            series_list = []
            if result.series:
                for s in result.series:
                    series_list.append({
                        "metric": s.metric,
                        "scope": s.scope,
                        "pointlist": [[p[0], p[1]] for p in s.pointlist] if s.pointlist else [],
                        "display_name": s.display_name,
                        "unit": s.unit[0].to_dict() if s.unit else None,
                    })
            return {
                "status": result.status,
                "query": result.query,
                "from_date": result._from_date,
                "to_date": result.to_date,
                "series": series_list,
            }

    # ── Dashboards ────────────────────────────────────────────────────

    @mcp.tool()
    async def datadog_list_dashboards(
        filter_shared: Optional[bool] = None,
        filter_deleted: bool = False,
        count: int = 50,
        start: int = 0,
    ) -> dict:
        """List Datadog dashboards.

        Args:
            filter_shared: If true, return only shared dashboards. Optional.
            filter_deleted: If true, include deleted dashboards (default false).
            count: Number of dashboards to return (default 50).
            start: Offset for pagination (default 0).

        Returns:
            List of dashboards with id, title, url, and layout type.
        """
        from datadog_api_client import ApiClient
        from datadog_api_client.v1.api.dashboards_api import DashboardsApi

        with ApiClient(_get_configuration()) as api_client:
            api = DashboardsApi(api_client)
            kwargs = {"count": count, "start": start}
            if filter_shared is not None:
                kwargs["filter_shared"] = filter_shared
            if filter_deleted:
                kwargs["filter_deleted"] = filter_deleted
            result = api.list_dashboards(**kwargs)
            dashboards = []
            if result.dashboards:
                for d in result.dashboards:
                    dashboards.append({
                        "id": d.id,
                        "title": d.title,
                        "description": d.description if hasattr(d, "description") else None,
                        "layout_type": str(d.layout_type.value) if hasattr(d.layout_type, "value") else str(d.layout_type) if d.layout_type else None,
                        "url": d.url if hasattr(d, "url") else None,
                        "created_at": str(d.created_at) if hasattr(d, "created_at") and d.created_at else None,
                        "modified_at": str(d.modified_at) if hasattr(d, "modified_at") and d.modified_at else None,
                        "author_handle": d.author_handle if hasattr(d, "author_handle") else None,
                    })
            return {"dashboards": dashboards, "total": len(dashboards)}

    # ── Events ────────────────────────────────────────────────────────

    @mcp.tool()
    async def datadog_get_events(
        start: int,
        end: int,
        priority: Optional[str] = None,
        sources: Optional[str] = None,
        tags: Optional[str] = None,
        unaggregated: bool = False,
        page: int = 0,
    ) -> dict:
        """Get Datadog events within a time range.

        Args:
            start: Start time as a UNIX epoch timestamp (seconds).
            end: End time as a UNIX epoch timestamp (seconds).
            priority: Filter by priority: "normal" or "low". Optional.
            sources: Comma-separated list of event sources. Optional.
            tags: Comma-separated list of tags to filter by. Optional.
            unaggregated: If true, return unaggregated events (default false).
            page: Page number for pagination (default 0).

        Returns:
            List of events with title, text, source, tags, and timestamps.
        """
        from datadog_api_client import ApiClient
        from datadog_api_client.v1.api.events_api import EventsApi

        with ApiClient(_get_configuration()) as api_client:
            api = EventsApi(api_client)
            kwargs = {"start": start, "end": end, "page": page}
            if priority:
                kwargs["priority"] = priority
            if sources:
                kwargs["sources"] = sources
            if tags:
                kwargs["tags"] = tags
            if unaggregated:
                kwargs["unaggregated"] = unaggregated
            result = api.list_events(**kwargs)
            events = []
            if result.events:
                for e in result.events:
                    events.append({
                        "id": e.id,
                        "title": e.title,
                        "text": e.text,
                        "source": e.source if hasattr(e, "source") else None,
                        "priority": str(e.priority.value) if hasattr(e.priority, "value") else str(e.priority) if e.priority else None,
                        "tags": list(e.tags) if e.tags else [],
                        "date_happened": e.date_happened,
                        "host": e.host if hasattr(e, "host") else None,
                        "alert_type": str(e.alert_type.value) if hasattr(e.alert_type, "value") else str(e.alert_type) if e.alert_type else None,
                    })
            return {"events": events}

    # ── Hosts ─────────────────────────────────────────────────────────

    @mcp.tool()
    async def datadog_list_hosts(
        filter: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_dir: Optional[str] = None,
        start: int = 0,
        count: int = 100,
    ) -> dict:
        """List hosts reporting to Datadog.

        Args:
            filter: Filter string for host search (e.g. "host:myhost" or "env:prod"). Optional.
            sort_field: Field to sort by (e.g. "apps", "cpu", "name"). Optional.
            sort_dir: Sort direction: "asc" or "desc". Optional.
            start: Offset for pagination (default 0).
            count: Number of hosts to return (default 100, max 1000).

        Returns:
            List of hosts with name, id, apps, sources, meta, and metrics.
        """
        from datadog_api_client import ApiClient
        from datadog_api_client.v1.api.hosts_api import HostsApi

        with ApiClient(_get_configuration()) as api_client:
            api = HostsApi(api_client)
            kwargs = {"start": start, "count": min(count, 1000)}
            if filter:
                kwargs["filter"] = filter
            if sort_field:
                kwargs["sort_field"] = sort_field
            if sort_dir:
                kwargs["sort_dir"] = sort_dir
            result = api.list_hosts(**kwargs)
            hosts = []
            if result.host_list:
                for h in result.host_list:
                    hosts.append({
                        "name": h.name,
                        "id": h.id,
                        "aliases": list(h.aliases) if h.aliases else [],
                        "apps": list(h.apps) if h.apps else [],
                        "sources": list(h.sources) if h.sources else [],
                        "up": h.up,
                        "last_reported_time": h.last_reported_time,
                        "meta": h.meta.to_dict() if hasattr(h, "meta") and h.meta else {},
                        "metrics": h.metrics.to_dict() if hasattr(h, "metrics") and h.metrics else {},
                    })
            return {
                "hosts": hosts,
                "total_matching": result.total_matching,
                "total_returned": result.total_returned,
            }
