"""QR code generator provider using the goqr.me API (free, no auth)."""

from urllib.parse import urlencode

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.qrserver.com/v1/create-qr-code/"


def _build_qr_url(params: dict) -> str:
    """Build a QR code image URL from parameters."""
    return f"{BASE_URL}?{urlencode(params)}"


def register(mcp: FastMCP) -> None:
    """Register QR code tools with the MCP server."""

    @mcp.tool()
    async def create_qr_code(
        data: str, size: str = "200x200", format: str = "png"
    ) -> dict:
        """Generate a QR code image URL for the given data.

        The goqr.me API returns an image directly at the constructed URL,
        so this tool returns the URL without downloading the image.

        Args:
            data: The text or URL to encode in the QR code.
            size: Image dimensions as WIDTHxHEIGHT (e.g. "200x200", "400x400").
            format: Image format — "png", "gif", "jpeg", or "svg".

        Returns:
            The direct image URL for the generated QR code.
        """
        url = _build_qr_url({"data": data, "size": size, "format": format})
        return {"qr_url": url, "data": data, "size": size, "format": format}

    @mcp.tool()
    async def create_qr_code_with_options(
        data: str,
        size: str = "200x200",
        color: str = "000000",
        bgcolor: str = "ffffff",
    ) -> dict:
        """Generate a colored QR code image URL with custom foreground and background colors.

        Args:
            data: The text or URL to encode in the QR code.
            size: Image dimensions as WIDTHxHEIGHT (e.g. "200x200", "400x400").
            color: Foreground (QR module) color as a hex string without '#' (e.g. "ff0000" for red).
            bgcolor: Background color as a hex string without '#' (e.g. "ffffff" for white).

        Returns:
            The direct image URL for the generated QR code with custom colors.
        """
        url = _build_qr_url({
            "data": data,
            "size": size,
            "color": color,
            "bgcolor": bgcolor,
            "format": "png",
        })
        return {
            "qr_url": url,
            "data": data,
            "size": size,
            "color": color,
            "bgcolor": bgcolor,
        }
