"""Dog CEO provider — random dog images and breed info via https://dog.ceo/api."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://dog.ceo/api"


async def _get(path: str) -> dict:
    """Make a GET request to the Dog CEO API."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{BASE_URL}{path}")
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register dog image tools with the MCP server."""

    @mcp.tool()
    async def get_random_dog_image() -> dict:
        """Get a random dog image URL from the Dog CEO API.

        Returns:
            A dict with the image URL and status.
        """
        data = await _get("/breeds/image/random")
        return {"image_url": data.get("message"), "status": data.get("status")}

    @mcp.tool()
    async def get_random_dog_by_breed(breed: str) -> dict:
        """Get a random image URL for a specific dog breed.

        Args:
            breed: The breed name (e.g. "labrador", "poodle"). For sub-breeds
                   use the format "breed/sub-breed" (e.g. "bulldog/french").

        Returns:
            A dict with the image URL and status.
        """
        data = await _get(f"/breed/{breed}/images/random")
        if data.get("status") == "error":
            return {"error": True, "message": data.get("message")}
        return {"image_url": data.get("message"), "status": data.get("status")}

    @mcp.tool()
    async def list_dog_breeds() -> dict:
        """List all available dog breeds and their sub-breeds.

        Returns:
            A dict mapping each breed to a list of its sub-breeds (empty list if none).
        """
        data = await _get("/breeds/list/all")
        return {"breeds": data.get("message", {}), "status": data.get("status")}

    @mcp.tool()
    async def get_breed_images(breed: str, limit: int = 5) -> dict:
        """Get multiple image URLs for a specific dog breed.

        Args:
            breed: The breed name (e.g. "labrador"). For sub-breeds use
                   "breed/sub-breed" (e.g. "bulldog/french").
            limit: Maximum number of images to return (default 5).

        Returns:
            A dict with a list of image URLs and status.
        """
        data = await _get(f"/breed/{breed}/images")
        if data.get("status") == "error":
            return {"error": True, "message": data.get("message")}
        images = data.get("message", [])[:limit]
        return {"images": images, "count": len(images), "status": data.get("status")}
