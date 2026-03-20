"""SendGrid provider using the sendgrid-python SDK."""

import json
import os
from typing import Optional

import sendgrid
from sendgrid.helpers.mail import (
    Bcc,
    Cc,
    Content,
    Email,
    Mail,
    Personalization,
    ReplyTo,
    To,
)
from mcp.server.fastmcp import FastMCP


def _get_client() -> sendgrid.SendGridAPIClient:
    """Return a SendGrid client configured from the SENDGRID_API_KEY env var."""
    key = os.environ.get("SENDGRID_API_KEY")
    if not key:
        raise RuntimeError("SENDGRID_API_KEY environment variable is not set")
    return sendgrid.SendGridAPIClient(api_key=key)


def register(mcp: FastMCP) -> None:
    """Register SendGrid tools with the MCP server."""

    # ── Emails ──────────────────────────────────────────────────────────

    @mcp.tool()
    def sendgrid_send_email(
        to: list[str],
        subject: str,
        from_email: str,
        html: Optional[str] = None,
        text: Optional[str] = None,
        cc: Optional[list[str]] = None,
        bcc: Optional[list[str]] = None,
        reply_to: Optional[str] = None,
        categories: Optional[list[str]] = None,
    ) -> dict:
        """Send an email via SendGrid.

        Args:
            to: List of recipient email addresses.
            subject: Email subject line.
            from_email: Sender email address.
            html: HTML body content (optional, provide html or text).
            text: Plain text body content (optional, provide html or text).
            cc: List of CC email addresses (optional).
            bcc: List of BCC email addresses (optional).
            reply_to: Reply-to email address (optional).
            categories: List of categories for tracking (optional).

        Returns:
            Dict confirming the email was accepted for delivery.
        """
        sg = _get_client()

        mail = Mail()
        mail.from_email = Email(from_email)
        mail.subject = subject

        personalization = Personalization()
        for addr in to:
            personalization.add_to(To(addr))
        if cc:
            for addr in cc:
                personalization.add_cc(Cc(addr))
        if bcc:
            for addr in bcc:
                personalization.add_bcc(Bcc(addr))
        mail.add_personalization(personalization)

        if text:
            mail.add_content(Content("text/plain", text))
        if html:
            mail.add_content(Content("text/html", html))
        if reply_to:
            mail.reply_to = ReplyTo(reply_to)
        if categories:
            for cat in categories:
                mail.add_category(cat)

        response = sg.client.mail.send.post(request_body=mail.get())
        return {
            "status": "accepted",
            "status_code": response.status_code,
            "message": "Email accepted for delivery",
        }

    @mcp.tool()
    def sendgrid_send_template_email(
        to: list[str],
        template_id: str,
        from_email: str,
        dynamic_template_data: Optional[dict] = None,
        subject: Optional[str] = None,
        cc: Optional[list[str]] = None,
        bcc: Optional[list[str]] = None,
        reply_to: Optional[str] = None,
        categories: Optional[list[str]] = None,
    ) -> dict:
        """Send a template email via SendGrid using a dynamic template.

        Args:
            to: List of recipient email addresses.
            template_id: SendGrid dynamic template ID (e.g. "d-xxxx").
            from_email: Sender email address.
            dynamic_template_data: Dict of substitution data for the template (optional).
            subject: Email subject line (optional, template may define its own).
            cc: List of CC email addresses (optional).
            bcc: List of BCC email addresses (optional).
            reply_to: Reply-to email address (optional).
            categories: List of categories for tracking (optional).

        Returns:
            Dict confirming the email was accepted for delivery.
        """
        sg = _get_client()

        mail = Mail()
        mail.from_email = Email(from_email)
        mail.template_id = template_id
        if subject:
            mail.subject = subject

        personalization = Personalization()
        for addr in to:
            personalization.add_to(To(addr))
        if cc:
            for addr in cc:
                personalization.add_cc(Cc(addr))
        if bcc:
            for addr in bcc:
                personalization.add_bcc(Bcc(addr))
        if dynamic_template_data:
            personalization.dynamic_template_data = dynamic_template_data
        mail.add_personalization(personalization)

        if reply_to:
            mail.reply_to = ReplyTo(reply_to)
        if categories:
            for cat in categories:
                mail.add_category(cat)

        response = sg.client.mail.send.post(request_body=mail.get())
        return {
            "status": "accepted",
            "status_code": response.status_code,
            "message": "Template email accepted for delivery",
        }

    # ── Templates ───────────────────────────────────────────────────────

    @mcp.tool()
    def sendgrid_list_templates(
        generations: str = "dynamic",
        page_size: int = 20,
    ) -> dict:
        """List email templates in SendGrid.

        Args:
            generations: Template generation to filter by — "legacy" or "dynamic"
                         (default "dynamic").
            page_size: Number of templates per page (1-200, default 20).

        Returns:
            Dict with a list of templates including id, name, generation, and
            updated_at.
        """
        sg = _get_client()
        params = {
            "generations": generations,
            "page_size": min(max(1, page_size), 200),
        }
        response = sg.client.templates.get(query_params=params)
        data = json.loads(response.body)
        templates = []
        for t in data.get("result", data.get("templates", [])):
            templates.append({
                "id": t.get("id"),
                "name": t.get("name"),
                "generation": t.get("generation"),
                "updated_at": t.get("updated_at"),
            })
        return {"templates": templates}

    # ── Stats ──────────────────────────────────────────────────────────

    @mcp.tool()
    def sendgrid_get_email_stats(
        start_date: str,
        end_date: Optional[str] = None,
        aggregated_by: Optional[str] = None,
    ) -> dict:
        """Retrieve email statistics from SendGrid.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format (optional, defaults to today).
            aggregated_by: Aggregation period — "day", "week", or "month"
                           (optional, defaults to "day").

        Returns:
            Dict with a list of stat entries, each containing date and metrics
            (requests, delivered, opens, clicks, bounces, etc.).
        """
        sg = _get_client()
        params: dict = {"start_date": start_date}
        if end_date:
            params["end_date"] = end_date
        if aggregated_by:
            params["aggregated_by"] = aggregated_by

        response = sg.client.stats.get(query_params=params)
        data = json.loads(response.body)

        results = []
        for entry in data if isinstance(data, list) else [data]:
            stats_list = entry.get("stats", [])
            metrics = stats_list[0].get("metrics", {}) if stats_list else {}
            results.append({
                "date": entry.get("date"),
                "requests": metrics.get("requests", 0),
                "delivered": metrics.get("delivered", 0),
                "opens": metrics.get("opens", 0),
                "unique_opens": metrics.get("unique_opens", 0),
                "clicks": metrics.get("clicks", 0),
                "unique_clicks": metrics.get("unique_clicks", 0),
                "bounces": metrics.get("bounces", 0),
                "spam_reports": metrics.get("spam_reports", 0),
                "blocks": metrics.get("blocks", 0),
                "deferred": metrics.get("deferred", 0),
            })
        return {"stats": results}

    # ── Contacts (Marketing Campaigns) ─────────────────────────────────

    @mcp.tool()
    def sendgrid_list_contacts(
        page_size: int = 50,
    ) -> dict:
        """List contacts in SendGrid Marketing Campaigns.

        Args:
            page_size: Number of contacts to return (default 50, max 1000).

        Returns:
            Dict with contact_count and a list of contacts including id, email,
            first_name, last_name, and created_at.
        """
        sg = _get_client()
        import json
        response = sg.client.marketing.contacts.search.post(
            request_body={
                "query": "email LIKE '%'",
                "page_size": min(max(1, page_size), 1000),
            }
        )
        data = json.loads(response.body)
        contacts = []
        for c in data.get("result", []):
            contacts.append({
                "id": c.get("id"),
                "email": c.get("email"),
                "first_name": c.get("first_name"),
                "last_name": c.get("last_name"),
                "created_at": c.get("created_at"),
            })
        return {
            "contact_count": data.get("contact_count", len(contacts)),
            "contacts": contacts,
        }

    @mcp.tool()
    def sendgrid_add_contact(
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        list_ids: Optional[list[str]] = None,
        custom_fields: Optional[dict] = None,
    ) -> dict:
        """Add or update a contact in SendGrid Marketing Campaigns.

        If a contact with the given email already exists, it will be updated.

        Args:
            email: Contact email address.
            first_name: Contact first name (optional).
            last_name: Contact last name (optional).
            list_ids: List of contact list IDs to add the contact to (optional).
            custom_fields: Dict of custom field IDs to values (optional).

        Returns:
            Dict with the job_id for the upsert operation.
        """
        sg = _get_client()
        import json

        contact: dict = {"email": email}
        if first_name:
            contact["first_name"] = first_name
        if last_name:
            contact["last_name"] = last_name
        if custom_fields:
            contact["custom_fields"] = custom_fields

        payload: dict = {"contacts": [contact]}
        if list_ids:
            payload["list_ids"] = list_ids

        response = sg.client.marketing.contacts.put(request_body=payload)
        data = json.loads(response.body)
        return {"job_id": data.get("job_id")}
