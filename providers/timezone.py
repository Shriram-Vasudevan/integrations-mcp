"""Timezone and world clock provider using WorldTimeAPI."""

from datetime import datetime, timedelta, timezone as tz

import httpx
from mcp.server.fastmcp import FastMCP

WORLDTIME_BASE = "http://worldtimeapi.org/api"

# Mapping of common city names to IANA timezone strings.
CITY_TO_TIMEZONE: dict[str, str] = {
    "new york": "America/New_York",
    "nyc": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "la": "America/Los_Angeles",
    "chicago": "America/Chicago",
    "denver": "America/Denver",
    "phoenix": "America/Phoenix",
    "anchorage": "America/Anchorage",
    "honolulu": "Pacific/Honolulu",
    "toronto": "America/Toronto",
    "vancouver": "America/Vancouver",
    "mexico city": "America/Mexico_City",
    "sao paulo": "America/Sao_Paulo",
    "buenos aires": "America/Argentina/Buenos_Aires",
    "bogota": "America/Bogota",
    "lima": "America/Lima",
    "santiago": "America/Santiago",
    "london": "Europe/London",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "amsterdam": "Europe/Amsterdam",
    "brussels": "Europe/Brussels",
    "rome": "Europe/Rome",
    "madrid": "Europe/Madrid",
    "lisbon": "Europe/Lisbon",
    "zurich": "Europe/Zurich",
    "vienna": "Europe/Vienna",
    "warsaw": "Europe/Warsaw",
    "prague": "Europe/Prague",
    "stockholm": "Europe/Stockholm",
    "oslo": "Europe/Oslo",
    "copenhagen": "Europe/Copenhagen",
    "helsinki": "Europe/Helsinki",
    "athens": "Europe/Athens",
    "istanbul": "Europe/Istanbul",
    "moscow": "Europe/Moscow",
    "dubai": "Asia/Dubai",
    "riyadh": "Asia/Riyadh",
    "tehran": "Asia/Tehran",
    "karachi": "Asia/Karachi",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "kolkata": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata",
    "chennai": "Asia/Kolkata",
    "dhaka": "Asia/Dhaka",
    "bangkok": "Asia/Bangkok",
    "jakarta": "Asia/Jakarta",
    "singapore": "Asia/Singapore",
    "kuala lumpur": "Asia/Kuala_Lumpur",
    "hong kong": "Asia/Hong_Kong",
    "shanghai": "Asia/Shanghai",
    "beijing": "Asia/Shanghai",
    "taipei": "Asia/Taipei",
    "seoul": "Asia/Seoul",
    "tokyo": "Asia/Tokyo",
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "brisbane": "Australia/Brisbane",
    "perth": "Australia/Perth",
    "auckland": "Pacific/Auckland",
    "fiji": "Pacific/Fiji",
    "cairo": "Africa/Cairo",
    "lagos": "Africa/Lagos",
    "nairobi": "Africa/Nairobi",
    "johannesburg": "Africa/Johannesburg",
    "cape town": "Africa/Johannesburg",
    "casablanca": "Africa/Casablanca",
    "accra": "Africa/Accra",
    "addis ababa": "Africa/Addis_Ababa",
    "kathmandu": "Asia/Kathmandu",
    "colombo": "Asia/Colombo",
    "yangon": "Asia/Yangon",
    "hanoi": "Asia/Ho_Chi_Minh",
    "ho chi minh": "Asia/Ho_Chi_Minh",
    "manila": "Asia/Manila",
    "san francisco": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",
    "boston": "America/New_York",
    "miami": "America/New_York",
    "atlanta": "America/New_York",
    "dallas": "America/Chicago",
    "houston": "America/Chicago",
    "detroit": "America/Detroit",
    "minneapolis": "America/Chicago",
    "portland": "America/Los_Angeles",
    "las vegas": "America/Los_Angeles",
    "montreal": "America/Toronto",
    "dublin": "Europe/Dublin",
    "edinburgh": "Europe/London",
    "munich": "Europe/Berlin",
    "barcelona": "Europe/Madrid",
    "milan": "Europe/Rome",
    "doha": "Asia/Qatar",
    "abu dhabi": "Asia/Dubai",
    "colombo": "Asia/Colombo",
}


def _parse_natural_timezone(city_name: str) -> str | None:
    """Map a common city name to its IANA timezone string.

    Returns None if the city is not in the bundled dictionary.
    """
    return CITY_TO_TIMEZONE.get(city_name.lower().strip())


