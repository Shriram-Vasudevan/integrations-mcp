"""Currency exchange rate provider using the Frankfurter API (ECB data)."""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.frankfurter.app"


async def _get(path: str, params: dict | None = None) -> dict:
    """Make a GET request to the Frankfurter API."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{BASE_URL}{path}", params=params or {})
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register currency tools with the MCP server."""

    @mcp.tool()
    async def get_exchange_rate(from_currency: str, to_currency: str) -> dict:
        """Get the latest exchange rate between two currencies.

        Uses ECB reference rates via the Frankfurter API.

        Args:
            from_currency: Source currency code (e.g. "USD").
            to_currency: Target currency code (e.g. "EUR").

        Returns:
            Latest exchange rate with base and target currencies.
        """
        data = await _get("/latest", {
            "from": from_currency.upper(),
            "to": to_currency.upper(),
        })
        target = to_currency.upper()
        return {
            "from": data.get("base", from_currency.upper()),
            "to": target,
            "rate": data.get("rates", {}).get(target),
            "date": data.get("date"),
        }

    @mcp.tool()
    async def convert_amount(
        amount: float, from_currency: str, to_currency: str
    ) -> dict:
        """Convert a monetary amount between two currencies at the latest rate.

        Args:
            amount: The amount to convert.
            from_currency: Source currency code (e.g. "GBP").
            to_currency: Target currency code (e.g. "JPY").

        Returns:
            Converted amount with rate details.
        """
        data = await _get("/latest", {
            "amount": amount,
            "from": from_currency.upper(),
            "to": to_currency.upper(),
        })
        target = to_currency.upper()
        converted = data.get("rates", {}).get(target)
        return {
            "amount": amount,
            "from": data.get("base", from_currency.upper()),
            "to": target,
            "converted": converted,
            "rate": round(converted / amount, 6) if converted and amount else None,
            "date": data.get("date"),
        }

    @mcp.tool()
    async def list_currencies() -> dict:
        """List all currencies supported by the Frankfurter API.

        Returns:
            Dictionary mapping currency codes to their full names.
        """
        data = await _get("/currencies")
        return {"currencies": data, "count": len(data)}

    @mcp.tool()
    async def get_historical_rate(
        from_currency: str, to_currency: str, date: str
    ) -> dict:
        """Get the exchange rate for a specific historical date.

        Args:
            from_currency: Source currency code (e.g. "USD").
            to_currency: Target currency code (e.g. "EUR").
            date: Date in YYYY-MM-DD format (e.g. "2024-01-15").

        Returns:
            Exchange rate for the given date.
        """
        data = await _get(f"/{date}", {
            "from": from_currency.upper(),
            "to": to_currency.upper(),
        })
        target = to_currency.upper()
        return {
            "from": data.get("base", from_currency.upper()),
            "to": target,
            "rate": data.get("rates", {}).get(target),
            "date": data.get("date"),
        }
