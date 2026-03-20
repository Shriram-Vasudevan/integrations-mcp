"""Stripe provider using the stripe-python SDK."""

import os
from typing import Optional

import stripe
from mcp.server.fastmcp import FastMCP


def _get_client() -> stripe.StripeClient:
    """Return a Stripe client configured from the STRIPE_API_KEY env var."""
    key = os.environ.get("STRIPE_API_KEY")
    if not key:
        raise RuntimeError("STRIPE_API_KEY environment variable is not set")
    return stripe.StripeClient(key)


def register(mcp: FastMCP) -> None:
    """Register Stripe tools with the MCP server."""

    @mcp.tool()
    async def stripe_list_customers(
        limit: int = 10,
        starting_after: Optional[str] = None,
        email: Optional[str] = None,
    ) -> dict:
        """List Stripe customers.

        Args:
            limit: Number of customers to return (1-100, default 10).
            email: Filter by customer email address (optional).
            starting_after: Customer ID cursor for pagination (optional).

        Returns:
            List of customers with id, email, name, and metadata.
        """
        client = _get_client()
        params: dict = {"limit": min(max(1, limit), 100)}
        if starting_after:
            params["starting_after"] = starting_after
        if email:
            params["email"] = email
        result = client.customers.list(params=params)
        customers = []
        for c in result.data:
            customers.append({
                "id": c.id,
                "email": c.email,
                "name": c.name,
                "description": c.description,
                "created": c.created,
                "currency": c.currency,
                "delinquent": c.delinquent,
                "metadata": dict(c.metadata) if c.metadata else {},
            })
        return {"has_more": result.has_more, "customers": customers}

    @mcp.tool()
    async def stripe_get_customer(customer_id: str) -> dict:
        """Retrieve a specific Stripe customer by ID.

        Args:
            customer_id: The customer ID (e.g. "cus_abc123").

        Returns:
            Customer details including email, name, and balance.
        """
        client = _get_client()
        c = client.customers.retrieve(customer_id)
        return {
            "id": c.id,
            "email": c.email,
            "name": c.name,
            "description": c.description,
            "phone": c.phone,
            "created": c.created,
            "currency": c.currency,
            "balance": c.balance,
            "delinquent": c.delinquent,
            "default_source": c.default_source,
            "metadata": dict(c.metadata) if c.metadata else {},
        }

    @mcp.tool()
    async def stripe_list_charges(
        limit: int = 10,
        starting_after: Optional[str] = None,
        customer: Optional[str] = None,
    ) -> dict:
        """List Stripe charges.

        Args:
            limit: Number of charges to return (1-100, default 10).
            starting_after: Charge ID cursor for pagination (optional).
            customer: Filter by customer ID (optional).

        Returns:
            List of charges with id, amount, currency, status, and customer.
        """
        client = _get_client()
        params: dict = {"limit": min(max(1, limit), 100)}
        if starting_after:
            params["starting_after"] = starting_after
        if customer:
            params["customer"] = customer
        result = client.charges.list(params=params)
        charges = []
        for ch in result.data:
            charges.append({
                "id": ch.id,
                "amount": ch.amount,
                "currency": ch.currency,
                "status": ch.status,
                "paid": ch.paid,
                "refunded": ch.refunded,
                "customer": ch.customer,
                "description": ch.description,
                "created": ch.created,
                "payment_method": ch.payment_method,
            })
        return {"has_more": result.has_more, "charges": charges}

    @mcp.tool()
    async def stripe_create_payment_intent(
        amount: int,
        currency: str = "usd",
        customer: Optional[str] = None,
        description: Optional[str] = None,
        payment_method: Optional[str] = None,
        confirm: bool = False,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Create a Stripe PaymentIntent.

        Args:
            amount: Amount in the smallest currency unit (e.g. cents for USD).
            currency: Three-letter ISO currency code (default "usd").
            customer: Customer ID to associate with this PaymentIntent (optional).
            description: Description of the payment (optional).
            payment_method: Payment method ID to attach (optional).
            confirm: Whether to immediately confirm the PaymentIntent (default False).
            metadata: Key-value metadata to attach (optional).

        Returns:
            PaymentIntent with id, status, amount, client_secret, and details.
        """
        client = _get_client()
        params: dict = {"amount": amount, "currency": currency}
        if customer:
            params["customer"] = customer
        if description:
            params["description"] = description
        if payment_method:
            params["payment_method"] = payment_method
        if confirm:
            params["confirm"] = True
        if metadata:
            params["metadata"] = metadata
        pi = client.payment_intents.create(params=params)
        return {
            "id": pi.id,
            "status": pi.status,
            "amount": pi.amount,
            "currency": pi.currency,
            "client_secret": pi.client_secret,
            "customer": pi.customer,
            "description": pi.description,
            "payment_method": pi.payment_method,
            "created": pi.created,
            "metadata": dict(pi.metadata) if pi.metadata else {},
        }

    @mcp.tool()
    async def stripe_list_subscriptions(
        limit: int = 10,
        starting_after: Optional[str] = None,
        customer: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict:
        """List Stripe subscriptions.

        Args:
            limit: Number of subscriptions to return (1-100, default 10).
            starting_after: Subscription ID cursor for pagination (optional).
            customer: Filter by customer ID (optional).
            status: Filter by status: active, past_due, canceled, unpaid, trialing, all (optional).

        Returns:
            List of subscriptions with id, status, customer, current period, and items.
        """
        client = _get_client()
        params: dict = {"limit": min(max(1, limit), 100)}
        if starting_after:
            params["starting_after"] = starting_after
        if customer:
            params["customer"] = customer
        if status:
            params["status"] = status
        result = client.subscriptions.list(params=params)
        subscriptions = []
        for sub in result.data:
            items = []
            if sub.items and sub.items.data:
                for item in sub.items.data:
                    price = item.price
                    recurring = price.recurring if price else None
                    items.append({
                        "id": item.id,
                        "price_id": price.id if price else None,
                        "product": price.product if price else None,
                        "amount": price.unit_amount if price else None,
                        "currency": price.currency if price else None,
                        "interval": recurring.interval if recurring else None,
                    })
            subscriptions.append({
                "id": sub.id,
                "status": sub.status,
                "customer": sub.customer,
                "current_period_start": sub.current_period_start,
                "current_period_end": sub.current_period_end,
                "cancel_at_period_end": sub.cancel_at_period_end,
                "created": sub.created,
                "items": items,
                "metadata": dict(sub.metadata) if sub.metadata else {},
            })
        return {"has_more": result.has_more, "subscriptions": subscriptions}

    @mcp.tool()
    async def stripe_get_subscription(subscription_id: str) -> dict:
        """Retrieve a specific Stripe subscription by ID.

        Args:
            subscription_id: The subscription ID (e.g. "sub_abc123").

        Returns:
            Subscription details including status, customer, items, and billing period.
        """
        client = _get_client()
        sub = client.subscriptions.retrieve(subscription_id)
        items = []
        if sub.items and sub.items.data:
            for item in sub.items.data:
                price = item.price
                recurring = price.recurring if price else None
                items.append({
                    "id": item.id,
                    "price_id": price.id if price else None,
                    "product": price.product if price else None,
                    "amount": price.unit_amount if price else None,
                    "currency": price.currency if price else None,
                    "interval": recurring.interval if recurring else None,
                })
        return {
            "id": sub.id,
            "status": sub.status,
            "customer": sub.customer,
            "current_period_start": sub.current_period_start,
            "current_period_end": sub.current_period_end,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "canceled_at": sub.canceled_at,
            "ended_at": sub.ended_at,
            "trial_start": sub.trial_start,
            "trial_end": sub.trial_end,
            "created": sub.created,
            "default_payment_method": sub.default_payment_method,
            "latest_invoice": sub.latest_invoice,
            "items": items,
            "metadata": dict(sub.metadata) if sub.metadata else {},
        }
