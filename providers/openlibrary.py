"""Open Library provider — search books, fetch details, and look up authors.

Uses the free Open Library API (https://openlibrary.org) with no authentication.
"""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://openlibrary.org"


async def _get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{BASE_URL}{path}",
            params=params,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register Open Library tools with the MCP server."""

    @mcp.tool()
    async def search_books(query: str, limit: int = 10) -> dict:
        """Search for books on Open Library.

        Args:
            query: Search term (title, author, subject, etc.).
            limit: Maximum results to return (1-100, default 10).

        Returns:
            Matching books with title, author, year, and ISBN.
        """
        limit = max(1, min(limit, 100))
        data = await _get("/search.json", params={"q": query, "limit": limit})
        results = []
        for doc in data.get("docs", []):
            isbns = doc.get("isbn", [])
            results.append({
                "title": doc.get("title"),
                "author": doc.get("author_name", []),
                "first_publish_year": doc.get("first_publish_year"),
                "isbn": isbns[0] if isbns else None,
                "olid": doc.get("key", "").replace("/works/", ""),
                "edition_count": doc.get("edition_count"),
            })
        return {
            "query": query,
            "total_results": data.get("numFound", 0),
            "result_count": len(results),
            "results": results,
        }

    @mcp.tool()
    async def get_book(olid: str) -> dict:
        """Get full details for a book by its Open Library work ID.

        Args:
            olid: Open Library work ID (e.g. "OL45804W").

        Returns:
            Book details including title, description, and subjects.
        """
        olid = olid.strip().removeprefix("/works/")
        data = await _get(f"/works/{olid}.json")

        description = data.get("description")
        if isinstance(description, dict):
            description = description.get("value", "")

        subjects = data.get("subjects", [])

        # Resolve author names
        authors = []
        for author_ref in data.get("authors", []):
            author_obj = author_ref.get("author", author_ref)
            author_key = author_obj.get("key", "")
            if author_key:
                try:
                    author_data = await _get(f"{author_key}.json")
                    authors.append(author_data.get("name"))
                except Exception:
                    authors.append(author_key)

        return {
            "title": data.get("title"),
            "olid": olid,
            "description": description,
            "subjects": subjects[:20],
            "authors": authors,
            "first_publish_date": data.get("first_publish_date"),
            "url": f"https://openlibrary.org/works/{olid}",
        }

    @mcp.tool()
    async def search_author(name: str) -> dict:
        """Search for an author on Open Library by name.

        Args:
            name: Author name to search for.

        Returns:
            Author details including bio and list of works.
        """
        search_data = await _get("/search/authors.json", params={"q": name})
        docs = search_data.get("docs", [])
        if not docs:
            return {"error": f"No author found for: {name}"}

        top = docs[0]
        author_key = top.get("key")

        # Fetch full author record
        author_data = await _get(f"/authors/{author_key}.json")

        bio = author_data.get("bio")
        if isinstance(bio, dict):
            bio = bio.get("value", "")

        # Fetch the author's works
        works_data = await _get(
            f"/authors/{author_key}/works.json", params={"limit": 25}
        )
        works = []
        for entry in works_data.get("entries", []):
            works.append({
                "title": entry.get("title"),
                "olid": entry.get("key", "").replace("/works/", ""),
                "first_publish_date": entry.get("first_publish_date"),
            })

        return {
            "name": author_data.get("name"),
            "key": author_key,
            "bio": bio,
            "birth_date": author_data.get("birth_date"),
            "death_date": author_data.get("death_date"),
            "work_count": top.get("work_count"),
            "works": works,
            "url": f"https://openlibrary.org/authors/{author_key}",
        }
