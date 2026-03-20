"""NASA APIs provider — APOD, Mars Rover Photos, Near Earth Objects, and EPIC Earth Imagery."""

import os

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.nasa.gov"
APOD_URL = f"{BASE_URL}/planetary/apod"
NEO_URL = f"{BASE_URL}/neo/rest/v1/feed"
MARS_PHOTOS_BASE = f"{BASE_URL}/mars-photos/api/v1/rovers"
EPIC_URL = f"{BASE_URL}/EPIC/api/natural"
EPIC_ARCHIVE_BASE = "https://epic.gsfc.nasa.gov/archive/natural"


def _api_key() -> str:
    """Return the NASA API key from env or fall back to DEMO_KEY."""
    return os.environ.get("NASA_API_KEY", "DEMO_KEY")


async def _get(url: str, params: dict) -> dict | list:
    """Make a GET request to a NASA API endpoint."""
    params["api_key"] = _api_key()
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=30.0)
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register NASA tools with the MCP server."""

    @mcp.tool()
    async def get_astronomy_picture_of_the_day(date: str | None = None) -> dict:
        """Get the NASA Astronomy Picture of the Day (APOD).

        Args:
            date: Optional date in YYYY-MM-DD format. Defaults to today.

        Returns:
            Title, explanation, image URL, and media type of the APOD entry.
        """
        params: dict = {}
        if date:
            params["date"] = date
        data = await _get(APOD_URL, params)
        return {
            "title": data.get("title"),
            "date": data.get("date"),
            "explanation": data.get("explanation"),
            "url": data.get("url"),
            "hdurl": data.get("hdurl"),
            "media_type": data.get("media_type"),
        }

    @mcp.tool()
    async def get_mars_rover_photos(
        rover: str = "curiosity",
        sol: int = 1000,
        camera: str | None = None,
    ) -> list[dict]:
        """Get photos from a NASA Mars rover.

        Args:
            rover: Rover name — curiosity, opportunity, or spirit. Default curiosity.
            sol: Martian sol (day) number. Default 1000.
            camera: Optional camera abbreviation (FHAZ, RHAZ, MAST, CHEMCAM,
                    MAHLI, MARDI, NAVCAM). If None, returns all cameras.

        Returns:
            List of photo entries with image URL, earth date, camera info,
            and rover metadata.
        """
        url = f"{MARS_PHOTOS_BASE}/{rover.lower()}/photos"
        params: dict = {"sol": sol}
        if camera:
            params["camera"] = camera.lower()
        data = await _get(url, params)
        photos = data.get("photos", [])[:25]
        return [
            {
                "id": p.get("id"),
                "img_src": p.get("img_src"),
                "earth_date": p.get("earth_date"),
                "sol": p.get("sol"),
                "camera": p.get("camera", {}).get("full_name"),
                "rover": p.get("rover", {}).get("name"),
                "rover_status": p.get("rover", {}).get("status"),
            }
            for p in photos
        ]

    @mcp.tool()
    async def get_near_earth_objects(start_date: str, end_date: str) -> list[dict]:
        """Get Near Earth Objects (asteroids) approaching Earth in a date range.

        The date range must not exceed 7 days (NASA API limitation).

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            List of asteroids with name, size estimates, velocity, miss distance,
            and whether they are potentially hazardous.
        """
        data = await _get(NEO_URL, {
            "start_date": start_date,
            "end_date": end_date,
        })
        results = []
        for date_objects in data.get("near_earth_objects", {}).values():
            for neo in date_objects:
                diameter = neo.get("estimated_diameter", {}).get("meters", {})
                close_approach = (
                    neo["close_approach_data"][0]
                    if neo.get("close_approach_data")
                    else {}
                )
                results.append({
                    "name": neo.get("name"),
                    "nasa_jpl_url": neo.get("nasa_jpl_url"),
                    "is_potentially_hazardous": neo.get(
                        "is_potentially_hazardous_asteroid"
                    ),
                    "estimated_diameter_min_m": diameter.get(
                        "estimated_diameter_min"
                    ),
                    "estimated_diameter_max_m": diameter.get(
                        "estimated_diameter_max"
                    ),
                    "close_approach_date": close_approach.get(
                        "close_approach_date_full"
                    ),
                    "relative_velocity_kmh": close_approach.get(
                        "relative_velocity", {}
                    ).get("kilometers_per_hour"),
                    "miss_distance_km": close_approach.get(
                        "miss_distance", {}
                    ).get("kilometers"),
                })
        return results

    @mcp.tool()
    async def get_epic_earth_image(date: str | None = None) -> list[dict]:
        """Get NASA EPIC (Earth Polychromatic Imaging Camera) satellite imagery.

        Returns metadata and image URLs for full-disc Earth photos taken by the
        DSCOVR satellite at the L1 Lagrange point.

        Args:
            date: Optional date in YYYY-MM-DD format. Defaults to the most
                  recent available imagery.

        Returns:
            List of image entries with identifier, caption, coordinates, and
            the constructed image URL.
        """
        url = f"{EPIC_URL}/date/{date}" if date else EPIC_URL
        data = await _get(url, {})
        if not isinstance(data, list):
            data = [data] if data else []
        results = []
        for entry in data[:10]:
            image_name = entry.get("image", "")
            entry_date = entry.get("date", "")
            # Build the archive URL: YYYY/MM/DD/png/<image>.png
            date_path = entry_date[:10].replace("-", "/") if entry_date else ""
            image_url = (
                f"{EPIC_ARCHIVE_BASE}/{date_path}/png/{image_name}.png"
                if date_path and image_name
                else None
            )
            coords = entry.get("centroid_coordinates", {})
            results.append({
                "identifier": entry.get("identifier"),
                "caption": entry.get("caption"),
                "date": entry_date,
                "image_url": image_url,
                "centroid_lat": coords.get("lat"),
                "centroid_lon": coords.get("lon"),
            })
        return results
