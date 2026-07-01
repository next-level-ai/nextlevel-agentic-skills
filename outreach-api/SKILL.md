---
name: outreach-api
description: Query the AI Outreach FastAPI server read-only via curl — campaigns, contacts, contact states, conversations, tasks, webhook events, prompts, and campaign monitoring. Use when the user asks about outreach campaigns, contact status, message history, stalled contacts, or monitoring data. Never performs writes.
---

# Outreach API — Read-only Agent Guide

You are calling the AI Outreach FastAPI server on the user's behalf. **Read-only operations only.**

## Before any request

1. **Base URL**: use `$OUTREACH_API_BASE_URL` if set, else ask the user.
2. **JWT**: read from `$OUTREACH_API_JWT`. If unset or expired, stop and ask the user — never invent one.
3. **Organization id**: required as `x-ai-agent-organization-context` header on every authenticated call. Get it once per session via `GET /api/auth/user/organizations` and remember it. If the user belongs to multiple orgs, ask which.

Every authenticated request must include:

```
Authorization: Bearer $OUTREACH_API_JWT
x-ai-agent-organization-context: $OUTREACH_ORG_ID
```

Always pipe responses through `jq`; default page sizes are large.

## Operating rules

- **Read-only.** This skill does not authorize POST, PATCH, PUT, or DELETE. If the user asks to start a campaign, send a message, import contacts, edit a prompt, or cancel a dial — stop and tell them this skill cannot do that. Direct them to the admin UI.
- **Paginate.** Default `limit=50` for interactive queries. Never request `limit>200` unless the user explicitly asks for a bulk pull.
- **Count before listing** when the user asks "how many." Use `?limit=1` and read `totalItems`, or `/campaign-monitoring/count`.
- **Don't fan out.** Prefer one filtered list call over N single-contact calls.
- **Cache** org id and campaign ids for the rest of the conversation; do not re-resolve every turn.
- **Never guess contact-state strings.** States are LLM-written and free-form per org. Call `/api/admin/contact-states/distinct` first to learn the exact values, then filter.
- **Quote state strings verbatim** when reporting them back — they're meaningful labels.
- **Respect org scoping.** A 404 on a known id means it belongs to another org; do not retry with different headers.

## Error handling

| Status | Cause | Action |
|---|---|---|
| 401 | Missing/expired JWT | Stop. Ask for a fresh token. No blind retry. |
| 403 | Missing `VIEW_CAMPAIGNS` or `VIEW_CONTACTS` | Stop. Tell the user which endpoint and permission. |
| 400 "Organization context header is required" | Missing org header | Resolve org id, retry once. |
| 404 | Not in this org (or doesn't exist) | Treat as not found in current scope. |
| 422 | Bad param | Re-check the endpoint signature in [reference/endpoints.md](reference/endpoints.md) before retrying. |

## Quick start

```bash
# Who am I, and which orgs can I act on?
curl -sS "$OUTREACH_API_BASE_URL/api/auth/user/organizations" \
  -H "Authorization: Bearer $OUTREACH_API_JWT" | jq

# How many contacts need human input?
curl -sS "$OUTREACH_API_BASE_URL/api/admin/contacts?requires_human_input=true&limit=1" \
  -H "Authorization: Bearer $OUTREACH_API_JWT" \
  -H "x-ai-agent-organization-context: $OUTREACH_ORG_ID" \
| jq '.totalItems'
```

## Reference

- Full endpoint catalog and the `search_contacts` filter table: [reference/endpoints.md](reference/endpoints.md)
- Worked query examples (stalled contacts, conversation summary, state counts, monitoring): [examples/queries.md](examples/queries.md)

## When this skill isn't enough

- **Exact response shapes**: fetch `$OUTREACH_API_BASE_URL/openapi.json` or open Swagger at `/docs`.
- **Write operations**: out of scope. Direct the user to the admin UI.
- **Cross-org queries**: unsupported. The API is hard-scoped to one org per request.
