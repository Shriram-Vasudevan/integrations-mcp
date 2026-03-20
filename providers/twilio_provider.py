"""Twilio provider using the official Twilio Python SDK.

Requires TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables.
"""

import asyncio
import os
from functools import partial
from typing import Optional

from mcp.server.fastmcp import FastMCP

_client_cache: dict[str, object] = {}


def _get_client():
    """Return a cached Twilio REST client."""
    from twilio.rest import Client

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        raise RuntimeError(
            "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables must be set"
        )
    key = f"{account_sid}:{auth_token}"
    if key not in _client_cache:
        _client_cache[key] = Client(account_sid, auth_token)
    return _client_cache[key]


async def _run_sync(func, *args, **kwargs):
    """Run a synchronous Twilio SDK call in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


def register(mcp: FastMCP) -> None:
    """Register Twilio tools with the MCP server."""

    # ── SMS ──────────────────────────────────────────────────────────────

    @mcp.tool()
    async def twilio_send_sms(
        to: str,
        body: str,
        from_: Optional[str] = None,
        status_callback: Optional[str] = None,
    ) -> dict:
        """Send an SMS message via Twilio.

        Args:
            to: Destination phone number in E.164 format (e.g. "+15551234567").
            body: Text content of the SMS (max 1600 characters).
            from_: Sender phone number in E.164 format. If omitted, uses the
                   first available number on the account.
            status_callback: URL for Twilio to POST status updates to.

        Returns:
            Message details including sid, status, date_sent, and price.
        """
        client = _get_client()

        if not from_:
            numbers = await _run_sync(
                lambda: list(client.incoming_phone_numbers.list(limit=1))
            )
            if not numbers:
                raise RuntimeError("No phone numbers on this Twilio account")
            from_ = numbers[0].phone_number

        kwargs = {"to": to, "body": body, "from_": from_}
        if status_callback:
            kwargs["status_callback"] = status_callback

        msg = await _run_sync(lambda: client.messages.create(**kwargs))
        return {
            "sid": msg.sid,
            "to": msg.to,
            "from": msg.from_,
            "body": msg.body,
            "status": msg.status,
            "date_sent": str(msg.date_sent) if msg.date_sent else None,
            "price": msg.price,
            "price_unit": msg.price_unit,
        }

    # ── Calls ────────────────────────────────────────────────────────────

    @mcp.tool()
    async def twilio_make_call(
        to: str,
        twiml: Optional[str] = None,
        url: Optional[str] = None,
        from_: Optional[str] = None,
        status_callback: Optional[str] = None,
        record: bool = False,
        timeout: int = 30,
    ) -> dict:
        """Initiate an outbound phone call via Twilio.

        You must provide either 'twiml' (inline TwiML markup) or 'url' (a URL
        returning TwiML) to control call behaviour.

        Args:
            to: Destination phone number in E.164 format.
            twiml: Inline TwiML markup (e.g. '<Response><Say>Hello</Say></Response>').
            url: URL that returns TwiML instructions for the call.
            from_: Caller phone number in E.164 format. If omitted, uses the first
                   available number on the account.
            status_callback: URL for Twilio to POST call status updates to.
            record: Whether to record the call (default False).
            timeout: Seconds to wait for an answer before giving up (default 30).

        Returns:
            Call details including sid, status, and from/to numbers.
        """
        if not twiml and not url:
            raise ValueError("Either 'twiml' or 'url' must be provided")

        client = _get_client()

        if not from_:
            numbers = await _run_sync(
                lambda: list(client.incoming_phone_numbers.list(limit=1))
            )
            if not numbers:
                raise RuntimeError("No phone numbers on this Twilio account")
            from_ = numbers[0].phone_number

        kwargs = {
            "to": to,
            "from_": from_,
            "record": record,
            "timeout": timeout,
        }
        if twiml:
            kwargs["twiml"] = twiml
        elif url:
            kwargs["url"] = url
        if status_callback:
            kwargs["status_callback"] = status_callback

        call = await _run_sync(lambda: client.calls.create(**kwargs))
        return {
            "sid": call.sid,
            "to": call.to,
            "from": call.from_,
            "status": call.status,
            "direction": call.direction,
            "date_created": str(call.date_created) if call.date_created else None,
        }

    # ── Messages ─────────────────────────────────────────────────────────

    @mcp.tool()
    async def twilio_list_messages(
        limit: int = 20,
        to: Optional[str] = None,
        from_: Optional[str] = None,
        date_sent_after: Optional[str] = None,
        date_sent_before: Optional[str] = None,
    ) -> dict:
        """List recent messages on the Twilio account.

        Args:
            limit: Maximum number of messages to return (1-1000, default 20).
            to: Filter by recipient phone number.
            from_: Filter by sender phone number.
            date_sent_after: ISO 8601 date — only messages sent after this date.
            date_sent_before: ISO 8601 date — only messages sent before this date.

        Returns:
            List of messages with sid, to, from, body, status, and direction.
        """
        from datetime import datetime

        kwargs: dict = {"limit": min(max(1, limit), 1000)}
        if to:
            kwargs["to"] = to
        if from_:
            kwargs["from_"] = from_
        if date_sent_after:
            kwargs["date_sent_after"] = datetime.fromisoformat(date_sent_after)
        if date_sent_before:
            kwargs["date_sent_before"] = datetime.fromisoformat(date_sent_before)

        client = _get_client()
        records = await _run_sync(
            lambda: list(client.messages.list(**kwargs))
        )
        messages = []
        for m in records:
            messages.append({
                "sid": m.sid,
                "to": m.to,
                "from": m.from_,
                "body": m.body,
                "status": m.status,
                "direction": m.direction,
                "date_sent": str(m.date_sent) if m.date_sent else None,
                "price": m.price,
            })
        return {"messages": messages, "count": len(messages)}

    @mcp.tool()
    async def twilio_get_message(sid: str) -> dict:
        """Get details of a specific Twilio message by SID.

        Args:
            sid: The message SID (e.g. "SM" followed by 32 hex characters).

        Returns:
            Full message details including sid, to, from, body, status, price,
            and error information if any.
        """
        client = _get_client()
        m = await _run_sync(lambda: client.messages(sid).fetch())
        return {
            "sid": m.sid,
            "to": m.to,
            "from": m.from_,
            "body": m.body,
            "status": m.status,
            "direction": m.direction,
            "date_sent": str(m.date_sent) if m.date_sent else None,
            "date_created": str(m.date_created) if m.date_created else None,
            "price": m.price,
            "price_unit": m.price_unit,
            "error_code": m.error_code,
            "error_message": m.error_message,
            "num_segments": m.num_segments,
            "num_media": m.num_media,
        }

    # ── Calls ────────────────────────────────────────────────────────────

    @mcp.tool()
    async def twilio_list_calls(
        limit: int = 20,
        to: Optional[str] = None,
        from_: Optional[str] = None,
        status: Optional[str] = None,
        start_time_after: Optional[str] = None,
        start_time_before: Optional[str] = None,
    ) -> dict:
        """List recent calls on the Twilio account.

        Args:
            limit: Maximum number of calls to return (1-1000, default 20).
            to: Filter by recipient phone number.
            from_: Filter by caller phone number.
            status: Filter by call status (queued, ringing, in-progress,
                    completed, busy, failed, no-answer, canceled).
            start_time_after: ISO 8601 date — only calls started after this time.
            start_time_before: ISO 8601 date — only calls started before this time.

        Returns:
            List of calls with sid, to, from, status, duration, and direction.
        """
        from datetime import datetime

        kwargs: dict = {"limit": min(max(1, limit), 1000)}
        if to:
            kwargs["to"] = to
        if from_:
            kwargs["from_"] = from_
        if status:
            kwargs["status"] = status
        if start_time_after:
            kwargs["start_time_after"] = datetime.fromisoformat(start_time_after)
        if start_time_before:
            kwargs["start_time_before"] = datetime.fromisoformat(start_time_before)

        client = _get_client()
        records = await _run_sync(
            lambda: list(client.calls.list(**kwargs))
        )
        calls = []
        for c in records:
            calls.append({
                "sid": c.sid,
                "to": c.to,
                "from": c.from_,
                "status": c.status,
                "direction": c.direction,
                "duration": c.duration,
                "start_time": str(c.start_time) if c.start_time else None,
                "end_time": str(c.end_time) if c.end_time else None,
                "price": c.price,
            })
        return {"calls": calls, "count": len(calls)}

    # ── Account Balance ──────────────────────────────────────────────────

    @mcp.tool()
    async def twilio_get_account_balance() -> dict:
        """Get the current account balance for the Twilio account.

        Returns:
            Account balance details including currency, balance, and account
            friendly name.
        """
        client = _get_client()
        account = await _run_sync(lambda: client.api.accounts(client.account_sid).fetch())
        balance_data = await _run_sync(
            lambda: client.api.accounts(client.account_sid).balance().fetch()
        )
        return {
            "account_sid": client.account_sid,
            "friendly_name": account.friendly_name,
            "status": account.status,
            "currency": balance_data.currency,
            "balance": balance_data.balance,
        }
