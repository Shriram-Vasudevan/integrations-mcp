"""Resend provider wrapping the Resend REST API (api.resend.com)."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

RESEND_API_BASE = "https://api.resend.com"


def _get_key() -> str:
    """Return the Resend API key from environment."""
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        raise RuntimeError("RESEND_API_KEY environment variable is not set")
    return key


def _headers() -> dict:
    """Return standard request headers with Bearer auth."""
    return {
        "Authorization": f"Bearer {_get_key()}",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, **kwargs) -> dict | list:
    """Make an authenticated request to the Resend REST API."""
    url = f"{RESEND_API_BASE}/{path.lstrip('/')}"
    resp = httpx.request(
        method,
        url,
        headers=_headers(),
        timeout=30,
        **kwargs,
    )
    resp.raise_for_status()
    if resp.status_code == 204 or not resp.content:
        return {}
    return resp.json()


def register(mcp: FastMCP) -> None:
    """Register Resend tools with the MCP server."""

    # ── Send Email ─────────────────────────────────────────────────────

    @mcp.tool()
    def resend_send_email(
        to: list[str],
        subject: str,
        from_address: str,
        html: Optional[str] = None,
        text: Optional[str] = None,
        cc: Optional[list[str]] = None,
        bcc: Optional[list[str]] = None,
        reply_to: Optional[list[str]] = None,
        tags: Optional[list[dict]] = None,
        attachments: Optional[list[dict]] = None,
        scheduled_at: Optional[str] = None,
    ) -> dict:
        """Send an email via Resend.

        Args:
            to: List of recipient email addresses.
            subject: Email subject line.
            from_address: Sender email address (e.g. "You <you@example.com>").
            html: HTML body content (optional, provide html or text).
            text: Plain text body content (optional, provide html or text).
            cc: List of CC email addresses (optional).
            bcc: List of BCC email addresses (optional).
            reply_to: List of reply-to email addresses (optional).
            tags: List of tag dicts with "name" and "value" keys (optional).
            attachments: List of attachment objects with 'filename' and 'content'
                         (base64) keys (optional).
            scheduled_at: ISO 8601 datetime to schedule delivery (optional).

        Returns:
            Dict with the created email id.
        """
        payload: dict = {
            "from": from_address,
            "to": to,
            "subject": subject,
        }
        if html:
            payload["html"] = html
        if text:
            payload["text"] = text
        if cc:
            payload["cc"] = cc
        if bcc:
            payload["bcc"] = bcc
        if reply_to:
            payload["reply_to"] = reply_to
        if tags:
            payload["tags"] = tags
        if attachments:
            payload["attachments"] = attachments
        if scheduled_at:
            payload["scheduled_at"] = scheduled_at
        data = _request("POST", "emails", json=payload)
        return {"id": data.get("id")}

    # ── Send Batch Emails ───────────────────────────────────────────────

    @mcp.tool()
    def resend_send_batch_emails(
        emails: list[dict],
    ) -> dict:
        """Send a batch of emails via Resend in a single API call.

        Each email in the batch is an independent message with its own
        recipients, subject, and body.

        Args:
            emails: List of email dicts, each with keys: "from" (sender address),
                    "to" (list of recipient addresses), "subject", and optionally
                    "html", "text", "cc", "bcc", "reply_to", "tags",
                    "attachments", "scheduled_at".

        Returns:
            Dict with a list of result objects containing the created email id
            for each message.
        """
        data = _request("POST", "emails/batch", json=emails)
        results = []
        items = data.get("data", data) if isinstance(data, dict) else data
        if isinstance(items, list):
            for item in items:
                results.append({"id": item.get("id")})
        return {"results": results, "count": len(results)}

    # ── List Emails ────────────────────────────────────────────────────

    @mcp.tool()
    def resend_list_emails() -> dict:
        """List recent emails sent via Resend.

        Returns:
            Dict with a list of email summaries including id, from, to, subject,
            and created_at.
        """
        data = _request("GET", "emails")
        emails = []
        for e in data.get("data", []):
            emails.append({
                "id": e.get("id"),
                "from": e.get("from"),
                "to": e.get("to"),
                "subject": e.get("subject"),
                "created_at": e.get("created_at"),
            })
        return {"emails": emails}

    # ── Get Email ──────────────────────────────────────────────────────

    @mcp.tool()
    def resend_get_email(email_id: str) -> dict:
        """Retrieve a specific email by ID.

        Args:
            email_id: The email ID to retrieve.

        Returns:
            Full email details including id, from, to, subject, html, text,
            status, and timestamps.
        """
        e = _request("GET", f"emails/{email_id}")
        return {
            "id": e.get("id"),
            "from": e.get("from"),
            "to": e.get("to"),
            "subject": e.get("subject"),
            "html": e.get("html"),
            "text": e.get("text"),
            "cc": e.get("cc"),
            "bcc": e.get("bcc"),
            "reply_to": e.get("reply_to"),
            "created_at": e.get("created_at"),
            "last_event": e.get("last_event"),
        }

    # ── List Domains ───────────────────────────────────────────────────

    @mcp.tool()
    def resend_list_domains() -> dict:
        """List all sending domains configured in Resend.

        Returns:
            Dict with a list of domains including id, name, status, region,
            and created_at.
        """
        data = _request("GET", "domains")
        domains = []
        for d in data.get("data", []):
            domains.append({
                "id": d.get("id"),
                "name": d.get("name"),
                "status": d.get("status"),
                "region": d.get("region"),
                "created_at": d.get("created_at"),
            })
        return {"domains": domains}

    # ── Verify Domain ─────────────────────────────────────────────────

    @mcp.tool()
    def resend_verify_domain(domain_id: str) -> dict:
        """Trigger DNS verification for a sending domain in Resend.

        After adding a domain, call this to ask Resend to re-check the DNS
        records and update the domain's verification status.

        Args:
            domain_id: The domain ID to verify.

        Returns:
            Dict confirming the verification was initiated, including the
            domain id and updated status.
        """
        data = _request("POST", f"domains/{domain_id}/verify")
        return {
            "id": data.get("id", domain_id),
            "status": data.get("status", "verification_started"),
            "message": "Domain verification initiated",
        }

    # ── Get Domain ─────────────────────────────────────────────────────

    @mcp.tool()
    def resend_get_domain(domain_id: str) -> dict:
        """Retrieve a specific sending domain by ID.

        Args:
            domain_id: The domain ID to retrieve.

        Returns:
            Domain details including id, name, status, region, and DNS records.
        """
        data = _request("GET", f"domains/{domain_id}")
        records = []
        for r in data.get("records", []):
            records.append({
                "record": r.get("record"),
                "name": r.get("name"),
                "type": r.get("type"),
                "ttl": r.get("ttl"),
                "status": r.get("status"),
                "value": r.get("value"),
                "priority": r.get("priority"),
            })
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "status": data.get("status"),
            "region": data.get("region"),
            "created_at": data.get("created_at"),
            "records": records,
        }
