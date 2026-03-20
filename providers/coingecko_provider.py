"""CoinGecko provider for crypto/asset price lookups using the public API."""

import httpx
from mcp.server.fastmcp import FastMCP

COINGECKO_API_URL = "https://api.coingecko.com/api/v3"


def register(mcp: FastMCP) -> None:
    """Register CoinGecko tools with the MCP server."""

    @mcp.tool()
    async def get_coin_price(
        coin_ids: str,
        vs_currency: str = "usd",
    ) -> dict:
        """Get current price for one or more cryptocurrencies.

        Args:
            coin_ids: Comma-separated CoinGecko coin IDs (e.g. "bitcoin", "bitcoin,ethereum,solana").
            vs_currency: Target currency for prices (default "usd"). Examples: "usd", "eur", "btc".

        Returns:
            Current prices for each requested coin in the target currency.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{COINGECKO_API_URL}/simple/price",
                params={
                    "ids": coin_ids,
                    "vs_currencies": vs_currency,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for coin_id, prices in data.items():
            results.append({
                "coin_id": coin_id,
                "price": prices.get(vs_currency.lower()),
                "currency": vs_currency.lower(),
            })

        return {
            "count": len(results),
            "currency": vs_currency.lower(),
            "prices": results,
        }

    @mcp.tool()
    async def get_coin_market_data(
        coin_ids: str,
        vs_currency: str = "usd",
    ) -> dict:
        """Get 24h price change and market cap for one or more cryptocurrencies.

        Args:
            coin_ids: Comma-separated CoinGecko coin IDs (e.g. "bitcoin,ethereum").
            vs_currency: Target currency (default "usd").

        Returns:
            Price, 24h change percentage, and market cap for each coin.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{COINGECKO_API_URL}/simple/price",
                params={
                    "ids": coin_ids,
                    "vs_currencies": vs_currency,
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        cur = vs_currency.lower()
        results = []
        for coin_id, info in data.items():
            results.append({
                "coin_id": coin_id,
                "price": info.get(cur),
                "market_cap": info.get(f"{cur}_market_cap"),
                "change_24h_pct": info.get(f"{cur}_24h_change"),
                "currency": cur,
            })

        return {
            "count": len(results),
            "currency": cur,
            "coins": results,
        }

    @mcp.tool()
    async def search_coins(query: str) -> dict:
        """Search for cryptocurrencies by name or symbol on CoinGecko.

        Args:
            query: Search term (e.g. "bitcoin", "eth", "solana").

        Returns:
            Matching coins with their ID, name, symbol, and market cap rank.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{COINGECKO_API_URL}/search",
                params={"query": query},
            )
            resp.raise_for_status()
            data = resp.json()

        coins = []
        for coin in data.get("coins", [])[:20]:
            coins.append({
                "id": coin.get("id"),
                "name": coin.get("name"),
                "symbol": coin.get("symbol"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "thumb": coin.get("thumb"),
            })

        return {
            "query": query,
            "count": len(coins),
            "coins": coins,
        }
