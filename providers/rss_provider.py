"""RSS/Atom feed reader provider."""

from datetime import datetime, timezone, timedelta
from time import mktime

import httpx
from mcp.server.fastmcp import FastMCP

USER_AGENT = "integrations-mcp/0.1.0"


def _parse_date(entry) -> str | None:
    """Extract a published date string from a feed entry."""
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            dt = datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
            return dt.isoformat()
    return entry.get("published") or entry.get("updated")


def _entry_to_item(entry) -> dict:
    """Convert a feedparser entry to a structured item dict."""
    return {
        "title": entry.get("title", ""),
        "link": entry.get("link", ""),
        "summary": entry.get("summary", ""),
        "published": _parse_date(entry),
        "author": entry.get("author", ""),
    }


def _is_within_hours(entry, hours: float) -> bool:
    """Check if an entry was published within the last N hours."""
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            dt = datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            return dt >= cutoff
    return True  # include entries with no parseable date


async def _fetch_feed(url: str):
    """Fetch feed content via httpx and parse with feedparser."""
    import feedparser
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=30.0,
        )
        resp.raise_for_status()
    return feedparser.parse(resp.text)


def register(mcp: FastMCP) -> None:
    """Register RSS/Atom feed tools with the MCP server."""

    @mcp.tool()
    async def fetch_rss_feed(url: str, max_items: int = 20) -> dict:
        """Fetch and parse an RSS or Atom feed URL.

        Returns structured feed metadata and items with title, link, summary,
        published date, and author.

        Args:
            url: The RSS or Atom feed URL to fetch.
            max_items: Maximum number of items to return (default 20).

        Returns:
            Feed metadata and list of parsed items.
        """
        feed = await _fetch_feed(url)
        if feed.bozo and not feed.entries:
            raise ValueError(
                f"Failed to parse feed: {feed.bozo_exception}"
            )
        items = [_entry_to_item(e) for e in feed.entries[:max_items]]
        return {
            "feed_title": feed.feed.get("title", ""),
            "feed_link": feed.feed.get("link", ""),
            "feed_description": feed.feed.get("description", ""),
            "item_count": len(items),
            "items": items,
        }

    @mcp.tool()
    async def popular_feeds() -> dict:
        """Return a curated dictionary of well-known RSS/Atom feed URLs by category.

        Categories include tech, science, world news, and finance.

        Returns:
            Dictionary mapping category names to lists of feeds with name and URL.
        """
        return {
            "tech": [
                {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
                {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
                {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
                {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
                {"name": "Hacker News", "url": "https://hnrss.org/frontpage"},
                {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/"},
            ],
            "science": [
                {"name": "Nature", "url": "https://www.nature.com/nature.rss"},
                {"name": "Science Daily", "url": "https://www.sciencedaily.com/rss/all.xml"},
                {"name": "NASA Breaking News", "url": "https://www.nasa.gov/news-release/feed/"},
                {"name": "New Scientist", "url": "https://www.newscientist.com/feed/home/"},
                {"name": "Phys.org", "url": "https://phys.org/rss-feed/"},
            ],
            "world_news": [
                {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
                {"name": "Reuters World", "url": "https://www.reutersagency.com/feed/"},
                {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
                {"name": "NPR News", "url": "https://feeds.npr.org/1001/rss.xml"},
                {"name": "AP News", "url": "https://rsshub.app/apnews/topics/apf-topnews"},
            ],
            "finance": [
                {"name": "Bloomberg Markets", "url": "https://feeds.bloomberg.com/markets/news.rss"},
                {"name": "CNBC Top News", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"},
                {"name": "Financial Times", "url": "https://www.ft.com/rss/home"},
                {"name": "MarketWatch", "url": "https://feeds.marketwatch.com/marketwatch/topstories/"},
                {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news/rssindex"},
            ],
        }

    @mcp.tool()
    async def fetch_rss_feed_recent(
        url: str, hours: float = 24, max_items: int = 50
    ) -> dict:
        """Fetch an RSS/Atom feed and return only items from the last N hours.

        Useful for monitoring feeds for recent updates — tech news, changelogs,
        blog posts, etc.

        Args:
            url: The RSS or Atom feed URL to fetch.
            hours: Only include items published within this many hours (default 24).
            max_items: Maximum number of items to return (default 50).

        Returns:
            Feed metadata and list of recent items.
        """
        feed = await _fetch_feed(url)
        if feed.bozo and not feed.entries:
            raise ValueError(
                f"Failed to parse feed: {feed.bozo_exception}"
            )
        recent = [
            _entry_to_item(e)
            for e in feed.entries
            if _is_within_hours(e, hours)
        ][:max_items]
        return {
            "feed_title": feed.feed.get("title", ""),
            "feed_link": feed.feed.get("link", ""),
            "filter_hours": hours,
            "item_count": len(recent),
            "items": recent,
        }
