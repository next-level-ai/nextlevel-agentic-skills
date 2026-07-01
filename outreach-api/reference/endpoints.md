# Endpoint Catalog

All endpoints are GET. Authenticated calls require both headers (see SKILL.md) unless noted.

## Identity (no org header needed)

| Endpoint | Purpose |
|---|---|
| `/api/auth/me` | Confirm caller identity. |
| `/api/auth/user/organizations` | List orgs the user can act on. Call first to pick org id. |
| `/api/auth/permissions` | Discover permission enum values (public). |

## Campaigns — requires VIEW_CAMPAIGNS

| Endpoint | Purpose |
|---|---|
| `/api/admin/campaigns?status=&limit=&offset=` | List campaigns. |
| `/api/admin/campaigns/{campaign_id}` | Full config: strategy, dialer settings, contact_count, secrets metadata (no values). |
| `/api/admin/stats` | Org-wide counts: tasks (total/pending/completed), contacts, webhook_events, prompts. |

## Contacts — requires VIEW_CONTACTS

| Endpoint | Purpose |
|---|---|
| `/api/admin/contacts` | Primary search/filter endpoint. See "search_contacts pattern" below. |
| `/api/admin/contacts/{contact_id}` | One contact with latest state. |
| `/api/admin/contact-states/distinct?campaign_id=` | Distinct state strings (org-scoped, optionally per campaign). Call before filtering by state. |
| `/api/admin/contacts/{contact_id}/state` | Full state transition history, newest first. |

## Conversations — requires VIEW_CONTACTS

| Endpoint | Purpose |
|---|---|
| `/api/admin/contacts/{contact_id}/message-history?channel=&limit=&offset=` | Paginated messages. `channel` ∈ {email, sms, phone}. |

## Tasks (scheduled outreach actions) — requires VIEW_CONTACTS

| Endpoint | Purpose |
|---|---|
| `/api/admin/tasks?contact_id=&campaign_id=&status=&task_type=&limit=&offset=` | List. `contact_id` is the contact's UUID. Each task carries its `contact_id` (UUID) plus a nested `contact` object (email, phone, first_name, last_name). |
| `/api/admin/tasks/{task_id}` | One task with workflow_id, scheduled_at, payload. |

## Events log — requires VIEW_CONTACTS

| Endpoint | Purpose |
|---|---|
| `/api/admin/webhook-events?contact_id=&campaign_id=&event_type=&processed=&limit=&offset=` | Inbound feed (email_received, sms_received, phone_call_started, phone_call_ended). Use for "what happened recently?". |

## Prompts (LLM system messages) — requires VIEW_CAMPAIGNS

| Endpoint | Purpose |
|---|---|
| `/api/admin/prompts?prompt_type=&campaign_id=&is_active=&limit=&offset=` | List. |
| `/api/admin/prompts/{prompt_id}` | Full content. |
| `/api/admin/llm/default-model` | System default model id. |

## Campaign monitoring — requires VIEW_CAMPAIGNS

| Endpoint | Purpose |
|---|---|
| `/api/admin/campaign-monitoring?campaign_id=&updated_from=&updated_to=` | Flat: each contact with next pending task + latest state. |
| `/api/admin/campaign-monitoring/dynamic?campaign_id=&updated_from=&updated_to=` | Same data with dynamic columns from `campaign.strategy.monitoring_fields`. Use when user asks "show me the monitoring table." |
| `/api/admin/campaign-monitoring/count?campaign_id=&latest_contact_state=&search=&updated_from=&updated_to=` | Count only. Use to gauge result size before fetching. |

## Export — requires VIEW_CONTACTS

| Endpoint | Purpose |
|---|---|
| `/api/campaigns/{campaign_id}/contacts/export?format=json&status=&email=&date_from=&date_to=&limit=&offset=` | Bundled: contacts + messages + state events. Prefer `format=json`; the CSV stream is hard to handle. |

## search_contacts pattern

`GET /api/admin/contacts` answers most queries. Filters (combine freely):

| Param | Effect |
|---|---|
| `email` | Partial, case-insensitive |
| `phone` | Partial, case-insensitive |
| `campaign_id` | Exact UUID |
| `requires_human_input` | `true` / `false` |
| `search` | Full-text across first_name, last_name, email, phone |
| `latest_contact_state` | Exact match on most recent state string (or `none` / `null`) |
| `updated_from` / `updated_to` | ISO datetime range on effective update time |
| `sort` | `created_at:desc`, `email:asc`, etc. Sortable: created_at, updated_at, email, first_name, last_name, phone. |
| `limit` | 1–1000, default 100 |
| `offset` | Default 0 |

Response: `{ items: [...], totalItems, totalPages, limit, offset }`.
