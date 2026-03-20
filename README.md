# integrations-mcp

*Built by an autnomous agent over about a day*

A comprehensive MCP (Model Context Protocol) server that exposes **390+ tools** across **66 providers**, giving AI assistants direct access to popular SaaS platforms, public APIs, and utility services.

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run the MCP server
python server.py
```

Configure provider-specific environment variables (see table below) for authenticated services. Providers with missing credentials are skipped gracefully at startup.

## Architecture

```
server.py                  → FastMCP entry point
providers/__init__.py      → Lazy provider registry (all providers loaded on demand)
providers/<name>.py        → Individual provider modules, each exporting a register(mcp) function
```

Each provider is imported lazily so a missing optional dependency only disables that one provider — the rest of the server continues to work.

## Provider Table

| Provider | Module | Tools | API / Service | Auth Required | Env Vars |
|----------|--------|------:|---------------|:-------------:|----------|
| **Advice Slip** | `advice.py` | 2 | Advice Slip API | No | — |
| **Airtable** | `airtable_provider.py` | 7 | Airtable (pyairtable) | Yes | `AIRTABLE_API_KEY` |
| **Amplitude** | `amplitude_provider.py` | 8 | Amplitude Analytics API | Yes | `AMPLITUDE_API_KEY`, `AMPLITUDE_SECRET_KEY` |
| **arXiv** | `arxiv_provider.py` | 3 | arXiv API | No | — |
| **Asana** | `asana_provider.py` | 9 | Asana REST API v1 | Yes | `ASANA_ACCESS_TOKEN` |
| **Calendly** | `calendly_provider.py` | 9 | Calendly API v2 | Yes | `CALENDLY_ACCESS_TOKEN` |
| **Cloudflare** | `cloudflare_provider.py` | 7 | Cloudflare SDK | Yes | `CLOUDFLARE_API_TOKEN` |
| **CoinGecko** | `coingecko_provider.py` | 3 | CoinGecko API v3 | No | — |
| **REST Countries** | `countries.py` | 6 | restcountries.com v3.1 | No | — |
| **Currency Exchange** | `currency.py` | 4 | Frankfurter API (ECB) | No | — |
| **Datadog** | `datadog_provider.py` | 6 | Datadog API | Yes | `DD_API_KEY`, `DD_APP_KEY` |
| **Datetime Utilities** | `datetime_utils.py` | 4 | Python stdlib (zoneinfo) | No | — |
| **Dictionary** | `dictionary.py` | 5 | Free Dictionary API + Datamuse | No | — |
| **Dog Images** | `dogs.py` | 4 | Dog CEO API | No | — |
| **Exchange Rates** | `exchange_rates.py` | 3 | Frankfurter API (ECB) | No | — |
| **Figma** | `figma_provider.py` | 8 | Figma REST API v1 | Yes | `FIGMA_ACCESS_TOKEN` |
| **GitHub** | `github_provider.py` | 16 | GitHub REST API v3 | Yes | `GITHUB_TOKEN` |
| **GitHub Public** | `github_public.py` | 3 | GitHub REST API (unauth) | No | — |
| **GitHub Search** | `github_search.py` | 4 | GitHub REST API (unauth) | No | — |
| **Google Calendar** | `google_calendar.py` | 7 | Google Calendar API v3 | Yes | `GOOGLE_CALENDAR_CREDENTIALS_JSON` |
| **Google Sheets** | `google_sheets_provider.py` | 8 | Google Sheets API v4 | Yes | `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_SHEETS_API_KEY` |
| **Hacker News** | `hackernews_provider.py` | 8 | HN Firebase + Algolia API | No | — |
| **HubSpot** | `hubspot_provider.py` | 11 | HubSpot CRM API v3 | Yes | `HUBSPOT_ACCESS_TOKEN` |
| **HuggingFace** | `huggingface_provider.py` | 6 | HuggingFace Hub SDK | Yes | `HUGGINGFACE_API_KEY` |
| **Intercom** | `intercom_provider.py` | 10 | Intercom REST API v2.11 | Yes | `INTERCOM_ACCESS_TOKEN` |
| **IP Geolocation** | `ipgeo.py` | 2 | ip-api.com | No | — |
| **ISS Tracker** | `iss.py` | 3 | Open Notify API | No | — |
| **Jira** | `jira_provider.py` | 7 | Jira REST API (atlassian-python-api) | Yes | `JIRA_URL`, `JIRA_USER`, `JIRA_API_TOKEN` |
| **Jokes** | `jokes.py` | 2 | JokeAPI v2 | No | — |
| **Linear** | `linear_provider.py` | 13 | Linear GraphQL API | Yes | `LINEAR_API_KEY` |
| **Meals** | `meals.py` | 3 | TheMealDB API | No | — |
| **Mixpanel** | `mixpanel_provider.py` | 10 | Mixpanel APIs | Yes | `MIXPANEL_SERVICE_ACCOUNT_USERNAME`, `MIXPANEL_SERVICE_ACCOUNT_SECRET`, `MIXPANEL_PROJECT_TOKEN` |
| **Monday.com** | `monday_provider.py` | 8 | Monday.com GraphQL API v2 | Yes | `MONDAY_API_KEY` |
| **NASA** | `nasa.py` | 5 | NASA APIs (APOD, NeoWs, Mars) | Optional | `NASA_API_KEY` (falls back to DEMO_KEY) |
| **Notion** | `notion_provider.py` | 9 | Notion API v1 | Yes | `NOTION_API_KEY` |
| **Number Facts** | `numberfacts.py` | 3 | numbersapi.com | No | — |
| **Numbers** | `numbers.py` | 3 | numbersapi.com | No | — |
| **Numbers API** | `numbers_api.py` | 3 | numbersapi.com | No | — |
| **Okta** | `okta_provider.py` | 10 | Okta Management API | Yes | `OKTA_DOMAIN`, `OKTA_API_TOKEN` |
| **Open Library** | `openlibrary_provider.py` | 3 | Open Library API | No | — |
| **PagerDuty** | `pagerduty_provider.py` | 9 | PagerDuty REST API v2 | Yes | `PAGERDUTY_API_KEY` |
| **Poetry** | `poetry.py` | 3 | PoetryDB | No | — |
| **Postmark** | `postmark_provider.py` | 8 | Postmark API | Yes | `POSTMARK_SERVER_TOKEN` |
| **QR Code** | `qrcode.py` | 3 | goqr.me API | No | — |
| **Quotes** | `quotes.py` | 3 | Quotable API + ZenQuotes | No | — |
| **Random User** | `random_user.py` | 2 | RandomUser.me API | No | — |
| **Random User (alt)** | `randomuser.py` | 2 | RandomUser.me API | No | — |
| **Resend** | `resend_provider.py` | 7 | Resend REST API | Yes | `RESEND_API_KEY` |
| **RSS/Atom Feeds** | `rss_provider.py` | 3 | Any RSS/Atom feed (feedparser) | No | — |
| **AWS S3** | `s3_provider.py` | 8 | AWS S3 (boto3) | Yes | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` |
| **Salesforce** | `salesforce_provider.py` | 8 | Salesforce REST API v60.0 | Yes | `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`, `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD` |
| **SendGrid** | `sendgrid_provider.py` | 9 | SendGrid Web API v3 | Yes | `SENDGRID_API_KEY` |
| **Sentry** | `sentry_provider.py` | 6 | Sentry Web API | Yes | `SENTRY_AUTH_TOKEN` |
| **Shopify** | `shopify_provider.py` | 11 | Shopify Admin REST API | Yes | `SHOPIFY_SHOP`, `SHOPIFY_ACCESS_TOKEN` |
| **Slack** | `slack_provider.py` | 10 | Slack Web API | Yes | `SLACK_BOT_TOKEN` |
| **Snowflake** | `snowflake_provider.py` | 8 | Snowflake SQL REST API | Yes | `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD` |
| **Stripe** | `stripe_provider.py` | 11 | Stripe REST API v1 | Yes | `STRIPE_SECRET_KEY` |
| **Supabase** | `supabase_provider.py` | 11 | Supabase Management API + PostgREST | Yes | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ACCESS_TOKEN` |
| **Timezone** | `timezone.py` | 5 | WorldTimeAPI | No | — |
| **Trivia** | `trivia.py` | 2 | Open Trivia DB | No | — |
| **Twilio** | `twilio_provider.py` | 8 | Twilio REST API | Yes | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` |
| **Vercel** | `vercel_provider.py` | 7 | Vercel REST API | Yes | `VERCEL_TOKEN` |
| **Weather** | `weather.py` | 3 | Open-Meteo + Nominatim | No | — |
| **Weather (Open-Meteo)** | `weather_openmeteo.py` | 2 | Open-Meteo API | No | — |
| **Wikipedia** | `wikipedia_provider.py` | 4 | Wikimedia REST API | No | — |
| **Zendesk** | `zendesk_provider.py` | 9 | Zendesk REST API v2 | Yes | `ZENDESK_SUBDOMAIN`, `ZENDESK_EMAIL`, `ZENDESK_API_TOKEN` |

> **Total: 66 providers · 390+ tools · 34 authenticated · 32 free/public**

## Detailed Tool Reference

See [`providers/PROVIDERS.md`](providers/PROVIDERS.md) for a full reference of every tool with parameters, descriptions, and example outputs.

## Adding a New Provider

1. Create `providers/your_provider.py` with a `register(mcp)` function.
2. Use `@mcp.tool()` to decorate each tool function.
3. Add `("providers.your_provider", "register")` to the `_PROVIDERS` list in `providers/__init__.py`.
4. Add any new dependencies to `pyproject.toml`.

```python
def register(mcp):
    @mcp.tool()
    def your_tool_name(param: str) -> dict:
        """Description of what this tool does."""
        # implementation
        return {"result": "..."}
```

## License

See repository for license details.