async def _api_get(path: str) -> dict | list:
    """Make a GET request to WorldTimeAPI."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{WORLDTIME_BASE}{path}")
        resp.raise_for_status()
        return resp.json()


def _parse_utc_offset(offset_str: str) -> timedelta:
    """Parse a UTC offset string like '+05:30' or '-04:00' into a timedelta."""
    sign = 1 if offset_str[0] == "+" else -1
    parts = offset_str[1:].split(":")
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    return timedelta(hours=sign * hours, minutes=sign * minutes)


def register(mcp: FastMCP) -> None:
    """Register timezone tools with the MCP server."""

    @mcp.tool()
    async def get_current_time(timezone: str) -> dict:
        """Get the current time in a given timezone.

        Args:
            timezone: IANA timezone string (e.g. "America/New_York") or a
                common city name (e.g. "tokyo", "new york").

        Returns:
            Current datetime, UTC offset, day of week, and timezone details.
        """
        resolved = _parse_natural_timezone(timezone)
        tz_id = resolved if resolved else timezone

        data = await _api_get(f"/timezone/{tz_id}")
        return {
            "timezone": data.get("timezone"),
            "datetime": data.get("datetime"),
            "utc_offset": data.get("utc_offset"),
            "day_of_week": data.get("day_of_week"),
            "day_of_year": data.get("day_of_year"),
            "week_number": data.get("week_number"),
            "abbreviation": data.get("abbreviation"),
            "dst": data.get("dst"),
            "resolved_from": timezone if resolved else None,
        }

    @mcp.tool()
    async def list_timezones() -> dict:
        """List all available IANA timezones from WorldTimeAPI.

        Returns:
            A dict with a 'timezones' key containing the full list of
            supported timezone identifiers.
        """
        data = await _api_get("/timezone")
        return {"timezones": data, "count": len(data)}

    @mcp.tool()
    async def convert_time(
        datetime_str: str, from_tz: str, to_tz: str
    ) -> dict:
        """Convert a datetime from one timezone to another.

        Args:
            datetime_str: ISO-8601 datetime string (e.g. "2026-03-18T14:30:00").
            from_tz: Source IANA timezone or city name.
            to_tz: Target IANA timezone or city name.

        Returns:
            The original and converted datetime with timezone details.
        """
        from_resolved = _parse_natural_timezone(from_tz) or from_tz
        to_resolved = _parse_natural_timezone(to_tz) or to_tz

        # Fetch current offset info for both timezones
        from_data = await _api_get(f"/timezone/{from_resolved}")
        to_data = await _api_get(f"/timezone/{to_resolved}")

        from_offset = _parse_utc_offset(from_data["utc_offset"])
        to_offset = _parse_utc_offset(to_data["utc_offset"])

        # Parse the input datetime and attach the source offset
        naive_dt = datetime.fromisoformat(datetime_str)
        source_dt = naive_dt.replace(tzinfo=tz(from_offset))

        # Convert to target timezone
        target_dt = source_dt.astimezone(tz(to_offset))

        return {
            "original": {
                "datetime": source_dt.isoformat(),
                "timezone": from_data.get("timezone"),
                "abbreviation": from_data.get("abbreviation"),
                "utc_offset": from_data.get("utc_offset"),
            },
            "converted": {
                "datetime": target_dt.isoformat(),
                "timezone": to_data.get("timezone"),
                "abbreviation": to_data.get("abbreviation"),
                "utc_offset": to_data.get("utc_offset"),
            },
        }

    @mcp.tool()
    async def get_time_difference(tz1: str, tz2: str) -> dict:
        """Get the current time difference between two timezones.

        Args:
            tz1: First IANA timezone or city name.
            tz2: Second IANA timezone or city name.

        Returns:
            Current times in both zones and the difference in hours/minutes.
        """
        tz1_resolved = _parse_natural_timezone(tz1) or tz1
        tz2_resolved = _parse_natural_timezone(tz2) or tz2

        data1 = await _api_get(f"/timezone/{tz1_resolved}")
        data2 = await _api_get(f"/timezone/{tz2_resolved}")

        offset1 = _parse_utc_offset(data1["utc_offset"])
        offset2 = _parse_utc_offset(data2["utc_offset"])

        diff = offset2 - offset1
        total_minutes = int(diff.total_seconds() / 60)
        diff_hours = total_minutes // 60
        diff_minutes = abs(total_minutes) % 60

        sign = "+" if total_minutes >= 0 else "-"
        diff_str = f"{sign}{abs(diff_hours)}h"
        if diff_minutes:
            diff_str += f"{diff_minutes}m"

        return {
            "tz1": {
                "timezone": data1.get("timezone"),
                "datetime": data1.get("datetime"),
                "utc_offset": data1.get("utc_offset"),
                "abbreviation": data1.get("abbreviation"),
            },
            "tz2": {
                "timezone": data2.get("timezone"),
                "datetime": data2.get("datetime"),
                "utc_offset": data2.get("utc_offset"),
                "abbreviation": data2.get("abbreviation"),
            },
            "difference": diff_str,
            "difference_total_minutes": total_minutes,
        }

    @mcp.tool()
    async def parse_natural_timezone(city_name: str) -> dict:
        """Map a common city name to its IANA timezone identifier.

        Uses a bundled dictionary of ~100 major cities. Useful for resolving
        informal city references before calling other timezone tools.

        Args:
            city_name: A city name (e.g. "tokyo", "new york", "mumbai").

        Returns:
            The resolved IANA timezone, or a list of suggestions if not found.
        """
        result = _parse_natural_timezone(city_name)
        if result:
            return {
                "city": city_name,
                "timezone": result,
                "found": True,
            }

        # Offer partial matches
        query = city_name.lower().strip()
        suggestions = [
            {"city": city, "timezone": tz_str}
            for city, tz_str in CITY_TO_TIMEZONE.items()
            if query in city or city in query
        ]
        return {
            "city": city_name,
            "found": False,
            "message": f"No exact match for '{city_name}'.",
            "suggestions": suggestions[:10],
        }
