"""Open Library provider using the Open Library API (https://openlibrary.org).

Exposes tools for searching books, fetching book details (by ISBN or OLID),
and looking up author bios with their works.
"""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://openlibrary.org"
COVERS_URL = "https://covers.openlibrary.org"


async def _get(path: str, params: dict | None = None) -> dict:
    """Make a GET request to the Open Library API."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}{path}",
            params=params,
            headers={"Accept": "application/json"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register Open Library tools with the MCP server."""

    @mcp.tool()
    async def search_books(query: str, limit: int = 10) -> dict:
        """Search for books on Open Library by keyword.

        Args:
            query: Search term or phrase (title, author, subject, etc.).
            limit: Maximum number of results (1-100, default 10).

        Returns:
            List of matching books with title, author, year, cover URL, and ISBN.
        """
        limit = max(1, min(limit, 100))
        data = await _get("/search.json", params={"q": query, "limit": limit})
        results = []
        for doc in data.get("docs", []):
            isbns = doc.get("isbn", [])
            cover_id = doc.get("cover_i")
            cover_url = (
                f"{COVERS_URL}/b/id/{cover_id}-M.jpg" if cover_id else None
            )
            results.append(
                {
                    "title": doc.get("title"),
                    "author": doc.get("author_name", []),
                    "first_publish_year": doc.get("first_publish_year"),
                    "cover": cover_url,
                    "isbn": isbns[:5],
                    "olid": doc.get("key", "").replace("/works/", ""),
                    "edition_count": doc.get("edition_count"),
                }
            )
        return {
            "query": query,
            "total_results": data.get("numFound", 0),
            "result_count": len(results),
            "results": results,
        }

    @mcp.tool()
    async def book_detail(isbn_or_olid: str) -> dict:
        """Get detailed information about a book from Open Library.

        Accepts either an ISBN (10 or 13 digit) or an Open Library work ID
        (e.g. "OL45804W"). Fetches full metadata including description,
        subjects, number of pages, and cover images.

        Args:
            isbn_or_olid: An ISBN-10, ISBN-13, or Open Library work ID.

        Returns:
            Book details including title, description, subjects, number of
            pages, authors, cover images, and links.
        """
        identifier = isbn_or_olid.strip()

        # Determine if this looks like an ISBN (all digits, optionally ending in X)
        clean = identifier.replace("-", "")
        is_isbn = clean.replace("X", "").replace("x", "").isdigit() and len(clean) in (10, 13)

        if is_isbn:
            # Use the ISBN bibkeys API to resolve to an edition, then get the work
            bibkey = f"ISBN:{clean}"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{BASE_URL}/api/books.json",
                    params={
                        "bibkeys": bibkey,
                        "format": "json",
                        "jscmd": "data",
                    },
                )
                resp.raise_for_status()
                bib_data = resp.json()

            if bibkey not in bib_data:
                return {"error": f"No book found for ISBN {clean}"}

            edition_info = bib_data[bibkey]

            # Also fetch the editions API for page count
            editions_data = await _get(f"/isbn/{clean}.json")
            work_key = None
            for w in editions_data.get("works", []):
                work_key = w.get("key")
                break

            # Fetch the work for description and subjects
            work_data = {}
            if work_key:
                work_data = await _get(f"{work_key}.json")

            description = work_data.get("description") or editions_data.get("description")
            if isinstance(description, dict):
                description = description.get("value", "")

            # Resolve authors
            authors = []
            for a in edition_info.get("authors", []):
                authors.append(a.get("name"))

            subjects = work_data.get("subjects", [])

            cover_ids = editions_data.get("covers", [])
            covers = [
                f"{COVERS_URL}/b/id/{cid}-M.jpg" for cid in cover_ids[:3]
            ]
            if not covers:
                # Fall back to ISBN-based cover
                covers = [f"{COVERS_URL}/b/isbn/{clean}-M.jpg"]

            return {
                "title": edition_info.get("title"),
                "isbn": clean,
                "olid": (work_key or "").replace("/works/", ""),
                "description": description,
                "subjects": subjects[:20],
                "number_of_pages": editions_data.get("number_of_pages") or edition_info.get("number_of_pages"),
                "authors": authors,
                "publish_date": editions_data.get("publish_date"),
                "publishers": edition_info.get("publishers", []),
                "covers": covers,
                "url": f"https://openlibrary.org/isbn/{clean}",
            }
        else:
            # Treat as Open Library work ID
            olid = identifier.removeprefix("/works/")
            data = await _get(f"/works/{olid}.json")

            description = data.get("description")
            if isinstance(description, dict):
                description = description.get("value", "")

            subjects = data.get("subjects", [])

            # Fetch first edition for page count
            editions_resp = await _get(
                f"/works/{olid}/editions.json", params={"limit": 1}
            )
            first_edition = {}
            if editions_resp.get("entries"):
                first_edition = editions_resp["entries"][0]

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
                "number_of_pages": first_edition.get("number_of_pages"),
                "authors": authors,
                "first_publish_date": data.get("first_publish_date"),
                "covers": [
                    f"{COVERS_URL}/b/id/{cid}-M.jpg"
                    for cid in (data.get("covers") or [])[:3]
                ],
                "links": [
                    {"title": link.get("title"), "url": link.get("url")}
                    for link in (data.get("links") or [])
                ],
                "url": f"https://openlibrary.org/works/{olid}",
            }

    @mcp.tool()
    async def author(name: str) -> dict:
        """Look up an author on Open Library by name.

        Returns the author's biography and a list of their works.

        Args:
            name: Author name to search for.

        Returns:
            Author bio (including birth/death dates and personal details)
            plus a list of their works with title, first publish year, and
            cover image.
        """
        # Search for the author
        search_data = await _get("/search/authors.json", params={"q": name})
        docs = search_data.get("docs", [])
        if not docs:
            return {"error": f"No author found for: {name}"}

        # Use the top match
        top = docs[0]
        author_key = top.get("key")

        # Fetch full author record for bio
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
            work_olid = entry.get("key", "").replace("/works/", "")
            cover_ids = entry.get("covers", [])
            cover_url = (
                f"{COVERS_URL}/b/id/{cover_ids[0]}-M.jpg"
                if cover_ids and cover_ids[0] != -1
                else None
            )
            works.append(
                {
                    "title": entry.get("title"),
                    "olid": work_olid,
                    "first_publish_year": entry.get("first_publish_date"),
                    "cover": cover_url,
                }
            )

        photos = author_data.get("photos", [])
        photo_url = (
            f"{COVERS_URL}/a/id/{photos[0]}-M.jpg"
            if photos and photos[0] != -1
            else None
        )

        return {
            "name": author_data.get("name"),
            "key": author_key,
            "bio": bio,
            "birth_date": author_data.get("birth_date"),
            "death_date": author_data.get("death_date"),
            "photo": photo_url,
            "alternate_names": author_data.get("alternate_names", []),
            "work_count": top.get("work_count"),
            "works": works,
            "url": f"https://openlibrary.org/authors/{author_key}",
        }
