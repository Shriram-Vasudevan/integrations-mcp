"""Exchange rates provider using the free Frankfurter API — no auth required."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.frankfurter.app"


def register(mcp: FastMCP) -> None:
    """Register exchange rate tools with the MCP server."""

    @mcp.tool()
    async def get_latest_rates(
        base: str = "USD", symbols: str | None = None
    ) -> dict:
        """Get the latest exchange rates for a base currency.

        Args:
            base: The base currency code (default "USD").
            symbols: Comma-separated target currency codes (e.g. "EUR,GBP").
                     If omitted, all available rates are returned.

        Returns:
            Latest exchange rates relative to the base currency.
        """
        params: dict[str, str] = {"from": base.upper()}
        if symbols:
            params["to"] = symbols.upper()

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/latest", params=params)
            resp.raise_for_status()
            return resp.json()

    @mcp.tool()
    async def convert_currency(
        amount: float, from_currency: str, to_currency: str
    ) -> dict:
        """Convert a monetary amount between two currencies at the latest rate.

        Args:
            amount: The amount to convert.
            from_currency: Source currency code (e.g. "USD").
            to_currency: Target currency code (e.g. "EUR").

        Returns:
            Converted amount with the rate used.
        """
        params = {
            "amount": str(amount),
            "from": from_currency.upper(),
            "to": to_currency.upper(),
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/latest", params=params)
            resp.raise_for_status()
            return resp.json()

    @mcp.tool()
    async def list_currencies() -> dict:
        """List all currencies supported by the Frankfurter exchange rate API.

        Returns:
            A mapping of currency codes to their full names.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/currencies")
            resp.raise_for_status()
            return resp.json()
