# Provider Tool Reference

Complete reference for every tool exposed by integrations-mcp, organized by provider. Each entry includes parameters, descriptions, and example outputs.

---

## Advice Slip

**Module:** `advice.py` · **API:** [Advice Slip API](https://api.adviceslip.com) · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_random_advice` | *(none)* | Get a random piece of advice |
| `search_advice` | `query: str` | Search for advice matching a keyword |

**Example output** (`get_random_advice`):
```json
{"id": 42, "advice": "Don't be afraid to ask questions."}
```

---

## Airtable

**Module:** `airtable_provider.py` · **API:** Airtable (pyairtable SDK) · **Auth:** `AIRTABLE_API_KEY`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `airtable_list_bases` | *(none)* | List all accessible bases |
| `airtable_list_tables` | `base_id: str` | List tables and field schemas in a base |
| `airtable_list_records` | `base_id: str`, `table_name: str`, `max_records: int=100`, `view: str=""`, `fields: list[str]?`, `formula: str=""`, `sort: list[str]?` | List records with filtering and sorting |
| `airtable_get_record` | `base_id: str`, `table_name: str`, `record_id: str` | Get a single record by ID |
| `airtable_create_record` | `base_id: str`, `table_name: str`, `fields: dict`, `typecast: bool=False` | Create a new record |
| `airtable_update_record` | `base_id: str`, `table_name: str`, `record_id: str`, `fields: dict`, `typecast: bool=False` | Partial-update an existing record |
| `airtable_delete_record` | `base_id: str`, `table_name: str`, `record_id: str` | Delete a record |

**Example output** (`airtable_list_bases`):
```json
{"bases": [{"id": "appXXX", "name": "My Base", "permission_level": "create"}]}
```

---

## Amplitude

**Module:** `amplitude_provider.py` · **API:** Amplitude Analytics API · **Auth:** `AMPLITUDE_API_KEY`, `AMPLITUDE_SECRET_KEY`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `amplitude_get_event_counts` | `event_type: str`, `start: str`, `end: str`, `interval: int=1`, `group_by: str?` | Event counts for a specific event over a date range |
| `amplitude_get_active_users` | `start: str`, `end: str`, `interval: int=1` | Active user counts (DAU/WAU/MAU) |
| `amplitude_get_new_users` | `start: str`, `end: str`, `interval: int=1` | New user counts |
| `amplitude_get_revenue` | `start: str`, `end: str`, `interval: int=1`, `metric: str="revenue"` | Revenue metrics (revenue, arpau, arpu, paying) |
| `amplitude_run_segmentation` | `event_type: str`, `start: str`, `end: str`, `metric: str="uniques"`, `interval: int=1`, `segment_property: str?`, `filters: list[dict]?` | Segmentation query with filters/grouping |
| `amplitude_list_cohorts` | *(none)* | List all defined cohorts |
| `amplitude_get_cohort_users` | `cohort_id: str`, `props: int=0`, `limit: int=1000` | User IDs in a cohort |
| `amplitude_get_funnel` | `funnel_id: str`, `start: str`, `end: str`, `interval: int=1`, `segment_property: str?` | Funnel analysis for a saved funnel |

---

## arXiv

**Module:** `arxiv_provider.py` · **API:** [arXiv API](https://export.arxiv.org) · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `arxiv_search` | `query: str`, `category: str?`, `start_date: str?`, `end_date: str?`, `sort_by: str="relevance"`, `sort_order: str="descending"`, `max_results: int=10`, `start: int=0` | Search papers by query, category, and date range |
| `arxiv_get_paper` | `arxiv_id: str` | Fetch metadata for a specific paper |
| `arxiv_get_papers` | `arxiv_ids: str` (comma-separated) | Fetch metadata for multiple papers |

**Example output** (`arxiv_search`):
```json
{"total_results": 100, "papers": [{"arxiv_id": "2401.00001", "title": "...", "authors": [...], "summary": "..."}]}
```

---

## Asana

**Module:** `asana_provider.py` · **API:** Asana REST API v1 · **Auth:** `ASANA_ACCESS_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `asana_list_workspaces` | *(none)* | List all workspaces |
| `asana_list_projects` | `workspace_gid: str`, `archived: bool=False` | List projects in a workspace |
| `asana_get_project` | `project_gid: str` | Get project details |
| `asana_list_tasks` | `project_gid: str`, `assignee: str?`, `completed_since: str?`, `completed: bool?` | List tasks with optional filters |
| `asana_get_task` | `task_gid: str` | Get task details with subtasks and comments |
| `asana_create_task` | `project_gid: str`, `name: str`, `notes: str=""`, `due_on: str?`, `assignee: str?` | Create a new task |
| `asana_update_task` | `task_gid: str`, `name: str?`, `notes: str?`, `due_on: str?`, `assignee: str?`, `completed: bool?` | Update an existing task |
| `asana_list_users` | `workspace_gid: str` | List users in a workspace |
| `asana_add_comment` | `task_gid: str`, `text: str` | Add a comment to a task |

---

## Calendly

**Module:** `calendly_provider.py` · **API:** Calendly API v2 · **Auth:** `CALENDLY_ACCESS_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `calendly_get_current_user` | *(none)* | Get current authenticated user info |
| `calendly_list_event_types` | `active: bool?` | List event types |
| `calendly_list_scheduled_events` | `min_start_time: str?`, `max_start_time: str?`, `status: str?`, `count: int=20` | List scheduled events |
| `calendly_get_event` | `event_uuid: str` | Get event details |
| `calendly_cancel_event` | `event_uuid: str`, `reason: str?` | Cancel an event |
| `calendly_list_invitees` | `event_uuid: str` | List invitees for an event |
| `calendly_create_scheduling_link` | `event_type_uuid: str`, `max_event_count: int=1` | Create a single-use scheduling link |
| `calendly_list_organization_memberships` | *(none)* | List organization memberships |
| `calendly_remove_invitee` | `invitee_uuid: str` | Remove data for an invitee |

---

## Cloudflare

**Module:** `cloudflare_provider.py` · **API:** Cloudflare SDK · **Auth:** `CLOUDFLARE_API_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `cloudflare_list_zones` | *(none)* | List all DNS zones |
| `cloudflare_get_zone` | `zone_id: str` | Get zone details |
| `cloudflare_list_dns_records` | `zone_id: str`, `type: str?`, `name: str?` | List DNS records for a zone |
| `cloudflare_create_dns_record` | `zone_id: str`, `type: str`, `name: str`, `content: str`, `ttl: int=1`, `proxied: bool=False` | Create a DNS record |
| `cloudflare_update_dns_record` | `zone_id: str`, `record_id: str`, `type: str`, `name: str`, `content: str`, `ttl: int=1`, `proxied: bool=False` | Update a DNS record |
| `cloudflare_delete_dns_record` | `zone_id: str`, `record_id: str` | Delete a DNS record |
| `cloudflare_purge_cache` | `zone_id: str`, `purge_everything: bool=False`, `files: list[str]?` | Purge cache for a zone |

---

## CoinGecko

**Module:** `coingecko_provider.py` · **API:** CoinGecko API v3 · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_coin_price` | `coin_ids: str`, `vs_currency: str="usd"` | Get current price for one or more coins |
| `get_coin_market_data` | `coin_ids: str`, `vs_currency: str="usd"` | Get market data (market cap, volume, etc.) |
| `search_coins` | `query: str` | Search coins by name or symbol |

---

## REST Countries

**Module:** `countries.py` · **API:** restcountries.com v3.1 · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_country` | `name: str` | Get country info by name |
| `get_country_by_code` | `code: str` | Get country by ISO code |
| `search_countries_by_region` | `region: str` | List countries in a region |
| `search_countries` | `query: str` | Fuzzy search countries |
| `get_countries_by_language` | `language: str` | Countries that speak a language |
| `compare_countries` | `country1: str`, `country2: str` | Compare two countries side-by-side |

---

## Currency Exchange

**Module:** `currency.py` · **API:** Frankfurter API (ECB data) · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_exchange_rate` | `base: str`, `target: str` | Get latest exchange rate |
| `convert_amount` | `amount: float`, `from_currency: str`, `to_currency: str` | Convert a monetary amount |
| `list_currencies` | *(none)* | List all supported currencies |
| `get_historical_rate` | `date: str`, `base: str`, `target: str` | Get historical exchange rate |

---

## Datadog

**Module:** `datadog_provider.py` · **API:** Datadog API (datadog-api-client SDK) · **Auth:** `DD_API_KEY`, `DD_APP_KEY`, optional `DD_SITE`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `datadog_list_monitors` | `query: str?`, `page: int=0`, `per_page: int=30` | List monitors with optional query filter |
| `datadog_get_monitor` | `monitor_id: int` | Get monitor details |
| `datadog_query_metrics` | `query: str`, `from_ts: int`, `to_ts: int` | Query time-series metrics |
| `datadog_list_dashboards` | `filter_shared: bool?` | List dashboards |
| `datadog_get_events` | `start: int`, `end: int`, `priority: str?`, `sources: str?` | Get events in a time range |
| `datadog_list_hosts` | `filter: str?`, `sort_field: str?`, `count: int=100` | List infrastructure hosts |

---

## Datetime Utilities

**Module:** `datetime_utils.py` · **API:** Python stdlib (zoneinfo) · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_current_time` | `timezone: str="UTC"` | Get current time in a timezone |
| `convert_timezone` | `datetime_str: str`, `from_tz: str`, `to_tz: str` | Convert datetime between timezones |
| `list_timezones` | `region: str?` | List available timezones |
| `time_until` | `target_datetime_str: str`, `timezone: str="UTC"` | Calculate time until a target datetime |

---

## Dictionary & Thesaurus

**Module:** `dictionary.py` · **API:** Free Dictionary API + Datamuse API · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `define` | `word: str` | Get definitions for a word |
| `phonetics` | `word: str` | Get phonetic transcriptions and audio links |
| `synonyms` | `word: str` | Find synonyms |
| `antonyms` | `word: str` | Find antonyms |
| `check_word_exists` | `word: str` | Check if a word is valid |

---

## Dog Images

**Module:** `dogs.py` · **API:** Dog CEO API · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_random_dog_image` | *(none)* | Get a random dog image URL |
| `get_random_dog_by_breed` | `breed: str` | Random image of a specific breed |
| `list_dog_breeds` | *(none)* | List all available breeds |
| `get_breed_images` | `breed: str`, `limit: int=5` | Get multiple images of a breed |

---

## Exchange Rates

**Module:** `exchange_rates.py` · **API:** Frankfurter API (ECB data) · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_latest_rates` | `base: str="EUR"`, `symbols: str?` | Get latest exchange rates |
| `convert_currency` | `amount: float`, `from_currency: str`, `to_currency: str` | Convert a monetary amount |
| `list_currencies` | *(none)* | List supported currencies |

---

## Figma

**Module:** `figma_provider.py` · **API:** Figma REST API v1 · **Auth:** `FIGMA_ACCESS_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `figma_list_projects` | `team_id: str` | List projects in a team |
| `figma_list_files` | `project_id: str` | List files in a project |
| `figma_get_file` | `file_key: str` | Get file metadata and structure |
| `figma_get_file_nodes` | `file_key: str`, `node_ids: str` (comma-separated) | Get specific nodes from a file |
| `figma_get_file_components` | `file_key: str` | List components in a file |
| `figma_get_comments` | `file_key: str` | Get comments on a file |
| `figma_post_comment` | `file_key: str`, `message: str`, `x: float?`, `y: float?` | Post a comment on a file |
| `figma_get_images` | `file_key: str`, `node_ids: str`, `format: str="png"`, `scale: float=1` | Export nodes as images |

---

## GitHub (Authenticated)

**Module:** `github_provider.py` · **API:** GitHub REST API v3 · **Auth:** `GITHUB_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `github_list_repos` | `visibility: str="all"`, `sort: str="updated"`, `per_page: int=30` | List repos for authenticated user |
| `github_get_repo` | `owner: str`, `repo: str` | Get repository details |
| `github_list_issues` | `owner: str`, `repo: str`, `state: str="open"`, `labels: str?`, `per_page: int=30` | List repository issues |
| `github_get_issue` | `owner: str`, `repo: str`, `issue_number: int` | Get issue details |
| `github_create_issue` | `owner: str`, `repo: str`, `title: str`, `body: str?`, `labels: list[str]?`, `assignees: list[str]?` | Create an issue |
| `github_update_issue` | `owner: str`, `repo: str`, `issue_number: int`, `title: str?`, `body: str?`, `state: str?`, `labels: list[str]?` | Update an issue |
| `github_comment_on_issue` | `owner: str`, `repo: str`, `issue_number: int`, `body: str` | Comment on an issue |
| `github_list_prs` | `owner: str`, `repo: str`, `state: str="open"`, `per_page: int=30` | List pull requests |
| `github_get_pr` | `owner: str`, `repo: str`, `pr_number: int` | Get pull request details |
| `github_create_pr_comment` | `owner: str`, `repo: str`, `pr_number: int`, `body: str` | Comment on a pull request |
| `github_list_commits` | `owner: str`, `repo: str`, `sha: str?`, `per_page: int=30` | List commits |
| `github_get_file_contents` | `owner: str`, `repo: str`, `path: str`, `ref: str?` | Get file contents |
| `github_create_or_update_file` | `owner: str`, `repo: str`, `path: str`, `message: str`, `content: str`, `sha: str?`, `branch: str?` | Create or update a file |
| `github_list_branches` | `owner: str`, `repo: str`, `per_page: int=30` | List branches |
| `github_search_code` | `query: str`, `per_page: int=30` | Search code across GitHub |
| `github_search_issues` | `query: str`, `per_page: int=30` | Search issues and PRs |

---

## GitHub Public

**Module:** `github_public.py` · **API:** GitHub REST API (unauthenticated, 60 req/hr) · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `search_repos` | `query: str`, `limit: int=5` | Search public repositories |
| `get_repo` | `owner: str`, `repo: str` | Get public repo details |
| `get_user` | `username: str` | Get public user profile |

---

## GitHub Search

**Module:** `github_search.py` · **API:** GitHub REST API (unauthenticated) · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `search_repositories` | `query: str`, `sort: str="stars"`, `limit: int=5` | Search repositories |
| `get_repository` | `owner: str`, `repo: str` | Get repository details |
| `search_users` | `query: str`, `limit: int=5` | Search GitHub users |
| `get_trending_repos` | `language: str?`, `limit: int=5` | Get trending repositories |

---

## Google Calendar

**Module:** `google_calendar.py` · **API:** Google Calendar API v3 · **Auth:** `GOOGLE_CALENDAR_CREDENTIALS_JSON`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `gcal_list_calendars` | *(none)* | List all calendars |
| `gcal_list_events` | `calendar_id: str="primary"`, `max_results: int=10`, `time_min: str?`, `time_max: str?`, `query: str?` | List events with optional filters |
| `gcal_get_event` | `calendar_id: str`, `event_id: str` | Get event details |
| `gcal_create_event` | `calendar_id: str="primary"`, `summary: str`, `start: str`, `end: str`, `description: str?`, `location: str?`, `attendees: list[str]?` | Create an event |
| `gcal_update_event` | `calendar_id: str`, `event_id: str`, `summary: str?`, `start: str?`, `end: str?`, `description: str?` | Update an event |
| `gcal_delete_event` | `calendar_id: str`, `event_id: str` | Delete an event |
| `gcal_list_freebusy` | `calendar_ids: list[str]`, `time_min: str`, `time_max: str` | Check free/busy status |

---

## Google Sheets

**Module:** `google_sheets_provider.py` · **API:** Google Sheets API v4 · **Auth:** `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_SHEETS_API_KEY`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `sheets_get_spreadsheet` | `spreadsheet_id: str` | Get spreadsheet metadata |
| `sheets_read_range` | `spreadsheet_id: str`, `range: str` | Read values from a range |
| `sheets_write_range` | `spreadsheet_id: str`, `range: str`, `values: list[list]` | Write values to a range |
| `sheets_append_rows` | `spreadsheet_id: str`, `range: str`, `values: list[list]` | Append rows to a sheet |
| `sheets_clear_range` | `spreadsheet_id: str`, `range: str` | Clear values in a range |
| `sheets_create_spreadsheet` | `title: str`, `sheet_names: list[str]?` | Create a new spreadsheet |
| `sheets_batch_update` | `spreadsheet_id: str`, `requests: list[dict]` | Batch update operations |
| `sheets_get_sheet_values_all` | `spreadsheet_id: str` | Get all values from all sheets |

---

## Hacker News

**Module:** `hackernews_provider.py` · **API:** HN Firebase API + Algolia Search · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_top_stories` | `limit: int=10` | Get top stories |
| `get_story` | `id: int` | Get a specific story |
| `get_new_stories` | `limit: int=10` | Get newest stories |
| `get_best_stories` | `limit: int=10` | Get best stories |
| `get_ask_hn` | `limit: int=10` | Get Ask HN stories |
| `get_show_hn` | `limit: int=10` | Get Show HN stories |
| `search_stories` | `query: str`, `page: int=0`, `hits_per_page: int=10` | Search stories via Algolia |
| `get_comments` | `story_id: int`, `limit: int=10` | Get comments for a story |

---

## HubSpot

**Module:** `hubspot_provider.py` · **API:** HubSpot CRM API v3 · **Auth:** `HUBSPOT_ACCESS_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `hubspot_list_contacts` | `limit: int=10`, `after: str?` | List contacts |
| `hubspot_get_contact` | `contact_id: str` | Get contact details |
| `hubspot_create_contact` | `email: str`, `firstname: str?`, `lastname: str?`, `phone: str?`, `company: str?` | Create a contact |
| `hubspot_update_contact` | `contact_id: str`, `properties: dict` | Update a contact |
| `hubspot_search_contacts` | `query: str`, `limit: int=10` | Search contacts |
| `hubspot_list_companies` | `limit: int=10`, `after: str?` | List companies |
| `hubspot_get_company` | `company_id: str` | Get company details |
| `hubspot_create_company` | `name: str`, `domain: str?`, `properties: dict?` | Create a company |
| `hubspot_list_deals` | `limit: int=10`, `after: str?` | List deals |
| `hubspot_get_deal` | `deal_id: str` | Get deal details |
| `hubspot_create_deal` | `dealname: str`, `pipeline: str?`, `dealstage: str?`, `amount: str?` | Create a deal |

---

## HuggingFace

**Module:** `huggingface_provider.py` · **API:** HuggingFace Hub SDK · **Auth:** `HUGGINGFACE_API_KEY`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `huggingface_search_models` | `query: str`, `author: str?`, `task: str?`, `sort: str="downloads"`, `limit: int=10` | Search models |
| `huggingface_get_model_info` | `model_id: str` | Get model details |
| `huggingface_list_datasets` | `author: str?`, `sort: str="downloads"`, `limit: int=10` | List datasets |
| `huggingface_search_datasets` | `query: str`, `author: str?`, `sort: str="downloads"`, `limit: int=10` | Search datasets |
| `huggingface_get_dataset_info` | `dataset_id: str` | Get dataset details |
| `huggingface_list_spaces` | `author: str?`, `sort: str="likes"`, `limit: int=10` | List Spaces |

---

## Intercom

**Module:** `intercom_provider.py` · **API:** Intercom REST API v2.11 · **Auth:** `INTERCOM_ACCESS_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `intercom_list_contacts` | `per_page: int=50` | List contacts |
| `intercom_get_contact` | `contact_id: str` | Get contact details |
| `intercom_create_contact` | `role: str="user"`, `email: str?`, `name: str?`, `phone: str?` | Create a contact |
| `intercom_update_contact` | `contact_id: str`, `email: str?`, `name: str?`, `phone: str?` | Update a contact |
| `intercom_search_contacts` | `query: str`, `field: str="email"` | Search contacts |
| `intercom_list_conversations` | `per_page: int=20` | List conversations |
| `intercom_get_conversation` | `conversation_id: str` | Get conversation details |
| `intercom_reply_to_conversation` | `conversation_id: str`, `body: str`, `message_type: str="comment"` | Reply to a conversation |
| `intercom_list_companies` | `per_page: int=50` | List companies |
| `intercom_get_company` | `company_id: str` | Get company details |

---

## IP Geolocation

**Module:** `ipgeo.py` · **API:** ip-api.com (45 req/min) · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `geolocate_ip` | `ip_address: str` | Geolocate an IP address |
| `get_my_ip_info` | *(none)* | Get geolocation info for your IP |

---

## ISS Tracker

**Module:** `iss.py` · **API:** Open Notify API · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_iss_location` | *(none)* | Get current ISS position (lat/lon) |
| `get_people_in_space` | *(none)* | List people currently in space |
| `get_iss_pass_times` | `lat: float`, `lon: float`, `n: int=5` | Predicted ISS pass times for a location |

---

## Jira

**Module:** `jira_provider.py` · **API:** Jira REST API (atlassian-python-api) · **Auth:** `JIRA_URL`, `JIRA_USER`, `JIRA_API_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `jira_list_projects` | *(none)* | List all projects |
| `jira_list_issues` | `project_key: str`, `jql: str?`, `max_results: int=50` | List issues with optional JQL filter |
| `jira_get_issue` | `issue_key: str` | Get issue details |
| `jira_create_issue` | `project_key: str`, `summary: str`, `issue_type: str="Task"`, `description: str?`, `assignee: str?`, `priority: str?` | Create an issue |
| `jira_update_issue` | `issue_key: str`, `summary: str?`, `description: str?`, `assignee: str?`, `priority: str?` | Update an issue |
| `jira_add_comment` | `issue_key: str`, `body: str` | Add a comment to an issue |
| `jira_list_sprints` | `board_id: int`, `state: str?` | List sprints for a board |

---

## Jokes

**Module:** `jokes.py` · **API:** JokeAPI v2 · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_joke` | `category: str="Any"`, `joke_type: str?` | Get a joke (single or twopart) |
| `get_joke_categories` | *(none)* | List available joke categories |

---

## Linear

**Module:** `linear_provider.py` · **API:** Linear GraphQL API · **Auth:** `LINEAR_API_KEY`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `linear_list_issues` | `team_id: str?`, `state: str?`, `assignee_id: str?`, `first: int=50` | List issues with filters |
| `linear_get_issue` | `issue_id: str` | Get issue details |
| `linear_create_issue` | `team_id: str`, `title: str`, `description: str?`, `assignee_id: str?`, `priority: int?`, `state_id: str?`, `label_ids: list[str]?` | Create an issue |
| `linear_update_issue` | `issue_id: str`, `title: str?`, `description: str?`, `assignee_id: str?`, `priority: int?`, `state_id: str?` | Update an issue |
| `linear_update_issue_status` | `issue_id: str`, `state_id: str` | Update issue status |
| `linear_list_projects` | `first: int=50` | List projects |
| `linear_get_project` | `project_id: str` | Get project details |
| `linear_list_teams` | *(none)* | List teams |
| `linear_get_team` | `team_id: str` | Get team details with workflow states |
| `linear_list_cycles` | `team_id: str` | List cycles for a team |
| `linear_list_labels` | `team_id: str?` | List labels |
| `linear_search_issues` | `query: str`, `first: int=50` | Search issues |
| `linear_add_comment` | `issue_id: str`, `body: str` | Add a comment to an issue |

---

## Meals (TheMealDB)

**Module:** `meals.py` · **API:** TheMealDB API · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `search_meals` | `query: str` | Search meals by name |
| `get_meal` | `id: str` | Get meal details by ID |
| `get_random_meal` | *(none)* | Get a random meal |

---

## Mixpanel

**Module:** `mixpanel_provider.py` · **API:** Mixpanel APIs · **Auth:** `MIXPANEL_SERVICE_ACCOUNT_USERNAME`, `MIXPANEL_SERVICE_ACCOUNT_SECRET`, `MIXPANEL_PROJECT_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `mixpanel_query_events` | `from_date: str`, `to_date: str`, `event: str?`, `limit: int=100` | Query raw events |
| `mixpanel_get_event_properties` | `event: str`, `property_name: str`, `from_date: str`, `to_date: str`, `limit: int=25` | Get property values for an event |
| `mixpanel_get_top_events` | `from_date: str`, `to_date: str`, `limit: int=10` | Get top events by volume |
| `mixpanel_user_profiles` | `where: str?`, `limit: int=100` | Query user profiles |
| `mixpanel_get_user_profile` | `distinct_id: str` | Get a specific user profile |
| `mixpanel_track_event` | `event: str`, `distinct_id: str`, `properties: dict?` | Track an event |
| `mixpanel_get_funnels` | `funnel_id: int`, `from_date: str`, `to_date: str` | Get funnel analysis |
| `mixpanel_get_retention` | `from_date: str`, `to_date: str`, `born_event: str?`, `event: str?` | Get retention data |
| `mixpanel_query_segmentation` | `event: str`, `from_date: str`, `to_date: str`, `on: str?`, `type: str="general"` | Segmentation query |
| `mixpanel_query_revenue` | `from_date: str`, `to_date: str` | Revenue analytics |

---

## Monday.com

**Module:** `monday_provider.py` · **API:** Monday.com GraphQL API v2 · **Auth:** `MONDAY_API_KEY`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `monday_list_boards` | `limit: int=25` | List boards |
| `monday_get_board` | `board_id: int` | Get board details with columns |
| `monday_list_items` | `board_id: int`, `limit: int=25`, `cursor: str?` | List items on a board |
| `monday_get_item` | `item_id: int` | Get item details |
| `monday_create_item` | `board_id: int`, `item_name: str`, `group_id: str?`, `column_values: dict?` | Create an item |
| `monday_update_item` | `board_id: int`, `item_id: int`, `column_values: dict` | Update item column values |
| `monday_list_groups` | `board_id: int` | List groups on a board |
| `monday_create_update` | `item_id: int`, `body: str` | Add an update/comment to an item |

---

## NASA

**Module:** `nasa.py` · **API:** NASA APIs (APOD, NeoWs, Mars Rover Photos) · **Auth:** `NASA_API_KEY` (optional, falls back to DEMO_KEY)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `apod` | `date: str?` | Astronomy Picture of the Day |
| `get_apod_range` | `start_date: str`, `end_date: str` | APOD for a date range |
| `get_random_apod` | `count: int=1` | Random APOD entries |
| `near_earth_objects` | `start_date: str`, `end_date: str` | Near-Earth objects in a date range |
| `mars_photos` | `sol: int`, `camera: str?`, `limit: int=5` | Mars rover photos |

---

## Notion

**Module:** `notion_provider.py` · **API:** Notion API v1 · **Auth:** `NOTION_API_KEY`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `notion_list_databases` | `start_cursor: str?`, `page_size: int=10` | List databases |
| `notion_query_database` | `database_id: str`, `filter: dict?`, `sorts: list[dict]?`, `page_size: int=10` | Query a database with filters |
| `notion_list_pages` | `start_cursor: str?`, `page_size: int=10` | List pages |
| `notion_get_page` | `page_id: str` | Get page properties |
| `notion_create_page` | `parent_id: str`, `parent_type: str="database"`, `properties: dict?`, `children: list[dict]?` | Create a page |
| `notion_update_page` | `page_id: str`, `properties: dict?`, `archived: bool?` | Update page properties |
| `notion_get_block_children` | `block_id: str`, `start_cursor: str?`, `page_size: int=10` | Get child blocks |
| `notion_append_block_children` | `block_id: str`, `children: list[dict]` | Append blocks to a page |
| `notion_search` | `query: str`, `filter_type: str?`, `page_size: int=10` | Search pages and databases |

---

## Number Facts

**Module:** `numberfacts.py` · **API:** numbersapi.com · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_number_fact` | `number: int`, `type: str="trivia"` | Get a fact about a number |
| `get_random_fact` | `type: str="trivia"` | Get a random number fact |
| `get_date_fact` | `month: int`, `day: int` | Get a fact about a date |

---

## Numbers

**Module:** `numbers.py` · **API:** numbersapi.com · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_number_fact` | `number: int`, `type: str="trivia"` | Get a fact about a number |
| `get_random_fact` | `type: str="trivia"` | Get a random number fact |
| `get_date_fact` | `month: int`, `day: int` | Get a fact about a date |

---

## Numbers API

**Module:** `numbers_api.py` · **API:** numbersapi.com · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_number_fact` | `number: int`, `type: str="trivia"` | Get a fact about a number |
| `get_date_fact` | `month: int`, `day: int` | Get a fact about a date |
| `get_random_fact` | `type: str="trivia"` | Get a random number fact |

---

## Okta

**Module:** `okta_provider.py` · **API:** Okta Management API · **Auth:** `OKTA_DOMAIN`, `OKTA_API_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `okta_list_users` | `limit: int=200`, `search: str?`, `filter: str?` | List users |
| `okta_get_user` | `user_id: str` | Get user details |
| `okta_create_user` | `email: str`, `first_name: str`, `last_name: str`, `login: str?`, `password: str?`, `activate: bool=True` | Create a user |
| `okta_update_user` | `user_id: str`, `profile: dict` | Update user profile |
| `okta_deactivate_user` | `user_id: str` | Deactivate a user |
| `okta_list_groups` | `limit: int=200`, `search: str?` | List groups |
| `okta_get_group` | `group_id: str` | Get group details |
| `okta_list_group_members` | `group_id: str`, `limit: int=200` | List group members |
| `okta_list_apps` | `limit: int=200` | List applications |
| `okta_get_app` | `app_id: str` | Get application details |

---

## Open Library

**Module:** `openlibrary_provider.py` · **API:** Open Library API · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `search_books` | `query: str`, `limit: int=5` | Search books |
| `book_detail` | `isbn_or_olid: str` | Get book details by ISBN or Open Library ID |
| `author` | `name: str` | Search for an author |

---

## PagerDuty

**Module:** `pagerduty_provider.py` · **API:** PagerDuty REST API v2 · **Auth:** `PAGERDUTY_API_KEY`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `pagerduty_list_incidents` | `statuses: list[str]?`, `since: str?`, `until: str?`, `limit: int=25` | List incidents |
| `pagerduty_get_incident` | `incident_id: str` | Get incident details |
| `pagerduty_create_incident` | `title: str`, `service_id: str`, `urgency: str="high"`, `body: str?` | Create an incident |
| `pagerduty_acknowledge_incident` | `incident_id: str` | Acknowledge an incident |
| `pagerduty_resolve_incident` | `incident_id: str` | Resolve an incident |
| `pagerduty_list_services` | `limit: int=25` | List services |
| `pagerduty_list_teams` | `limit: int=25` | List teams |
| `pagerduty_list_on_calls` | `schedule_ids: list[str]?`, `since: str?`, `until: str?` | List on-call schedules |
| `pagerduty_list_schedules` | `limit: int=25` | List schedules |

---

## Poetry

**Module:** `poetry.py` · **API:** PoetryDB · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `search_poems_by_author` | `author: str` | Search poems by author |
| `get_poem` | `title: str`, `author: str?` | Get a specific poem |
| `get_random_poem` | *(none)* | Get a random poem |

---

## Postmark

**Module:** `postmark_provider.py` · **API:** Postmark API · **Auth:** `POSTMARK_SERVER_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `postmark_send_email` | `from_email: str`, `to: str`, `subject: str`, `html_body: str?`, `text_body: str?`, `tag: str?` | Send an email |
| `postmark_send_batch` | `messages: list[dict]` | Send batch emails |
| `postmark_get_message_stream` | `stream_id: str="outbound"` | Get message stream info |
| `postmark_list_message_streams` | *(none)* | List message streams |
| `postmark_list_bounces` | `count: int=50`, `offset: int=0`, `type: str?` | List bounced emails |
| `postmark_get_bounce` | `bounce_id: int` | Get bounce details |
| `postmark_get_stats` | `tag: str?`, `from_date: str?`, `to_date: str?` | Get delivery statistics |
| `postmark_get_outbound_overview` | `tag: str?`, `from_date: str?`, `to_date: str?` | Outbound email overview |

---

## QR Code

**Module:** `qrcode.py` · **API:** goqr.me API · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `generate_qr_url` | `data: str`, `size: int=200`, `format: str="png"` | Generate a QR code image URL |
| `generate_qr_base64` | `data: str`, `size: int=200` | Generate a QR code as base64 |
| `generate_vcard_qr` | `name: str`, `phone: str?`, `email: str?`, `url: str?` | Generate a vCard QR code |

---

## Quotes

**Module:** `quotes.py` · **API:** Quotable API + ZenQuotes · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_random_quote` | `tags: str?`, `author: str?` | Get a random quote |
| `search_quotes` | `query: str`, `limit: int=5` | Search quotes |
| `list_quote_authors` | `limit: int=10` | List available authors |

---

## Random User

**Module:** `random_user.py` · **API:** RandomUser.me · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `generate_user` | `nationality: str?`, `gender: str?` | Generate a single random user profile |
| `generate_users` | `count: int=5`, `nationality: str?` | Generate multiple random user profiles |

---

## Random User (alt)

**Module:** `randomuser.py` · **API:** RandomUser.me · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `generate_random_user` | `nationality: str?`, `gender: str?` | Generate a single random user |
| `generate_random_users` | `count: int=5`, `nationality: str?` | Generate multiple random users |

---

## Resend

**Module:** `resend_provider.py` · **API:** Resend REST API · **Auth:** `RESEND_API_KEY`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `resend_send_email` | `from_email: str`, `to: str`, `subject: str`, `html: str?`, `text: str?` | Send an email |
| `resend_send_batch_emails` | `emails: list[dict]` | Send batch emails |
| `resend_list_emails` | *(none)* | List sent emails |
| `resend_get_email` | `email_id: str` | Get email details |
| `resend_list_domains` | *(none)* | List verified domains |
| `resend_verify_domain` | `domain_id: str` | Verify a domain |
| `resend_get_domain` | `domain_id: str` | Get domain details |

---

## RSS/Atom Feeds

**Module:** `rss_provider.py` · **API:** Any RSS/Atom feed (feedparser) · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `fetch_rss_feed` | `url: str`, `max_items: int=10` | Fetch and parse an RSS/Atom feed |
| `popular_feeds` | *(none)* | List popular/example feed URLs |
| `fetch_rss_feed_recent` | `url: str`, `hours: int=24`, `max_items: int=10` | Fetch recent feed entries within N hours |

---

## AWS S3

**Module:** `s3_provider.py` · **API:** AWS S3 (boto3) · **Auth:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `s3_list_buckets` | *(none)* | List all S3 buckets |
| `s3_list_objects` | `bucket: str`, `prefix: str=""`, `max_keys: int=100` | List objects in a bucket |
| `s3_get_object_metadata` | `bucket: str`, `key: str` | Get object metadata |
| `s3_read_object` | `bucket: str`, `key: str`, `encoding: str="utf-8"` | Read object contents |
| `s3_put_object` | `bucket: str`, `key: str`, `body: str`, `content_type: str?` | Upload an object |
| `s3_delete_object` | `bucket: str`, `key: str` | Delete an object |
| `s3_copy_object` | `source_bucket: str`, `source_key: str`, `dest_bucket: str`, `dest_key: str` | Copy an object |
| `s3_generate_presigned_url` | `bucket: str`, `key: str`, `expiration: int=3600` | Generate a presigned URL |

---

## Salesforce

**Module:** `salesforce_provider.py` · **API:** Salesforce REST API v60.0 · **Auth:** `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`, `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `salesforce_query` | `soql: str` | Execute a SOQL query |
| `salesforce_get_record` | `sobject: str`, `record_id: str` | Get a record by ID |
| `salesforce_create_record` | `sobject: str`, `data: dict` | Create a record |
| `salesforce_update_record` | `sobject: str`, `record_id: str`, `data: dict` | Update a record |
| `salesforce_delete_record` | `sobject: str`, `record_id: str` | Delete a record |
| `salesforce_list_objects` | *(none)* | List all sObject types |
| `salesforce_describe_object` | `sobject: str` | Describe an sObject schema |
| `salesforce_search` | `sosl: str` | Execute a SOSL search |

---

## SendGrid

**Module:** `sendgrid_provider.py` · **API:** SendGrid Web API v3 · **Auth:** `SENDGRID_API_KEY`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `sendgrid_send_email` | `to: str`, `from_email: str`, `subject: str`, `content: str`, `content_type: str="text/plain"` | Send an email |
| `sendgrid_send_bulk_email` | `personalizations: list[dict]`, `from_email: str`, `subject: str`, `content: str` | Send bulk personalized emails |
| `sendgrid_list_templates` | `page_size: int=10` | List email templates |
| `sendgrid_get_template` | `template_id: str` | Get template details |
| `sendgrid_list_contacts` | `page_size: int=50` | List marketing contacts |
| `sendgrid_add_contact` | `email: str`, `first_name: str?`, `last_name: str?`, `list_ids: list[str]?` | Add a marketing contact |
| `sendgrid_remove_contact` | `contact_id: str` | Remove a contact |
| `sendgrid_get_stats` | `start_date: str`, `end_date: str?`, `aggregated_by: str="day"` | Get email statistics |
| `sendgrid_list_suppressions` | `type: str="bounces"`, `limit: int=100` | List suppressed emails |

---

## Sentry

**Module:** `sentry_provider.py` · **API:** Sentry Web API · **Auth:** `SENTRY_AUTH_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `sentry_list_projects` | `organization: str` | List projects in an org |
| `sentry_get_project` | `organization: str`, `project_slug: str` | Get project details |
| `sentry_list_issues` | `organization: str`, `project_slug: str`, `query: str?`, `sort: str?` | List issues with optional filters |
| `sentry_get_issue` | `issue_id: str` | Get issue details |
| `sentry_list_issue_events` | `issue_id: str` | List events for an issue |
| `sentry_get_event` | `organization: str`, `project_slug: str`, `event_id: str` | Get event details |

---

## Shopify

**Module:** `shopify_provider.py` · **API:** Shopify Admin REST API · **Auth:** `SHOPIFY_SHOP`, `SHOPIFY_ACCESS_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `shopify_list_products` | `limit: int=50`, `collection_id: str?` | List products |
| `shopify_get_product` | `product_id: int` | Get product details |
| `shopify_create_product` | `title: str`, `body_html: str?`, `vendor: str?`, `product_type: str?`, `tags: str?` | Create a product |
| `shopify_update_product` | `product_id: int`, `title: str?`, `body_html: str?`, `vendor: str?`, `tags: str?` | Update a product |
| `shopify_list_orders` | `limit: int=50`, `status: str="any"`, `financial_status: str?` | List orders |
| `shopify_get_order` | `order_id: int` | Get order details |
| `shopify_list_customers` | `limit: int=50` | List customers |
| `shopify_get_customer` | `customer_id: int` | Get customer details |
| `shopify_create_customer` | `email: str`, `first_name: str?`, `last_name: str?`, `phone: str?`, `tags: str?` | Create a customer |
| `shopify_list_collections` | `limit: int=50` | List collections |
| `shopify_get_inventory_levels` | `location_id: int`, `limit: int=50` | Get inventory levels |

---

## Slack

**Module:** `slack_provider.py` · **API:** Slack Web API · **Auth:** `SLACK_BOT_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `slack_list_channels` | `limit: int=100`, `types: str="public_channel"` | List channels |
| `slack_get_channel` | `channel_id: str` | Get channel info |
| `slack_post_message` | `channel: str`, `text: str`, `thread_ts: str?` | Post a message |
| `slack_list_messages` | `channel: str`, `limit: int=20`, `oldest: str?`, `latest: str?` | List messages in a channel |
| `slack_get_thread_replies` | `channel: str`, `thread_ts: str` | Get replies in a thread |
| `slack_list_users` | `limit: int=100` | List workspace users |
| `slack_get_user` | `user_id: str` | Get user profile |
| `slack_upload_file` | `channels: str`, `content: str`, `filename: str`, `title: str?` | Upload a file |
| `slack_search_messages` | `query: str`, `count: int=20` | Search messages |
| `slack_add_reaction` | `channel: str`, `timestamp: str`, `name: str` | Add a reaction emoji |

---

## Snowflake

**Module:** `snowflake_provider.py` · **API:** Snowflake SQL REST API · **Auth:** `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `snowflake_execute_query` | `statement: str`, `database: str?`, `schema: str?`, `warehouse: str?`, `timeout: int=60` | Execute a SQL statement |
| `snowflake_list_databases` | *(none)* | List databases |
| `snowflake_list_schemas` | `database: str` | List schemas in a database |
| `snowflake_list_tables` | `database: str`, `schema: str="PUBLIC"` | List tables |
| `snowflake_describe_table` | `database: str`, `schema: str`, `table: str` | Describe table schema |
| `snowflake_get_query_status` | `statement_handle: str` | Check async query status |
| `snowflake_list_warehouses` | *(none)* | List warehouses |
| `snowflake_get_query_history` | `warehouse: str?`, `limit: int=25` | Get recent query history |

---

## Stripe

**Module:** `stripe_provider.py` · **API:** Stripe REST API v1 · **Auth:** `STRIPE_SECRET_KEY`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `stripe_list_customers` | `limit: int=10`, `email: str?` | List customers |
| `stripe_get_customer` | `customer_id: str` | Get customer details |
| `stripe_create_customer` | `email: str?`, `name: str?`, `description: str?`, `metadata: dict?` | Create a customer |
| `stripe_list_charges` | `limit: int=10`, `customer: str?` | List charges |
| `stripe_get_charge` | `charge_id: str` | Get charge details |
| `stripe_list_invoices` | `limit: int=10`, `customer: str?`, `status: str?` | List invoices |
| `stripe_get_invoice` | `invoice_id: str` | Get invoice details |
| `stripe_list_subscriptions` | `limit: int=10`, `customer: str?`, `status: str?` | List subscriptions |
| `stripe_get_subscription` | `subscription_id: str` | Get subscription details |
| `stripe_list_products` | `limit: int=10`, `active: bool?` | List products |
| `stripe_get_balance` | *(none)* | Get account balance |

---

## Supabase

**Module:** `supabase_provider.py` · **API:** Supabase Management API + PostgREST · **Auth:** `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ACCESS_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `supabase_execute_sql` | `query: str` | Execute a SQL query |
| `supabase_list_tables` | *(none)* | List all tables |
| `supabase_describe_table` | `table_name: str` | Describe table schema |
| `supabase_select_rows` | `table: str`, `columns: str="*"`, `filters: dict?`, `limit: int=100`, `order: str?` | Select rows from a table |
| `supabase_insert_rows` | `table: str`, `rows: list[dict]` | Insert rows |
| `supabase_list_users` | *(none)* | List auth users |
| `supabase_get_user` | `user_id: str` | Get user details |
| `supabase_create_user` | `email: str`, `password: str`, `user_metadata: dict?` | Create an auth user |
| `supabase_update_user` | `user_id: str`, `email: str?`, `password: str?`, `user_metadata: dict?` | Update an auth user |
| `supabase_delete_user` | `user_id: str` | Delete an auth user |
| `supabase_list_projects` | *(none)* | List Supabase projects |

---

## Timezone

**Module:** `timezone.py` · **API:** WorldTimeAPI · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_current_time` | `timezone: str` | Get current time in a timezone |
| `list_timezones` | *(none)* | List available timezones |
| `convert_time` | `datetime_str: str`, `from_tz: str`, `to_tz: str` | Convert time between timezones |
| `get_time_difference` | `tz1: str`, `tz2: str` | Get time difference between two timezones |
| `parse_natural_timezone` | `city_name: str` | Resolve a city name to a timezone |

---

## Trivia

**Module:** `trivia.py` · **API:** Open Trivia DB · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_trivia_questions` | `amount: int=5`, `category: int?`, `difficulty: str?` | Get trivia questions |
| `get_trivia_categories` | *(none)* | List trivia categories |

---

## Twilio

**Module:** `twilio_provider.py` · **API:** Twilio REST API · **Auth:** `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `twilio_send_sms` | `to: str`, `from_: str`, `body: str` | Send an SMS message |
| `twilio_send_whatsapp` | `to: str`, `from_: str`, `body: str` | Send a WhatsApp message |
| `twilio_list_messages` | `limit: int=20`, `to: str?`, `from_: str?` | List messages |
| `twilio_get_message` | `message_sid: str` | Get message details |
| `twilio_list_calls` | `limit: int=20` | List calls |
| `twilio_make_call` | `to: str`, `from_: str`, `url: str` | Initiate a phone call |
| `twilio_list_phone_numbers` | *(none)* | List owned phone numbers |
| `twilio_lookup_number` | `phone_number: str` | Look up phone number info |

---

## Vercel

**Module:** `vercel_provider.py` · **API:** Vercel REST API · **Auth:** `VERCEL_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `vercel_list_projects` | `limit: int=20` | List projects |
| `vercel_get_project` | `project_id: str` | Get project details |
| `vercel_list_deployments` | `project_id: str?`, `limit: int=20`, `state: str?` | List deployments |
| `vercel_get_deployment` | `deployment_id: str` | Get deployment details |
| `vercel_create_deployment` | `name: str`, `git_source: dict` | Create a deployment |
| `vercel_list_domains` | `limit: int=20` | List domains |
| `vercel_list_environment_variables` | `project_id: str` | List environment variables |

---

## Weather

**Module:** `weather.py` · **API:** Open-Meteo + Nominatim geocoding · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_current_weather` | `location: str` | Get current weather for a city/place |
| `get_weather_forecast` | `location: str`, `days: int=3` | Get multi-day weather forecast |
| `get_weather_by_coordinates` | `lat: float`, `lon: float` | Get weather by lat/lon coordinates |

---

## Weather (Open-Meteo)

**Module:** `weather_openmeteo.py` · **API:** Open-Meteo API · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_current_weather` | `lat: float`, `lon: float` | Get current weather by coordinates |
| `get_forecast` | `lat: float`, `lon: float`, `days: int=3` | Get forecast by coordinates |

---

## Wikipedia

**Module:** `wikipedia_provider.py` · **API:** Wikimedia REST API · **Auth:** None

| Tool | Parameters | Description |
|------|-----------|-------------|
| `search_wikipedia` | `query: str`, `limit: int=5` | Search Wikipedia articles |
| `get_article_summary` | `title: str` | Get article summary |
| `get_article_sections` | `title: str` | Get article section structure |
| `get_related_articles` | `title: str` | Get related articles |

---

## Zendesk

**Module:** `zendesk_provider.py` · **API:** Zendesk REST API v2 · **Auth:** `ZENDESK_SUBDOMAIN`, `ZENDESK_EMAIL`, `ZENDESK_API_TOKEN`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `zendesk_list_tickets` | `status: str?`, `sort_by: str="created_at"`, `per_page: int=25` | List tickets |
| `zendesk_get_ticket` | `ticket_id: int` | Get ticket details |
| `zendesk_create_ticket` | `subject: str`, `description: str`, `priority: str?`, `type: str?`, `assignee_id: int?`, `tags: list[str]?` | Create a ticket |
| `zendesk_update_ticket` | `ticket_id: int`, `status: str?`, `priority: str?`, `assignee_id: int?`, `tags: list[str]?`, `comment: str?` | Update a ticket |
| `zendesk_add_comment` | `ticket_id: int`, `body: str`, `public: bool=True` | Add a comment to a ticket |
| `zendesk_list_users` | `role: str?`, `per_page: int=25` | List users |
| `zendesk_get_user` | `user_id: int` | Get user details |
| `zendesk_search` | `query: str`, `type: str="ticket"` | Search across Zendesk |
| `zendesk_list_organizations` | `per_page: int=25` | List organizations |
