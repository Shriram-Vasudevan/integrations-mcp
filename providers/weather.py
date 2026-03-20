"""Weather provider using the free Open-Meteo API — no auth required."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def register(mcp: FastMCP) -> None:
    """Register weather tools with the MCP server."""

    @mcp.tool()
    async def get_current_weather(latitude: float, longitude: float) -> dict:
        """Get current weather conditions for given coordinates.

        Args:
            latitude: Latitude of the location (-90 to 90).
            longitude: Longitude of the location (-180 to 180).

        Returns:
            Current temperature (°C), wind speed (km/h), and weather code with description.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                BASE_URL,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current_weather": "true",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        current = data.get("current_weather", {})
        code = current.get("weathercode", -1)

        return {
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "temperature_c": current.get("temperature"),
            "windspeed_kmh": current.get("windspeed"),
            "weather_code": code,
            "weather_description": WEATHER_CODES.get(code, "Unknown"),
            "observation_time": current.get("time"),
        }

    @mcp.tool()
    async def get_forecast(latitude: float, longitude: float, days: int = 7) -> dict:
        """Get a multi-day weather forecast for given coordinates.

        Args:
            latitude: Latitude of the location (-90 to 90).
            longitude: Longitude of the location (-180 to 180).
            days: Number of forecast days (1-16, default 7).

        Returns:
            Daily forecast with high/low temperature, precipitation, and weather code.
        """
        days = max(1, min(days, 16))

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                BASE_URL,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                    "forecast_days": days,
                    "timezone": "auto",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        forecast = []
        for i, date in enumerate(dates):
            code = daily["weathercode"][i]
            forecast.append({
                "date": date,
                "temperature_max_c": daily["temperature_2m_max"][i],
                "temperature_min_c": daily["temperature_2m_min"][i],
                "precipitation_mm": daily["precipitation_sum"][i],
                "weather_code": code,
                "weather_description": WEATHER_CODES.get(code, "Unknown"),
            })

        return {
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "timezone": data.get("timezone"),
            "forecast_days": len(forecast),
            "daily_forecast": forecast,
        }

    @mcp.tool()
    async def get_historical_weather(
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
    ) -> dict:
        """Get historical weather data for given coordinates and date range.

        Args:
            latitude: Latitude of the location (-90 to 90).
            longitude: Longitude of the location (-180 to 180).
            start_date: Start date in ISO format (YYYY-MM-DD).
            end_date: End date in ISO format (YYYY-MM-DD).

        Returns:
            Daily historical weather with max/min temperature, precipitation,
            wind speed, and weather code with description.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                ARCHIVE_URL,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "start_date": start_date,
                    "end_date": end_date,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,weathercode",
                    "timezone": "auto",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        history = []
        for i, date in enumerate(dates):
            code = daily["weathercode"][i]
            history.append({
                "date": date,
                "temperature_max_c": daily["temperature_2m_max"][i],
                "temperature_min_c": daily["temperature_2m_min"][i],
                "precipitation_mm": daily["precipitation_sum"][i],
                "windspeed_max_kmh": daily["windspeed_10m_max"][i],
                "weather_code": code,
                "weather_description": WEATHER_CODES.get(code, "Unknown") if code is not None else "Unknown",
            })

        return {
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "timezone": data.get("timezone"),
            "start_date": start_date,
            "end_date": end_date,
            "total_days": len(history),
            "daily_history": history,
        }
