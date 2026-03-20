"""arXiv provider for searching papers and fetching metadata via the arXiv API."""

import xml.etree.ElementTree as ET
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

ARXIV_API_BASE = "http://export.arxiv.org/api/query"

# Atom / OpenSearch namespaces used in arXiv API responses
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def _parse_entries(xml_text: str) -> list[dict]:
    """Parse Atom XML from arXiv and return a list of paper dicts."""
    root = ET.fromstring(xml_text)
    entries = root.findall("atom:entry", NS)
    papers = []
    for entry in entries:
        # Extract arXiv ID from the <id> URL
        raw_id = entry.findtext("atom:id", "", NS)
        arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id

        title = entry.findtext("atom:title", "", NS).strip().replace("\n", " ")
        abstract = entry.findtext("atom:summary", "", NS).strip().replace("\n", " ")
        published = entry.findtext("atom:published", "", NS)
        updated = entry.findtext("atom:updated", "", NS)

        authors = [
            a.findtext("atom:name", "", NS)
            for a in entry.findall("atom:author", NS)
        ]

        # Find PDF link
        pdf_link = ""
        for link in entry.findall("atom:link", NS):
            if link.get("title") == "pdf":
                pdf_link = link.get("href", "")
                break

        # Primary category
        primary_cat_el = entry.find("arxiv:primary_category", NS)
        primary_category = primary_cat_el.get("term", "") if primary_cat_el is not None else ""

        categories = [
            c.get("term", "")
            for c in entry.findall("atom:category", NS)
        ]

        # Optional DOI and journal ref
        doi = entry.findtext("arxiv:doi", "", NS)
        journal_ref = entry.findtext("arxiv:journal_ref", "", NS)
        comment = entry.findtext("arxiv:comment", "", NS)

        papers.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "published": published,
            "updated": updated,
            "pdf_url": pdf_link,
            "primary_category": primary_category,
            "categories": categories,
            "doi": doi or None,
            "journal_ref": journal_ref or None,
            "comment": comment or None,
        })
    return papers


async def _query_arxiv(params: dict) -> str:
    """Execute a request against the arXiv API and return raw XML."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(ARXIV_API_BASE, params=params)
        resp.raise_for_status()
        return resp.text


def register(mcp: FastMCP) -> None:
    """Register arXiv tools with the MCP server."""

    @mcp.tool()
    async def arxiv_search(
        query: str,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sort_by: str = "relevance",
        sort_order: str = "descending",
        max_results: int = 10,
        start: int = 0,
    ) -> dict:
        """Search arXiv papers by query, category, and date range.

        Args:
            query: Search query string. Supports arXiv search syntax
                   (e.g. "transformer attention", "au:Hinton", "ti:neural").
            category: arXiv category to restrict search (e.g. "cs.AI", "cs.LG",
                      "math.CO", "physics.hep-th"). Optional.
            start_date: Filter papers submitted on or after this date (YYYYMMDD format,
                        e.g. "20240101"). Optional.
            end_date: Filter papers submitted on or before this date (YYYYMMDD format,
                      e.g. "20240331"). Optional.
            sort_by: Sort criterion — "relevance", "lastUpdatedDate", or
                     "submittedDate" (default "relevance").
            sort_order: Sort direction — "ascending" or "descending" (default "descending").
            max_results: Maximum number of results to return, 1–100 (default 10).
            start: Offset for pagination (default 0).

        Returns:
            Dictionary with total_results count and a list of paper objects
            containing arxiv_id, title, authors, abstract, pdf_url,
            published date, categories, and more.
        """
        # Build the search query
        search_parts = []
        if query:
            search_parts.append(f"all:{query}")
        if category:
            search_parts.append(f"cat:{category}")
        if start_date or end_date:
            sd = start_date or "190001010000"
            ed = end_date or "209912312359"
            # Append time components if not present
            if len(sd) == 8:
                sd += "0000"
            if len(ed) == 8:
                ed += "2359"
            search_parts.append(f"submittedDate:[{sd} TO {ed}]")

        search_query = " AND ".join(search_parts) if search_parts else "all:*"

        params = {
            "search_query": search_query,
            "sortBy": sort_by,
            "sortOrder": sort_order,
            "start": start,
            "max_results": min(max(max_results, 1), 100),
        }

        xml_text = await _query_arxiv(params)
        papers = _parse_entries(xml_text)

        # Extract total results from OpenSearch metadata
        root = ET.fromstring(xml_text)
        total = root.findtext("opensearch:totalResults", "0", NS)

        return {
            "total_results": int(total),
            "start": start,
            "papers": papers,
            "count": len(papers),
        }

    @mcp.tool()
    async def arxiv_get_paper(arxiv_id: str) -> dict:
        """Fetch metadata for a specific arXiv paper by its ID.

        Args:
            arxiv_id: The arXiv paper ID (e.g. "2301.07041", "2301.07041v1",
                      or legacy format "hep-th/9905111").

        Returns:
            Paper metadata including title, authors, abstract, pdf_url,
            published/updated dates, categories, DOI, and journal reference.
        """
        params = {"id_list": arxiv_id, "max_results": 1}
        xml_text = await _query_arxiv(params)
        papers = _parse_entries(xml_text)

        if not papers:
            return {"error": f"No paper found with ID: {arxiv_id}"}

        return {"paper": papers[0]}

    @mcp.tool()
    async def arxiv_get_papers(arxiv_ids: str) -> dict:
        """Fetch metadata for multiple arXiv papers by their IDs in a single request.

        Args:
            arxiv_ids: Comma-separated arXiv paper IDs
                       (e.g. "2301.07041,2301.07042,hep-th/9905111").

        Returns:
            List of paper metadata objects for each requested ID.
        """
        clean_ids = ",".join(i.strip() for i in arxiv_ids.split(",") if i.strip())
        params = {"id_list": clean_ids, "max_results": len(clean_ids.split(","))}
        xml_text = await _query_arxiv(params)
        papers = _parse_entries(xml_text)

        return {"papers": papers, "count": len(papers)}
