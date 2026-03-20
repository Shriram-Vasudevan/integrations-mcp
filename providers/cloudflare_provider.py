"""Cloudflare provider using the official cloudflare Python SDK.

Requires CLOUDFLARE_API_TOKEN environment variable.
"""

import os
from typing import Optional

import cloudflare
from mcp.server.fastmcp import FastMCP

NOT_GIVEN = cloudflare.NOT_GIVEN


def _get_client() -> cloudflare.Cloudflare:
    """Return an authenticated Cloudflare SDK client."""
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not token:
        raise RuntimeError("CLOUDFLARE_API_TOKEN environment variable is not set")
    return cloudflare.Cloudflare(api_token=token)


def register(mcp: FastMCP) -> None:
    """Register Cloudflare tools with the MCP server."""

    @mcp.tool()
    def cloudflare_list_zones(
        name: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict:
        """List Cloudflare zones (domains) in the account.

        Args:
            name: Filter by zone name / domain (optional).
            status: Filter by zone status: "active", "pending", "initializing", "moved" (optional).
            page: Page number for pagination (default 1).
            per_page: Number of zones per page (default 50, max 50).

        Returns:
            List of zones with id, name, status, name servers, and plan info.
        """
        cf = _get_client()
        result_page = cf.zones.list(
            name=name if name else NOT_GIVEN,
            status=status if status else NOT_GIVEN,
            page=page,
            per_page=min(per_page, 50),
        )
        zones = []
        for z in result_page:
            zones.append({
                "id": z.id,
                "name": z.name,
                "status": z.status,
                "paused": z.paused,
                "name_servers": list(z.name_servers) if z.name_servers else [],
                "plan": z.plan.name if z.plan else "",
                "created_on": str(z.created_on) if z.created_on else "",
                "modified_on": str(z.modified_on) if z.modified_on else "",
            })
        return {"zones": zones, "count": len(zones)}

    @mcp.tool()
    def cloudflare_get_zone(zone_id: str) -> dict:
        """Get details of a specific Cloudflare zone.

        Args:
            zone_id: The zone ID to retrieve.

        Returns:
            Zone details including name, status, name servers, plan, and account.
        """
        cf = _get_client()
        z = cf.zones.get(zone_id=zone_id)
        return {
            "id": z.id,
            "name": z.name,
            "status": z.status,
            "paused": z.paused,
            "name_servers": list(z.name_servers) if z.name_servers else [],
            "original_name_servers": list(z.original_name_servers) if z.original_name_servers else [],
            "plan": z.plan.name if z.plan else "",
            "account": z.account.name if z.account else "",
            "created_on": str(z.created_on) if z.created_on else "",
            "modified_on": str(z.modified_on) if z.modified_on else "",
        }

    @mcp.tool()
    def cloudflare_list_dns_records(
        zone_id: str,
        record_type: Optional[str] = None,
        name: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
    ) -> dict:
        """List DNS records for a Cloudflare zone.

        Args:
            zone_id: The zone ID to list records for.
            record_type: Filter by DNS record type: "A", "AAAA", "CNAME", "MX", "TXT", "NS", "SRV", etc. (optional).
            name: Filter by record name (optional).
            page: Page number for pagination (default 1).
            per_page: Number of records per page (default 100, max 100).

        Returns:
            List of DNS records with id, type, name, content, TTL, and proxy status.
        """
        cf = _get_client()
        result_page = cf.dns.records.list(
            zone_id=zone_id,
            type=record_type if record_type else NOT_GIVEN,
            name=name if name else NOT_GIVEN,
            page=page,
            per_page=min(per_page, 100),
        )
        records = []
        for r in result_page:
            records.append({
                "id": r.id,
                "type": r.type,
                "name": r.name,
                "content": r.content,
                "ttl": r.ttl,
                "proxied": r.proxied,
                "priority": getattr(r, "priority", None),
                "created_on": str(r.created_on) if r.created_on else "",
                "modified_on": str(r.modified_on) if r.modified_on else "",
            })
        return {"records": records, "count": len(records)}

    @mcp.tool()
    def cloudflare_create_dns_record(
        zone_id: str,
        record_type: str,
        name: str,
        content: str,
        ttl: int = 1,
        proxied: bool = False,
        priority: Optional[int] = None,
    ) -> dict:
        """Create a new DNS record in a Cloudflare zone.

        Args:
            zone_id: The zone ID to create the record in.
            record_type: DNS record type: "A", "AAAA", "CNAME", "MX", "TXT", "NS", "SRV", etc.
            name: DNS record name (e.g. "example.com" or "sub.example.com").
            content: DNS record content (e.g. IP address for A records, target for CNAME).
            ttl: Time to live in seconds (1 = automatic, default 1).
            proxied: Whether the record is proxied through Cloudflare (default false).
            priority: Priority for MX/SRV records (optional, required for MX).

        Returns:
            Created DNS record with id, type, name, and content.
        """
        cf = _get_client()
        r = cf.dns.records.create(
            zone_id=zone_id,
            type=record_type,
            name=name,
            content=content,
            ttl=ttl,
            proxied=proxied,
            priority=priority if priority is not None else NOT_GIVEN,
        )
        return {
            "id": r.id,
            "type": r.type,
            "name": r.name,
            "content": r.content,
            "ttl": r.ttl,
            "proxied": r.proxied,
            "created_on": str(r.created_on) if r.created_on else "",
        }

    @mcp.tool()
    def cloudflare_update_dns_record(
        zone_id: str,
        record_id: str,
        record_type: str,
        name: str,
        content: str,
        ttl: int = 1,
        proxied: bool = False,
        priority: Optional[int] = None,
    ) -> dict:
        """Update an existing DNS record in a Cloudflare zone.

        Args:
            zone_id: The zone ID containing the record.
            record_id: The DNS record ID to update.
            record_type: DNS record type: "A", "AAAA", "CNAME", "MX", "TXT", etc.
            name: DNS record name.
            content: DNS record content.
            ttl: Time to live in seconds (1 = automatic, default 1).
            proxied: Whether the record is proxied through Cloudflare (default false).
            priority: Priority for MX/SRV records (optional).

        Returns:
            Updated DNS record with id, type, name, and content.
        """
        cf = _get_client()
        r = cf.dns.records.update(
            dns_record_id=record_id,
            zone_id=zone_id,
            type=record_type,
            name=name,
            content=content,
            ttl=ttl,
            proxied=proxied,
            priority=priority if priority is not None else NOT_GIVEN,
        )
        return {
            "id": r.id,
            "type": r.type,
            "name": r.name,
            "content": r.content,
            "ttl": r.ttl,
            "proxied": r.proxied,
            "modified_on": str(r.modified_on) if r.modified_on else "",
        }

    @mcp.tool()
    def cloudflare_delete_dns_record(zone_id: str, record_id: str) -> dict:
        """Delete a DNS record from a Cloudflare zone.

        Args:
            zone_id: The zone ID containing the record.
            record_id: The DNS record ID to delete.

        Returns:
            Confirmation with the deleted record ID.
        """
        cf = _get_client()
        result = cf.dns.records.delete(dns_record_id=record_id, zone_id=zone_id)
        return {
            "id": result.id if result else record_id,
            "deleted": True,
        }

    @mcp.tool()
    def cloudflare_purge_cache(
        zone_id: str,
        purge_everything: bool = False,
        files: Optional[str] = None,
        tags: Optional[str] = None,
        hosts: Optional[str] = None,
    ) -> dict:
        """Purge cached content for a Cloudflare zone.

        Args:
            zone_id: The zone ID to purge cache for.
            purge_everything: Purge all cached files (default false). If true, other filters are ignored.
            files: Comma-separated list of URLs to purge (optional, e.g. "https://example.com/style.css,https://example.com/app.js").
            tags: Comma-separated list of cache tags to purge (optional, Enterprise only).
            hosts: Comma-separated list of hostnames to purge (optional, Enterprise only).

        Returns:
            Purge operation result with purge ID.
        """
        if not purge_everything and not files and not tags and not hosts:
            return {"error": "Must specify purge_everything=true, or provide files, tags, or hosts to purge."}

        cf = _get_client()
        result = cf.cache.purge(
            zone_id=zone_id,
            purge_everything=purge_everything if purge_everything else NOT_GIVEN,
            files=[f.strip() for f in files.split(",")] if files else NOT_GIVEN,
            tags=[t.strip() for t in tags.split(",")] if tags else NOT_GIVEN,
            hosts=[h.strip() for h in hosts.split(",")] if hosts else NOT_GIVEN,
        )
        return {
            "id": result.id if result else "",
            "success": True,
        }
