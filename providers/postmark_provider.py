"""Postmark provider wrapping the Postmark API (api.postmarkapp.com)."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

POSTMARK_API_BASE = "https://api.postmarkapp.com"


def _get_token() -> str:
    """Return the Postmark server token from environment."""
    token = os.environ.get("POSTMARK_SERVER_TOKEN")
    if not token:
        raise RuntimeError("POSTMARK_SERVER_TOKEN environment variable is not set")
    return token


def _headers() -> dict:
    """Return standard request headers with token auth."""
    return {
        "X-Postmark-Server-Token": _get_token(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _request(method: str, path: str, **kwargs) -> dict | list:
    """Make an authenticated request to the Postmark API."""
    url = f"{POSTMARK_API_BASE}/{path.lstrip('/')}"
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
    """Register Postmark tools with the MCP server."""

    # ── Send Email ─────────────────────────────────────────────────────

    @mcp.tool()
    def postmark_send_email(
        to: str,
        subject: str,
        from_address: str,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        reply_to: Optional[str] = None,
        tag: Optional[str] = None,
        track_opens: bool = True,
        track_links: Optional[str] = None,
        message_stream: Optional[str] = None,
        attachments: Optional[list[dict]] = None,
    ) -> dict:
        """Send a single email via Postmark.

        Args:
            to: Recipient email address(es), comma-separated for multiple.
            subject: Email subject line.
            from_address: Sender email address (e.g. "sender@example.com").
            html_body: HTML body content (optional, provide html_body or text_body).
            text_body: Plain text body content (optional).
            cc: CC email address(es), comma-separated (optional).
            bcc: BCC email address(es), comma-separated (optional).
            reply_to: Reply-to email address (optional).
            tag: Tag for categorizing the message (optional).
            track_opens: Whether to track email opens (default true).
            track_links: Link tracking mode — "None", "HtmlAndText",
                         "HtmlOnly", "TextOnly" (optional).
            message_stream: Message stream ID — e.g. "outbound" or
                            "broadcasts" (optional, defaults to "outbound").
            attachments: List of attachment dicts with "Name", "Content" (base64),
                         and "ContentType" keys (optional).

        Returns:
            Dict with MessageID, To, SubmittedAt, and ErrorCode.
        """
        payload: dict = {
            "From": from_address,
            "To": to,
            "Subject": subject,
            "TrackOpens": track_opens,
        }
        if html_body:
            payload["HtmlBody"] = html_body
        if text_body:
            payload["TextBody"] = text_body
        if cc:
            payload["Cc"] = cc
        if bcc:
            payload["Bcc"] = bcc
        if reply_to:
            payload["ReplyTo"] = reply_to
        if tag:
            payload["Tag"] = tag
        if track_links:
            payload["TrackLinks"] = track_links
        if message_stream:
            payload["MessageStream"] = message_stream
        if attachments:
            payload["Attachments"] = attachments

        data = _request("POST", "email", json=payload)
        return {
            "message_id": data.get("MessageID"),
            "to": data.get("To"),
            "submitted_at": data.get("SubmittedAt"),
            "error_code": data.get("ErrorCode"),
            "message": data.get("Message"),
        }

    # ── Send Batch ─────────────────────────────────────────────────────

    @mcp.tool()
    def postmark_send_batch(
        messages: list[dict],
    ) -> dict:
        """Send a batch of emails via Postmark in a single API call (max 500).

        Args:
            messages: List of message dicts, each with keys: From, To, Subject,
                      and optionally HtmlBody, TextBody, Cc, Bcc, ReplyTo, Tag,
                      MessageStream, TrackOpens, TrackLinks, Attachments.

        Returns:
            Dict with a list of result objects containing MessageID, To,
            SubmittedAt, and ErrorCode for each message.
        """
        data = _request("POST", "email/batch", json=messages)
        results = []
        items = data if isinstance(data, list) else []
        for item in items:
            results.append({
                "message_id": item.get("MessageID"),
                "to": item.get("To"),
                "submitted_at": item.get("SubmittedAt"),
                "error_code": item.get("ErrorCode"),
                "message": item.get("Message"),
            })
        return {"results": results}

    # ── Message Streams ────────────────────────────────────────────────

    @mcp.tool()
    def postmark_get_message_stream(stream_id: str) -> dict:
        """Get details of a specific message stream.

        Args:
            stream_id: The message stream ID (e.g. "outbound", "inbound",
                       "broadcasts", or a custom stream ID).

        Returns:
            Stream details including ID, Name, Description, MessageStreamType,
            and timestamps.
        """
        data = _request("GET", f"message-streams/{stream_id}")
        return {
            "id": data.get("ID"),
            "server_id": data.get("ServerID"),
            "name": data.get("Name"),
            "description": data.get("Description"),
            "message_stream_type": data.get("MessageStreamType"),
            "created_at": data.get("CreatedAt"),
            "updated_at": data.get("UpdatedAt"),
            "archived_at": data.get("ArchivedAt"),
        }

    @mcp.tool()
    def postmark_list_message_streams(
        message_stream_type: Optional[str] = None,
        include_archived: bool = False,
    ) -> dict:
        """List message streams for the server.

        Args:
            message_stream_type: Filter by type — "Transactional", "Broadcasts",
                                 or "Inbound" (optional, returns all if omitted).
            include_archived: Whether to include archived streams (default false).

        Returns:
            Dict with a list of message stream objects.
        """
        params: dict = {"IncludeArchivedStreams": str(include_archived).lower()}
        if message_stream_type:
            params["MessageStreamType"] = message_stream_type

        data = _request("GET", "message-streams", params=params)
        streams = []
        for s in data.get("MessageStreams", []):
            streams.append({
                "id": s.get("ID"),
                "name": s.get("Name"),
                "description": s.get("Description"),
                "message_stream_type": s.get("MessageStreamType"),
                "created_at": s.get("CreatedAt"),
                "updated_at": s.get("UpdatedAt"),
            })
        return {"streams": streams}

    # ── Bounces ────────────────────────────────────────────────────────

    @mcp.tool()
    def postmark_list_bounces(
        count: int = 50,
        offset: int = 0,
        bounce_type: Optional[str] = None,
        inactive: Optional[bool] = None,
        email_filter: Optional[str] = None,
        tag: Optional[str] = None,
        message_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        message_stream: Optional[str] = None,
    ) -> dict:
        """List bounced messages from Postmark.

        Args:
            count: Number of bounces to return (1-500, default 50).
            offset: Pagination offset (default 0).
            bounce_type: Filter by bounce type — e.g. "HardBounce",
                         "SoftBounce", "SpamComplaint" (optional).
            inactive: Filter by inactive status (optional).
            email_filter: Filter by full or partial email address (optional).
            tag: Filter by tag (optional).
            message_id: Filter by original message ID (optional).
            from_date: Start date filter in YYYY-MM-DD format (optional).
            to_date: End date filter in YYYY-MM-DD format (optional).
            message_stream: Filter by message stream ID (optional).

        Returns:
            Dict with TotalCount and a list of bounce objects.
        """
        params: dict = {
            "count": min(max(1, count), 500),
            "offset": offset,
        }
        if bounce_type:
            params["type"] = bounce_type
        if inactive is not None:
            params["inactive"] = str(inactive).lower()
        if email_filter:
            params["emailFilter"] = email_filter
        if tag:
            params["tag"] = tag
        if message_id:
            params["messageID"] = message_id
        if from_date:
            params["fromdate"] = from_date
        if to_date:
            params["todate"] = to_date
        if message_stream:
            params["messagestream"] = message_stream

        data = _request("GET", "bounces", params=params)
        bounces = []
        for b in data.get("Bounces", []):
            bounces.append({
                "id": b.get("ID"),
                "type": b.get("Type"),
                "type_code": b.get("TypeCode"),
                "name": b.get("Name"),
                "tag": b.get("Tag"),
                "message_id": b.get("MessageID"),
                "server_id": b.get("ServerID"),
                "message_stream": b.get("MessageStream"),
                "description": b.get("Description"),
                "details": b.get("Details"),
                "email": b.get("Email"),
                "from": b.get("From"),
                "bounced_at": b.get("BouncedAt"),
                "can_activate": b.get("CanActivate"),
                "subject": b.get("Subject"),
                "inactive": b.get("Inactive"),
            })
        return {
            "total_count": data.get("TotalCount", 0),
            "bounces": bounces,
        }

    @mcp.tool()
    def postmark_get_bounce(bounce_id: int) -> dict:
        """Retrieve a single bounce by ID.

        Args:
            bounce_id: The bounce ID to retrieve.

        Returns:
            Bounce details including type, email, description, and timestamps.
        """
        b = _request("GET", f"bounces/{bounce_id}")
        return {
            "id": b.get("ID"),
            "type": b.get("Type"),
            "type_code": b.get("TypeCode"),
            "name": b.get("Name"),
            "tag": b.get("Tag"),
            "message_id": b.get("MessageID"),
            "server_id": b.get("ServerID"),
            "message_stream": b.get("MessageStream"),
            "description": b.get("Description"),
            "details": b.get("Details"),
            "email": b.get("Email"),
            "from": b.get("From"),
            "bounced_at": b.get("BouncedAt"),
            "can_activate": b.get("CanActivate"),
            "subject": b.get("Subject"),
            "inactive": b.get("Inactive"),
            "content": b.get("Content"),
        }

    # ── Stats ──────────────────────────────────────────────────────────

    @mcp.tool()
    def postmark_get_stats(
        stat_type: str = "outbound/overview",
        tag: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        message_stream: Optional[str] = None,
    ) -> dict:
        """Retrieve sending statistics from Postmark.

        Args:
            stat_type: Type of stats to retrieve — "outbound/overview" (default),
                       "outbound/sends", "outbound/bounces", "outbound/spam",
                       "outbound/tracked", "outbound/opens", "outbound/clicks",
                       or "outbound/platform".
            tag: Filter stats by tag (optional).
            from_date: Start date in YYYY-MM-DD format (optional).
            to_date: End date in YYYY-MM-DD format (optional).
            message_stream: Filter by message stream ID (optional).

        Returns:
            Dict with the requested statistics. Shape varies by stat_type.
        """
        params: dict = {}
        if tag:
            params["tag"] = tag
        if from_date:
            params["fromdate"] = from_date
        if to_date:
            params["todate"] = to_date
        if message_stream:
            params["messagestream"] = message_stream

        data = _request("GET", f"stats/{stat_type}", params=params)
        return data if isinstance(data, dict) else {"data": data}

    @mcp.tool()
    def postmark_get_outbound_overview(
        tag: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        message_stream: Optional[str] = None,
    ) -> dict:
        """Get a high-level overview of outbound sending statistics.

        Args:
            tag: Filter stats by tag (optional).
            from_date: Start date in YYYY-MM-DD format (optional).
            to_date: End date in YYYY-MM-DD format (optional).
            message_stream: Filter by message stream ID (optional).

        Returns:
            Dict with Sent, Bounced, SMTPApiErrors, BounceRate,
            SpamComplaints, SpamComplaintsRate, Opens, UniqueOpens,
            Tracked, WithClientRecorded, WithPlatformRecorded,
            WithReadTimeRecorded, TotalClicks, UniqueLinksClicked.
        """
        params: dict = {}
        if tag:
            params["tag"] = tag
        if from_date:
            params["fromdate"] = from_date
        if to_date:
            params["todate"] = to_date
        if message_stream:
            params["messagestream"] = message_stream

        data = _request("GET", "stats/outbound", params=params)
        return {
            "sent": data.get("Sent", 0),
            "bounced": data.get("Bounced", 0),
            "smtp_api_errors": data.get("SMTPApiErrors", 0),
            "bounce_rate": data.get("BounceRate", 0),
            "spam_complaints": data.get("SpamComplaints", 0),
            "spam_complaints_rate": data.get("SpamComplaintsRate", 0),
            "opens": data.get("Opens", 0),
            "unique_opens": data.get("UniqueOpens", 0),
            "tracked": data.get("Tracked", 0),
            "total_clicks": data.get("TotalClicks", 0),
            "unique_links_clicked": data.get("UniqueLinksClicked", 0),
        }
