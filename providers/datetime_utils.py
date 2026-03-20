"""Timezone and datetime utilities provider using Python stdlib (no external API)."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, available_timezones

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register datetime utility tools with the MCP server."""

    @mcp.tool()
    async def get_current_time(timezone: str = "UTC") -> dict:
        """Get the current time in a given timezone.

        Args:
            timezone: IANA timezone string (e.g. "America/New_York", "UTC").

        Returns:
            Current datetime, UTC offset, and timezone details.
        """
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        return {
            "timezone": timezone,
            "datetime": now.isoformat(),
            "utc_offset": now.strftime("%z"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": now.strftime("%A"),
            "day_of_year": now.timetuple().tm_yday,
            "week_number": now.isocalendar()[1],
        }

    @mcp.tool()
    async def convert_timezone(
        datetime_str: str, from_tz: str, to_tz: str
    ) -> dict:
        """Convert a datetime from one timezone to another.

        Args:
            datetime_str: ISO-8601 datetime string (e.g. "2026-03-18T14:30:00").
            from_tz: Source IANA timezone (e.g. "America/New_York").
            to_tz: Target IANA timezone (e.g. "Asia/Tokyo").

        Returns:
            The original and converted datetime with timezone details.
        """
        source_tz = ZoneInfo(from_tz)
        target_tz = ZoneInfo(to_tz)

        naive_dt = datetime.fromisoformat(datetime_str)
        if naive_dt.tzinfo is not None:
            source_dt = naive_dt.astimezone(source_tz)
        else:
            source_dt = naive_dt.replace(tzinfo=source_tz)

        target_dt = source_dt.astimezone(target_tz)

        return {
            "original": {
                "datetime": source_dt.isoformat(),
                "timezone": from_tz,
                "utc_offset": source_dt.strftime("%z"),
            },
            "converted": {
                "datetime": target_dt.isoformat(),
                "timezone": to_tz,
                "utc_offset": target_dt.strftime("%z"),
            },
        }

    @mcp.tool()
    async def list_timezones(region: str | None = None) -> dict:
        """List available IANA timezones, optionally filtered by region.

        Args:
            region: Optional region prefix to filter by (e.g. "America",
                "Europe", "Asia"). Case-insensitive.

        Returns:
            A sorted list of matching timezone identifiers and their count.
        """
        all_tzs = sorted(available_timezones())
        if region:
            prefix = region.strip().capitalize()
            filtered = [tz for tz in all_tzs if tz.startswith(prefix)]
        else:
            filtered = all_tzs

        return {"timezones": filtered, "count": len(filtered)}

    @mcp.tool()
    async def time_until(
        target_datetime_str: str, timezone: str = "UTC"
    ) -> dict:
        """Calculate the time remaining until a target datetime.

        Args:
            target_datetime_str: ISO-8601 datetime string for the target
                (e.g. "2026-12-31T23:59:59").
            timezone: IANA timezone for the target datetime (default "UTC").

        Returns:
            The time remaining broken down into days, hours, minutes, seconds,
            plus total seconds. Negative values indicate the target is in the past.
        """
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)

        naive_target = datetime.fromisoformat(target_datetime_str)
        if naive_target.tzinfo is not None:
            target = naive_target.astimezone(tz)
        else:
            target = naive_target.replace(tzinfo=tz)

        delta = target - now
        total_seconds = int(delta.total_seconds())
        is_past = total_seconds < 0
        abs_seconds = abs(total_seconds)

        days, remainder = divmod(abs_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        return {
            "target": target.isoformat(),
            "now": now.isoformat(),
            "timezone": timezone,
            "is_past": is_past,
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
            "total_seconds": total_seconds,
        }
