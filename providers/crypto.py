"""CoinGecko crypto price provider using the free public API."""

import httpx
from mcp.server.fastmcp import FastMCP

COINGECKO_API = "https://api.coingecko.com/api/v3"


def register(mcp: FastMCP) -> None:
    """Register crypto price tools with the MCP server."""

    @mcp.tool()
    async def get_crypto_price(coin_id: str, vs_currency: str = "usd") -> dict:
        """Get the current price, market cap, and 24h change for a cryptocurrency.

        Args:
            coin_id: CoinGecko coin ID (e.g. "bitcoin", "ethereum", "solana").
            vs_currency: Target currency for the price (default "usd").

        Returns:
            Price, market cap, and 24-hour change percentage for the coin.
        """
        cur = vs_currency.lower()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{COINGECKO_API}/simple/price",
                params={
                    "ids": coin_id,
                    "vs_currencies": cur,
                    "include_market_cap": "true",
                    "include_24hr_change": "true",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        info = data.get(coin_id.lower(), {})
        return {
            "coin_id": coin_id.lower(),
            "currency": cur,
            "price": info.get(cur),
            "market_cap": info.get(f"{cur}_market_cap"),
            "change_24h_pct": info.get(f"{cur}_24h_change"),
        }

    @mcp.tool()
    async def get_top_coins(limit: int = 10) -> dict:
        """Get the top cryptocurrencies ranked by market cap.

        Args:
            limit: Number of coins to return (default 10, max 250).

        Returns:
            List of top coins with price, market cap, and 24h change.
        """
        limit = max(1, min(limit, 250))
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{COINGECKO_API}/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": limit,
                    "page": 1,
                    "sparkline": "false",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        coins = []
        for coin in data:
            coins.append({
                "rank": coin.get("market_cap_rank"),
                "id": coin.get("id"),
                "symbol": coin.get("symbol"),
                "name": coin.get("name"),
                "price_usd": coin.get("current_price"),
                "market_cap": coin.get("market_cap"),
                "change_24h_pct": coin.get("price_change_percentage_24h"),
            })

        return {
            "count": len(coins),
            "coins": coins,
        }
