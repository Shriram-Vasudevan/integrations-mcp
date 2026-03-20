"""Slack provider wrapping the Slack Web API via async httpx."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

SLACK_API_BASE = "https://slack.com/api"


def _get_token() -> str:
    """Return the Slack bot token from environment."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN environment variable is not set")
    return token


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json; charset=utf-8",
    }


async def _request(method: str, slack_method: str, **kwargs) -> dict:
    """Make an authenticated request to the Slack Web API.

    Args:
        method: HTTP method (GET or POST).
        slack_method: Slack API method name (e.g. "conversations.list").
        **kwargs: Extra arguments passed to httpx (params, json, data, files, etc.).

    Returns:
        Parsed JSON response from Slack.

    Raises:
        RuntimeError: If the Slack API returns ok=false.
    """
    # For multipart uploads, don't set Content-Type (httpx sets it with boundary)
    if "files" in kwargs:
        headers = {"Authorization": f"Bearer {_get_token()}"}
    else:
        headers = _headers()

    url = f"{SLACK_API_BASE}/{slack_method}"
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=headers, timeout=30, **kwargs)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")
        return data


def register(mcp: FastMCP) -> None:
    """Register Slack tools with the MCP server."""

    @mcp.tool()
    async def slack_list_channels(
        limit: int = 100,
        cursor: Optional[str] = None,
        types: str = "public_channel",
    ) -> dict:
        """List Slack channels the bot has access to.

        Args:
            limit: Max channels to return (1-1000, default 100).
            cursor: Pagination cursor for next page of results.
            types: Comma-separated channel types (public_channel, private_channel, mpim, im).

        Returns:
            List of channels with id, name, topic, purpose, and member count.
        """
        params: dict = {"limit": min(max(1, limit), 1000), "types": types}
        if cursor:
            params["cursor"] = cursor
        data = await _request("GET", "conversations.list", params=params)
        channels = []
        for ch in data.get("channels", []):
            channels.append({
                "id": ch["id"],
                "name": ch.get("name", ""),
                "is_private": ch.get("is_private", False),
                "topic": ch.get("topic", {}).get("value", ""),
                "purpose": ch.get("purpose", {}).get("value", ""),
                "num_members": ch.get("num_members", 0),
            })
        return {
            "channels": channels,
            "next_cursor": data.get("response_metadata", {}).get("next_cursor", ""),
        }

    @mcp.tool()
    async def slack_get_channel(channel: str) -> dict:
        """Get detailed information about a Slack channel.

        Args:
            channel: Channel ID (e.g. "C01234ABCDE").

        Returns:
            Channel details including name, topic, purpose, member count, and creation date.
        """
        data = await _request("GET", "conversations.info", params={"channel": channel})
        ch = data.get("channel", {})
        return {
            "id": ch["id"],
            "name": ch.get("name", ""),
            "is_private": ch.get("is_private", False),
            "is_archived": ch.get("is_archived", False),
            "topic": ch.get("topic", {}).get("value", ""),
            "purpose": ch.get("purpose", {}).get("value", ""),
            "num_members": ch.get("num_members", 0),
            "created": ch.get("created"),
            "creator": ch.get("creator", ""),
        }

    @mcp.tool()
    async def slack_post_message(
        channel: str,
        text: str,
        blocks: Optional[str] = None,
        thread_ts: Optional[str] = None,
        unfurl_links: bool = True,
        unfurl_media: bool = True,
    ) -> dict:
        """Post a message to a Slack channel or thread.

        Args:
            channel: Channel ID or name (e.g. "C01234ABCDE" or "#general").
            text: Message text (supports Slack mrkdwn formatting). Also used as fallback for blocks.
            blocks: Optional JSON string of Block Kit blocks for rich message layouts.
            thread_ts: Parent message timestamp to reply in a thread (optional).
            unfurl_links: Whether to unfurl URLs in the message.
            unfurl_media: Whether to unfurl media URLs.

        Returns:
            Posted message details including channel, timestamp, and text.
        """
        import json as _json

        payload: dict = {
            "channel": channel,
            "text": text,
            "unfurl_links": unfurl_links,
            "unfurl_media": unfurl_media,
        }
        if blocks:
            payload["blocks"] = _json.loads(blocks) if isinstance(blocks, str) else blocks
        if thread_ts:
            payload["thread_ts"] = thread_ts
        data = await _request("POST", "chat.postMessage", json=payload)
        msg = data.get("message", {})
        return {
            "channel": data.get("channel", channel),
            "ts": msg.get("ts", ""),
            "text": msg.get("text", ""),
            "thread_ts": msg.get("thread_ts"),
        }

    @mcp.tool()
    async def slack_list_messages(
        channel: str,
        limit: int = 20,
        cursor: Optional[str] = None,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
    ) -> dict:
        """List messages (history) from a Slack channel.

        Args:
            channel: Channel ID (e.g. "C01234ABCDE").
            limit: Number of messages to return (1-1000, default 20).
            cursor: Pagination cursor for next page.
            oldest: Unix timestamp — only messages after this time.
            latest: Unix timestamp — only messages before this time.

        Returns:
            List of messages with user, text, timestamp, and thread info.
        """
        params: dict = {"channel": channel, "limit": min(max(1, limit), 1000)}
        if cursor:
            params["cursor"] = cursor
        if oldest:
            params["oldest"] = oldest
        if latest:
            params["latest"] = latest
        data = await _request("GET", "conversations.history", params=params)
        messages = []
        for msg in data.get("messages", []):
            messages.append({
                "user": msg.get("user", ""),
                "text": msg.get("text", ""),
                "ts": msg.get("ts", ""),
                "thread_ts": msg.get("thread_ts"),
                "reply_count": msg.get("reply_count", 0),
                "reactions": msg.get("reactions", []),
            })
        return {
            "channel": channel,
            "messages": messages,
            "has_more": data.get("has_more", False),
            "next_cursor": data.get("response_metadata", {}).get("next_cursor", ""),
        }

    @mcp.tool()
    async def slack_get_thread_replies(
        channel: str,
        ts: str,
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> dict:
        """Get all replies in a message thread.

        Args:
            channel: Channel ID where the thread exists.
            ts: Timestamp of the parent message (thread_ts).
            limit: Number of replies to return (1-1000, default 100).
            cursor: Pagination cursor for next page.

        Returns:
            List of thread messages including the parent and all replies.
        """
        params: dict = {"channel": channel, "ts": ts, "limit": min(max(1, limit), 1000)}
        if cursor:
            params["cursor"] = cursor
        data = await _request("GET", "conversations.replies", params=params)
        messages = []
        for msg in data.get("messages", []):
            messages.append({
                "user": msg.get("user", ""),
                "text": msg.get("text", ""),
                "ts": msg.get("ts", ""),
                "thread_ts": msg.get("thread_ts"),
                "reply_count": msg.get("reply_count", 0),
                "reactions": msg.get("reactions", []),
            })
        return {
            "channel": channel,
            "thread_ts": ts,
            "messages": messages,
            "has_more": data.get("has_more", False),
            "next_cursor": data.get("response_metadata", {}).get("next_cursor", ""),
        }

    @mcp.tool()
    async def slack_list_users(
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> dict:
        """List users in the Slack workspace.

        Args:
            limit: Max users to return (1-1000, default 100).
            cursor: Pagination cursor for next page.

        Returns:
            List of users with id, name, real name, email, and status.
        """
        params: dict = {"limit": min(max(1, limit), 1000)}
        if cursor:
            params["cursor"] = cursor
        data = await _request("GET", "users.list", params=params)
        users = []
        for u in data.get("members", []):
            profile = u.get("profile", {})
            users.append({
                "id": u["id"],
                "name": u.get("name", ""),
                "real_name": u.get("real_name", ""),
                "email": profile.get("email", ""),
                "title": profile.get("title", ""),
                "status_text": profile.get("status_text", ""),
                "status_emoji": profile.get("status_emoji", ""),
                "is_bot": u.get("is_bot", False),
                "deleted": u.get("deleted", False),
            })
        return {
            "users": users,
            "next_cursor": data.get("response_metadata", {}).get("next_cursor", ""),
        }

    @mcp.tool()
    async def slack_get_user(user: str) -> dict:
        """Get detailed info about a Slack user.

        Args:
            user: User ID (e.g. "U01234ABCDE").

        Returns:
            User profile with name, email, title, status, timezone, and avatar.
        """
        data = await _request("GET", "users.info", params={"user": user})
        u = data.get("user", {})
        profile = u.get("profile", {})
        return {
            "id": u["id"],
            "name": u.get("name", ""),
            "real_name": u.get("real_name", ""),
            "email": profile.get("email", ""),
            "title": profile.get("title", ""),
            "status_text": profile.get("status_text", ""),
            "status_emoji": profile.get("status_emoji", ""),
            "timezone": u.get("tz", ""),
            "timezone_label": u.get("tz_label", ""),
            "is_admin": u.get("is_admin", False),
            "is_bot": u.get("is_bot", False),
            "avatar_url": profile.get("image_192", ""),
        }

    @mcp.tool()
    async def slack_upload_file(
        channels: str,
        content: str,
        filename: str = "file.txt",
        title: Optional[str] = None,
        initial_comment: Optional[str] = None,
        filetype: Optional[str] = None,
    ) -> dict:
        """Upload a file to Slack channel(s).

        Args:
            channels: Comma-separated channel IDs to share the file in.
            content: Text content of the file.
            filename: Name for the file (default "file.txt").
            title: Title for the file (defaults to filename).
            initial_comment: Message to post alongside the file.
            filetype: File type identifier (e.g. "python", "json", "csv").

        Returns:
            Uploaded file info including id, name, and permalink.
        """
        form_data: dict = {
            "channels": channels,
            "filename": filename,
            "title": title or filename,
        }
        if initial_comment:
            form_data["initial_comment"] = initial_comment
        if filetype:
            form_data["filetype"] = filetype
        data = await _request(
            "POST",
            "files.upload",
            data=form_data,
            files={"content": (filename, content.encode("utf-8"))},
            timeout=60,
        )
        f = data.get("file", {})
        return {
            "id": f.get("id", ""),
            "name": f.get("name", ""),
            "title": f.get("title", ""),
            "filetype": f.get("filetype", ""),
            "size": f.get("size", 0),
            "permalink": f.get("permalink", ""),
        }

    @mcp.tool()
    async def slack_search_messages(
        query: str,
        count: int = 20,
        sort: str = "timestamp",
        sort_dir: str = "desc",
        cursor: Optional[str] = None,
    ) -> dict:
        """Search for messages across the Slack workspace.

        Note: Requires a user token with search:read scope. Bot tokens cannot use search.

        Args:
            query: Search query (supports Slack search modifiers like from:, in:, has:).
            count: Number of results to return (1-100, default 20).
            sort: Sort field — "timestamp" or "score" (default "timestamp").
            sort_dir: Sort direction — "asc" or "desc" (default "desc").
            cursor: Pagination cursor for next page.

        Returns:
            Matching messages with channel, user, text, timestamp, and permalink.
        """
        params: dict = {
            "query": query,
            "count": min(max(1, count), 100),
            "sort": sort,
            "sort_dir": sort_dir,
        }
        if cursor:
            params["cursor"] = cursor
        data = await _request("GET", "search.messages", params=params)
        msg_data = data.get("messages", {})
        matches = []
        for m in msg_data.get("matches", []):
            matches.append({
                "channel": m.get("channel", {}).get("name", ""),
                "channel_id": m.get("channel", {}).get("id", ""),
                "user": m.get("user", ""),
                "username": m.get("username", ""),
                "text": m.get("text", ""),
                "ts": m.get("ts", ""),
                "permalink": m.get("permalink", ""),
            })
        return {
            "query": query,
            "total": msg_data.get("total", 0),
            "matches": matches,
            "next_cursor": msg_data.get("pagination", {}).get("next_cursor", ""),
        }

    @mcp.tool()
    async def slack_add_reaction(
        channel: str,
        timestamp: str,
        name: str,
    ) -> dict:
        """Add a reaction emoji to a message.

        Args:
            channel: Channel ID where the message is.
            timestamp: Timestamp (ts) of the message to react to.
            name: Emoji name without colons (e.g. "thumbsup", "eyes", "rocket").

        Returns:
            Confirmation of the added reaction.
        """
        await _request("POST", "reactions.add", json={
            "channel": channel,
            "timestamp": timestamp,
            "name": name,
        })
        return {
            "channel": channel,
            "ts": timestamp,
            "reaction": name,
            "status": "added",
        }
