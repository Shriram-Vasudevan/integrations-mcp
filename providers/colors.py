"""Color provider using the free thecolorapi.com API — no auth required."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://www.thecolorapi.com"


def register(mcp: FastMCP) -> None:
    """Register color tools with the MCP server."""

    @mcp.tool()
    async def get_color_info(hex: str) -> dict:
        """Get detailed information about a color by its hex code.

        Args:
            hex: Hex color code (e.g. "FF5733" or "#FF5733").

        Returns:
            Color name, RGB, HSL, and CMYK values.
        """
        hex_clean = hex.lstrip("#")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BASE_URL}/id",
                params={"hex": hex_clean},
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "name": data["name"]["value"],
            "hex": data["hex"]["value"],
            "rgb": {
                "r": data["rgb"]["r"],
                "g": data["rgb"]["g"],
                "b": data["rgb"]["b"],
            },
            "hsl": {
                "h": data["hsl"]["h"],
                "s": data["hsl"]["s"],
                "l": data["hsl"]["l"],
            },
            "cmyk": {
                "c": data["cmyk"]["c"],
                "m": data["cmyk"]["m"],
                "y": data["cmyk"]["y"],
                "k": data["cmyk"]["k"],
            },
        }

    @mcp.tool()
    async def get_color_scheme(
        hex: str, mode: str = "analogic", count: int = 5
    ) -> dict:
        """Generate a color scheme/palette based on a seed color.

        Args:
            hex: Hex color code (e.g. "FF5733" or "#FF5733").
            mode: Scheme mode — one of monochrome, analogic, complement, triad, quad.
            count: Number of colors to return (default 5).

        Returns:
            A palette of related colors with name, hex, RGB, HSL, and CMYK for each.
        """
        hex_clean = hex.lstrip("#")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BASE_URL}/scheme",
                params={"hex": hex_clean, "mode": mode, "count": count},
            )
            resp.raise_for_status()
            data = resp.json()

        colors = []
        for color in data.get("colors", []):
            colors.append({
                "name": color["name"]["value"],
                "hex": color["hex"]["value"],
                "rgb": {
                    "r": color["rgb"]["r"],
                    "g": color["rgb"]["g"],
                    "b": color["rgb"]["b"],
                },
                "hsl": {
                    "h": color["hsl"]["h"],
                    "s": color["hsl"]["s"],
                    "l": color["hsl"]["l"],
                },
                "cmyk": {
                    "c": color["cmyk"]["c"],
                    "m": color["cmyk"]["m"],
                    "y": color["cmyk"]["y"],
                    "k": color["cmyk"]["k"],
                },
            })

        return {
            "mode": mode,
            "count": len(colors),
            "seed": {
                "name": data["seed"]["name"]["value"],
                "hex": data["seed"]["hex"]["value"],
            },
            "colors": colors,
        }
