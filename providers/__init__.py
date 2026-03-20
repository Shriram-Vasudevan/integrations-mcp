"""Provider registry for integrations-mcp.

Providers are imported lazily inside register_all_providers() to avoid
loading every SDK at module-import time.  This keeps server startup fast
and prevents a single broken/missing dependency from blocking all providers.
"""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Each entry is (module_path, register_function_name).
# Only the canonical *_provider version is listed for providers that have
# both a legacy and a modern implementation.
_PROVIDERS: list[tuple[str, str]] = [
    ("providers.advice", "register"),
    ("providers.arxiv_provider", "register"),
    ("providers.airtable_provider", "register"),
    ("providers.amplitude_provider", "register"),
    ("providers.asana_provider", "register"),
    ("providers.calendly_provider", "register"),
    ("providers.cloudflare_provider", "register"),
    ("providers.coingecko_provider", "register"),
    ("providers.colors", "register"),
    ("providers.crypto", "register"),
    ("providers.countries", "register"),
    ("providers.currency", "register"),
    ("providers.catfacts", "register"),
    ("providers.dad_jokes", "register"),
    ("providers.dictionary", "register"),
    ("providers.dogs", "register"),
    ("providers.exchange_rates", "register"),
    ("providers.datadog_provider", "register"),
    ("providers.figma_provider", "register"),
    ("providers.foodfacts", "register"),
    ("providers.github_provider", "register"),
    ("providers.github_public", "register"),
    ("providers.github_search", "register"),
    ("providers.google_calendar", "register"),
    ("providers.google_sheets_provider", "register"),
    ("providers.hacker_news", "register"),
    ("providers.hackernews_provider", "register"),
    ("providers.holidays", "register"),
    ("providers.hubspot_provider", "register"),
    ("providers.huggingface_provider", "register"),
    ("providers.intercom_provider", "register"),
    ("providers.ipgeo", "register"),
    ("providers.iss", "register"),
    ("providers.jira_provider", "register"),
    ("providers.jokes", "register"),
    ("providers.linear_provider", "register"),
    ("providers.meals", "register"),
    ("providers.name_analysis", "register"),
    ("providers.mixpanel_provider", "register"),
    ("providers.monday_provider", "register"),
    ("providers.nasa", "register"),
    ("providers.nasa_apod", "register"),
    ("providers.numbers", "register"),
    ("providers.numberfacts", "register"),
    ("providers.numbers_api", "register"),
    ("providers.notion", "register"),
    ("providers.notion_provider", "register"),
    ("providers.openlibrary", "register"),
    ("providers.openlibrary_provider", "register"),
    ("providers.okta_provider", "register"),
    ("providers.pagerduty_provider", "register"),
    ("providers.pokemon", "register"),
    ("providers.poetry", "register"),
    ("providers.qrcode", "register"),
    ("providers.quotes", "register"),
    ("providers.random_user", "register"),
    ("providers.randomuser", "register"),
    ("providers.postmark_provider", "register"),
    ("providers.resend_provider", "register"),
    ("providers.rss_provider", "register"),
    ("providers.s3_provider", "register"),
    ("providers.salesforce_provider", "register"),
    ("providers.sendgrid_provider", "register"),
    ("providers.sentry_provider", "register"),
    ("providers.shopify_provider", "register"),
    ("providers.slack_provider", "register"),
    ("providers.snowflake_provider", "register"),
    ("providers.supabase_provider", "register"),
    ("providers.stripe_provider", "register"),
    ("providers.twilio_provider", "register"),
    ("providers.vercel_provider", "register"),
    ("providers.timezone", "register"),
    ("providers.datetime_utils", "register"),
    ("providers.trivia", "register"),
    ("providers.useless_facts", "register"),
    ("providers.utils", "register"),
    ("providers.nameanalysis", "register"),
    ("providers.weather", "register"),
    ("providers.wikipedia", "register"),
    ("providers.zendesk_provider", "register"),
]


def register_all_providers(mcp: "FastMCP") -> None:
    """Register all available providers with the MCP server.

    Each provider is imported on demand so that:
    - A missing optional dependency only disables that one provider.
    - Startup is not bottlenecked by heavy SDK imports until they are needed.
    """
    for module_path, func_name in _PROVIDERS:
        try:
            mod = importlib.import_module(module_path)
            register_fn = getattr(mod, func_name)
            register_fn(mcp)
        except Exception:
            logger.warning("Failed to load provider %s", module_path, exc_info=True)
