"""Google Calendar provider wrapping the Google Calendar REST API v3."""

import json
import os

from mcp.server.fastmcp import FastMCP

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_service():
    """Build and return an authorized Google Calendar API service.

    Reads credentials from the GOOGLE_CALENDAR_CREDENTIALS_JSON env var.
    Supports both service-account JSON and OAuth token JSON.
    """
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    raw = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS_JSON", "")
    if not raw:
        raise RuntimeError(
            "GOOGLE_CALENDAR_CREDENTIALS_JSON environment variable is required"
        )
    info = json.loads(raw)

    if info.get("type") == "service_account":
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES
        )
    else:
        creds = Credentials.from_authorized_user_info(info, scopes=SCOPES)

    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def register(mcp: FastMCP) -> None:
    """Register Google Calendar tools with the MCP server."""

    @mcp.tool()
    def gcal_list_calendars(
        max_results: int = 100,
        show_hidden: bool = False,
    ) -> dict:
        """List calendars accessible to the authenticated user.

        Args:
            max_results: Maximum number of calendars to return (default 100).
            show_hidden: Include hidden calendars (default False).

        Returns:
            List of calendars with id, summary, description, and timezone.
        """
        service = _get_service()
        result = (
            service.calendarList()
            .list(maxResults=max_results, showHidden=show_hidden)
            .execute()
        )
        calendars = []
        for cal in result.get("items", []):
            calendars.append(
                {
                    "id": cal["id"],
                    "summary": cal.get("summary", ""),
                    "description": cal.get("description", ""),
                    "time_zone": cal.get("timeZone", ""),
                    "access_role": cal.get("accessRole", ""),
                    "primary": cal.get("primary", False),
                }
            )
        return {"total": len(calendars), "calendars": calendars}

    @mcp.tool()
    def gcal_list_events(
        calendar_id: str = "primary",
        time_min: str = "",
        time_max: str = "",
        max_results: int = 50,
        query: str = "",
        single_events: bool = True,
        order_by: str = "startTime",
    ) -> dict:
        """List events from a Google Calendar.

        Args:
            calendar_id: Calendar ID (default "primary").
            time_min: Lower bound (inclusive) as RFC3339 timestamp, e.g. "2025-01-01T00:00:00Z".
            time_max: Upper bound (exclusive) as RFC3339 timestamp.
            max_results: Maximum number of events to return (default 50).
            query: Free-text search terms to filter events.
            single_events: Expand recurring events into individual instances (default True).
            order_by: Sort order — "startTime" (default, requires single_events=True) or "updated".

        Returns:
            List of events with id, summary, start, end, and attendees.
        """
        service = _get_service()
        kwargs: dict = {
            "calendarId": calendar_id,
            "maxResults": max_results,
            "singleEvents": single_events,
            "orderBy": order_by,
        }
        if time_min:
            kwargs["timeMin"] = time_min
        if time_max:
            kwargs["timeMax"] = time_max
        if query:
            kwargs["q"] = query

        result = service.events().list(**kwargs).execute()
        events = []
        for ev in result.get("items", []):
            events.append(_format_event(ev))
        return {
            "calendar_id": calendar_id,
            "total": len(events),
            "events": events,
        }

    @mcp.tool()
    def gcal_get_event(event_id: str, calendar_id: str = "primary") -> dict:
        """Get details of a specific calendar event.

        Args:
            event_id: The event ID.
            calendar_id: Calendar ID (default "primary").

        Returns:
            Full event details including summary, times, attendees, and description.
        """
        service = _get_service()
        ev = (
            service.events()
            .get(calendarId=calendar_id, eventId=event_id)
            .execute()
        )
        return _format_event(ev, full=True)

    @mcp.tool()
    def gcal_create_event(
        summary: str,
        start: str,
        end: str,
        calendar_id: str = "primary",
        description: str = "",
        location: str = "",
        time_zone: str = "",
        attendees: list[str] | None = None,
        recurrence: list[str] | None = None,
    ) -> dict:
        """Create a new calendar event.

        Args:
            summary: Event title.
            start: Start time as RFC3339 timestamp (e.g. "2025-06-15T09:00:00-07:00") or date for all-day events ("2025-06-15").
            end: End time as RFC3339 timestamp or date for all-day events.
            calendar_id: Calendar ID (default "primary").
            description: Event description (optional).
            location: Event location (optional).
            time_zone: IANA time zone (e.g. "America/Los_Angeles"). Used when start/end lack offset (optional).
            attendees: List of attendee email addresses (optional).
            recurrence: RRULE strings for recurring events, e.g. ["RRULE:FREQ=WEEKLY;COUNT=10"] (optional).

        Returns:
            Created event id, summary, and link.
        """
        service = _get_service()
        body: dict = {"summary": summary}
        body["start"] = _build_time_body(start, time_zone)
        body["end"] = _build_time_body(end, time_zone)
        if description:
            body["description"] = description
        if location:
            body["location"] = location
        if attendees:
            body["attendees"] = [{"email": email} for email in attendees]
        if recurrence:
            body["recurrence"] = recurrence

        ev = (
            service.events()
            .insert(calendarId=calendar_id, body=body)
            .execute()
        )
        return {
            "id": ev["id"],
            "summary": ev.get("summary", ""),
            "html_link": ev.get("htmlLink", ""),
            "status": ev.get("status", ""),
        }

    @mcp.tool()
    def gcal_update_event(
        event_id: str,
        calendar_id: str = "primary",
        summary: str = "",
        start: str = "",
        end: str = "",
        description: str = "",
        location: str = "",
        time_zone: str = "",
        attendees: list[str] | None = None,
    ) -> dict:
        """Update an existing calendar event.

        Only the provided fields are changed; others remain unchanged.

        Args:
            event_id: The event ID.
            calendar_id: Calendar ID (default "primary").
            summary: New title (optional).
            start: New start time as RFC3339 timestamp or date (optional).
            end: New end time as RFC3339 timestamp or date (optional).
            description: New description (optional).
            location: New location (optional).
            time_zone: IANA time zone for start/end (optional).
            attendees: New list of attendee emails — replaces existing (optional).

        Returns:
            Updated event id, summary, and link.
        """
        service = _get_service()
        existing = (
            service.events()
            .get(calendarId=calendar_id, eventId=event_id)
            .execute()
        )
        if summary:
            existing["summary"] = summary
        if start:
            existing["start"] = _build_time_body(start, time_zone)
        if end:
            existing["end"] = _build_time_body(end, time_zone)
        if description:
            existing["description"] = description
        if location:
            existing["location"] = location
        if attendees is not None:
            existing["attendees"] = [{"email": email} for email in attendees]

        ev = (
            service.events()
            .update(calendarId=calendar_id, eventId=event_id, body=existing)
            .execute()
        )
        return {
            "id": ev["id"],
            "summary": ev.get("summary", ""),
            "html_link": ev.get("htmlLink", ""),
            "status": ev.get("status", ""),
        }

    @mcp.tool()
    def gcal_delete_event(event_id: str, calendar_id: str = "primary") -> dict:
        """Delete a calendar event.

        Args:
            event_id: The event ID.
            calendar_id: Calendar ID (default "primary").

        Returns:
            Confirmation of the deletion.
        """
        service = _get_service()
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return {"status": "deleted", "event_id": event_id, "calendar_id": calendar_id}

    @mcp.tool()
    def gcal_list_freebusy(
        time_min: str,
        time_max: str,
        calendar_ids: list[str] | None = None,
        time_zone: str = "UTC",
    ) -> dict:
        """Query free/busy information for one or more calendars.

        Args:
            time_min: Start of the interval as RFC3339 timestamp (e.g. "2025-06-15T00:00:00Z").
            time_max: End of the interval as RFC3339 timestamp.
            calendar_ids: List of calendar IDs to query (default: ["primary"]).
            time_zone: IANA time zone for the response (default "UTC").

        Returns:
            Busy intervals for each requested calendar.
        """
        service = _get_service()
        ids = calendar_ids or ["primary"]
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "timeZone": time_zone,
            "items": [{"id": cid} for cid in ids],
        }
        result = service.freebusy().query(body=body).execute()
        calendars_busy: dict = {}
        for cid, info in result.get("calendars", {}).items():
            errors = info.get("errors", [])
            busy = [
                {"start": b["start"], "end": b["end"]}
                for b in info.get("busy", [])
            ]
            calendars_busy[cid] = {"busy": busy}
            if errors:
                calendars_busy[cid]["errors"] = [
                    e.get("reason", "") for e in errors
                ]
        return {
            "time_min": time_min,
            "time_max": time_max,
            "calendars": calendars_busy,
        }


