"""PagerDuty provider using the pdpyras SDK.

Requires PAGERDUTY_API_KEY environment variable (a v2 REST API token).
"""

import asyncio
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP


def _get_session():
    """Create a pdpyras APISession from environment variables."""
    from pdpyras import APISession

    api_key = os.environ.get("PAGERDUTY_API_KEY")
    if not api_key:
        raise RuntimeError("PAGERDUTY_API_KEY environment variable is not set")
    return APISession(api_key)


def register(mcp: FastMCP) -> None:
    """Register PagerDuty tools with the MCP server."""

    @mcp.tool()
    async def pagerduty_list_incidents(
        statuses: str = "triggered,acknowledged",
        limit: int = 25,
        offset: int = 0,
        sort_by: str = "created_at:desc",
        since: str = "",
        until: str = "",
    ) -> dict:
        """List PagerDuty incidents, optionally filtered by status and date range.

        Args:
            statuses: Comma-separated statuses to filter by (triggered, acknowledged, resolved). Default: "triggered,acknowledged".
            limit: Max results per page (default 25, max 100).
            offset: Pagination offset (default 0).
            sort_by: Sort order (default "created_at:desc").
            since: Start of date range in ISO 8601 format (optional).
            until: End of date range in ISO 8601 format (optional).

        Returns:
            List of incidents with id, title, status, urgency, service, and timestamps.
        """

        def _fetch():
            session = _get_session()
            params = {
                "statuses[]": [s.strip() for s in statuses.split(",")],
                "limit": min(limit, 100),
                "offset": offset,
                "sort_by": sort_by,
            }
            if since:
                params["since"] = since
            if until:
                params["until"] = until
            return session.get("incidents", params=params).json()

        data = await asyncio.to_thread(_fetch)
        incidents = []
        for inc in data.get("incidents", []):
            service = inc.get("service", {})
            incidents.append(
                {
                    "id": inc["id"],
                    "incident_number": inc.get("incident_number"),
                    "title": inc.get("title", ""),
                    "status": inc.get("status", ""),
                    "urgency": inc.get("urgency", ""),
                    "service_id": service.get("id", ""),
                    "service_name": service.get("summary", ""),
                    "created_at": inc.get("created_at", ""),
                    "updated_at": inc.get("last_status_change_at", ""),
                    "html_url": inc.get("html_url", ""),
                }
            )
        return {
            "total": data.get("total", len(incidents)),
            "offset": data.get("offset", offset),
            "more": data.get("more", False),
            "incidents": incidents,
        }

    @mcp.tool()
    async def pagerduty_get_incident(incident_id: str) -> dict:
        """Get details of a specific PagerDuty incident.

        Args:
            incident_id: The incident ID (e.g. "P1234ABC").

        Returns:
            Full incident details including title, status, assignments, urgency, and timeline.
        """

        def _fetch():
            session = _get_session()
            return session.get(f"incidents/{incident_id}").json()

        data = await asyncio.to_thread(_fetch)
        inc = data.get("incident", {})
        service = inc.get("service", {})
        escalation_policy = inc.get("escalation_policy", {})
        assignments = [
            {
                "assignee_id": a.get("assignee", {}).get("id", ""),
                "assignee_name": a.get("assignee", {}).get("summary", ""),
                "at": a.get("at", ""),
            }
            for a in inc.get("assignments", [])
        ]
        return {
            "id": inc.get("id", ""),
            "incident_number": inc.get("incident_number"),
            "title": inc.get("title", ""),
            "status": inc.get("status", ""),
            "urgency": inc.get("urgency", ""),
            "description": inc.get("description", ""),
            "service_id": service.get("id", ""),
            "service_name": service.get("summary", ""),
            "escalation_policy_id": escalation_policy.get("id", ""),
            "escalation_policy_name": escalation_policy.get("summary", ""),
            "created_at": inc.get("created_at", ""),
            "updated_at": inc.get("last_status_change_at", ""),
            "resolved_at": inc.get("resolved_at"),
            "assignments": assignments,
            "html_url": inc.get("html_url", ""),
        }

    @mcp.tool()
    async def pagerduty_acknowledge_incident(
        incident_id: str,
        requester_email: str,
    ) -> dict:
        """Acknowledge a triggered PagerDuty incident.

        Args:
            incident_id: The incident ID to acknowledge.
            requester_email: Email of the user performing the action (must match a PagerDuty user).

        Returns:
            Updated incident id, status, and title.
        """

        def _update():
            session = _get_session()
            payload = {
                "incident": {
                    "type": "incident_reference",
                    "status": "acknowledged",
                }
            }
            return session.put(
                f"incidents/{incident_id}",
                json=payload,
                headers={"From": requester_email},
            ).json()

        data = await asyncio.to_thread(_update)
        inc = data.get("incident", {})
        return {
            "id": inc.get("id", ""),
            "status": inc.get("status", ""),
            "title": inc.get("title", ""),
        }

    @mcp.tool()
    async def pagerduty_resolve_incident(
        incident_id: str,
        requester_email: str,
    ) -> dict:
        """Resolve a PagerDuty incident.

        Args:
            incident_id: The incident ID to resolve.
            requester_email: Email of the user performing the action (must match a PagerDuty user).

        Returns:
            Updated incident id, status, and title.
        """

        def _update():
            session = _get_session()
            payload = {
                "incident": {
                    "type": "incident_reference",
                    "status": "resolved",
                }
            }
            return session.put(
                f"incidents/{incident_id}",
                json=payload,
                headers={"From": requester_email},
            ).json()

        data = await asyncio.to_thread(_update)
        inc = data.get("incident", {})
        return {
            "id": inc.get("id", ""),
            "status": inc.get("status", ""),
            "title": inc.get("title", ""),
        }

    @mcp.tool()
    async def pagerduty_list_services(
        limit: int = 25,
        offset: int = 0,
        query: str = "",
    ) -> dict:
        """List PagerDuty services.

        Args:
            limit: Max results per page (default 25, max 100).
            offset: Pagination offset (default 0).
            query: Filter services by name (optional).

        Returns:
            List of services with id, name, status, and escalation policy.
        """

        def _fetch():
            session = _get_session()
            params = {
                "limit": min(limit, 100),
                "offset": offset,
            }
            if query:
                params["query"] = query
            return session.get("services", params=params).json()

        data = await asyncio.to_thread(_fetch)
        services = []
        for svc in data.get("services", []):
            ep = svc.get("escalation_policy", {})
            services.append(
                {
                    "id": svc["id"],
                    "name": svc.get("name", ""),
                    "description": svc.get("description", ""),
                    "status": svc.get("status", ""),
                    "escalation_policy_id": ep.get("id", ""),
                    "escalation_policy_name": ep.get("summary", ""),
                    "html_url": svc.get("html_url", ""),
                }
            )
        return {
            "total": data.get("total", len(services)),
            "offset": data.get("offset", offset),
            "more": data.get("more", False),
            "services": services,
        }

    @mcp.tool()
    async def pagerduty_list_on_calls(
        limit: int = 25,
        offset: int = 0,
        escalation_policy_ids: str = "",
        schedule_ids: str = "",
        since: str = "",
        until: str = "",
    ) -> dict:
        """List current on-call entries across escalation policies.

        Args:
            limit: Max results per page (default 25, max 100).
            offset: Pagination offset (default 0).
            escalation_policy_ids: Comma-separated escalation policy IDs to filter by (optional).
            schedule_ids: Comma-separated schedule IDs to filter by (optional).
            since: Start of on-call window in ISO 8601 (optional).
            until: End of on-call window in ISO 8601 (optional).

        Returns:
            List of on-call entries with user, escalation policy, escalation level, and schedule info.
        """

        def _fetch():
            session = _get_session()
            params = {
                "limit": min(limit, 100),
                "offset": offset,
            }
            if escalation_policy_ids:
                params["escalation_policy_ids[]"] = [
                    eid.strip() for eid in escalation_policy_ids.split(",")
                ]
            if schedule_ids:
                params["schedule_ids[]"] = [
                    sid.strip() for sid in schedule_ids.split(",")
                ]
            if since:
                params["since"] = since
            if until:
                params["until"] = until
            return session.get("oncalls", params=params).json()

        data = await asyncio.to_thread(_fetch)
        oncalls = []
        for oc in data.get("oncalls", []):
            user = oc.get("user", {})
            ep = oc.get("escalation_policy", {})
            schedule = oc.get("schedule", {})
            oncalls.append(
                {
                    "user_id": user.get("id", ""),
                    "user_name": user.get("summary", ""),
                    "escalation_policy_id": ep.get("id", ""),
                    "escalation_policy_name": ep.get("summary", ""),
                    "escalation_level": oc.get("escalation_level"),
                    "schedule_id": schedule.get("id") if schedule else None,
                    "schedule_name": schedule.get("summary") if schedule else None,
                    "start": oc.get("start", ""),
                    "end": oc.get("end", ""),
                }
            )
        return {
            "total": data.get("total", len(oncalls)),
            "offset": data.get("offset", offset),
            "more": data.get("more", False),
            "oncalls": oncalls,
        }

    @mcp.tool()
    async def pagerduty_create_incident(
        title: str,
        service_id: str,
        requester_email: str,
        urgency: str = "high",
        body: str = "",
        escalation_policy_id: str = "",
    ) -> dict:
        """Create (trigger) a new PagerDuty incident.

        Args:
            title: Incident title/summary.
            service_id: The ID of the service the incident is on.
            requester_email: Email of the user creating the incident (must match a PagerDuty user).
            urgency: Incident urgency: "high" or "low" (default "high").
            body: Detailed description of the incident (optional).
            escalation_policy_id: Override escalation policy ID (optional, uses service default if omitted).

        Returns:
            Created incident id, status, urgency, and URL.
        """

        def _create():
            session = _get_session()
            incident: dict = {
                "type": "incident",
                "title": title,
                "service": {
                    "id": service_id,
                    "type": "service_reference",
                },
                "urgency": urgency,
            }
            if body:
                incident["body"] = {
                    "type": "incident_body",
                    "details": body,
                }
            if escalation_policy_id:
                incident["escalation_policy"] = {
                    "id": escalation_policy_id,
                    "type": "escalation_policy_reference",
                }
            return session.post(
                "incidents",
                json={"incident": incident},
                headers={"From": requester_email},
            ).json()

        data = await asyncio.to_thread(_create)
        inc = data.get("incident", {})
        return {
            "id": inc.get("id", ""),
            "incident_number": inc.get("incident_number"),
            "title": inc.get("title", ""),
            "status": inc.get("status", ""),
            "urgency": inc.get("urgency", ""),
            "html_url": inc.get("html_url", ""),
        }

    @mcp.tool()
    async def pagerduty_list_schedules(
        limit: int = 25,
        offset: int = 0,
        query: str = "",
    ) -> dict:
        """List PagerDuty on-call schedules.

        Args:
            limit: Max results per page (default 25, max 100).
            offset: Pagination offset (default 0).
            query: Filter schedules by name (optional).

        Returns:
            List of schedules with id, name, time zone, description, and user details.
        """

        def _fetch():
            session = _get_session()
            params = {
                "limit": min(limit, 100),
                "offset": offset,
            }
            if query:
                params["query"] = query
            return session.get("schedules", params=params).json()

        data = await asyncio.to_thread(_fetch)
        schedules = []
        for sched in data.get("schedules", []):
            users = [
                {"id": u.get("id", ""), "name": u.get("summary", "")}
                for u in sched.get("users", [])
            ]
            schedules.append(
                {
                    "id": sched["id"],
                    "name": sched.get("name", ""),
                    "description": sched.get("description", ""),
                    "time_zone": sched.get("time_zone", ""),
                    "users": users,
                    "html_url": sched.get("html_url", ""),
                }
            )
        return {
            "total": data.get("total", len(schedules)),
            "offset": data.get("offset", offset),
            "more": data.get("more", False),
            "schedules": schedules,
        }

    @mcp.tool()
    async def pagerduty_list_teams(
        limit: int = 25,
        offset: int = 0,
        query: str = "",
    ) -> dict:
        """List PagerDuty teams.

        Args:
            limit: Max results per page (default 25, max 100).
            offset: Pagination offset (default 0).
            query: Filter teams by name (optional).

        Returns:
            List of teams with id, name, description, and default role.
        """

        def _fetch():
            session = _get_session()
            params = {
                "limit": min(limit, 100),
                "offset": offset,
            }
            if query:
                params["query"] = query
            return session.get("teams", params=params).json()

        data = await asyncio.to_thread(_fetch)
        teams = []
        for team in data.get("teams", []):
            teams.append(
                {
                    "id": team["id"],
                    "name": team.get("name", ""),
                    "description": team.get("description", ""),
                    "default_role": team.get("default_role", ""),
                    "html_url": team.get("html_url", ""),
                }
            )
        return {
            "total": data.get("total", len(teams)),
            "offset": data.get("offset", offset),
            "more": data.get("more", False),
            "teams": teams,
        }