def _build_time_body(time_str: str, time_zone: str) -> dict:
    """Build a start/end body dict for the Calendar API.

    Detects date-only vs datetime strings.
    """
    if len(time_str) == 10:
        body: dict = {"date": time_str}
    else:
        body = {"dateTime": time_str}
    if time_zone:
        body["timeZone"] = time_zone
    return body


def _format_event(ev: dict, full: bool = False) -> dict:
    """Format a raw Calendar API event into a clean dict."""
    start = ev.get("start", {})
    end = ev.get("end", {})
    result = {
        "id": ev["id"],
        "summary": ev.get("summary", ""),
        "status": ev.get("status", ""),
        "start": start.get("dateTime") or start.get("date", ""),
        "end": end.get("dateTime") or end.get("date", ""),
        "html_link": ev.get("htmlLink", ""),
    }
    if full:
        result["description"] = ev.get("description", "")
        result["location"] = ev.get("location", "")
        result["creator"] = ev.get("creator", {}).get("email", "")
        result["organizer"] = ev.get("organizer", {}).get("email", "")
        result["attendees"] = [
            {
                "email": a.get("email", ""),
                "response_status": a.get("responseStatus", ""),
                "display_name": a.get("displayName", ""),
            }
            for a in ev.get("attendees", [])
        ]
        result["recurrence"] = ev.get("recurrence", [])
        result["recurring_event_id"] = ev.get("recurringEventId", "")
        result["created"] = ev.get("created", "")
        result["updated"] = ev.get("updated", "")
    return result
