# Worked Examples

All examples assume `$OUTREACH_API_BASE_URL`, `$OUTREACH_API_JWT`, and `$OUTREACH_ORG_ID` are resolved (see SKILL.md).

## "Which contacts in campaign X are stalled — no activity in 24h?"

```bash
# 1. Resolve campaign id from name
curl -sS "$OUTREACH_API_BASE_URL/api/admin/campaigns?limit=200" \
  -H "Authorization: Bearer $OUTREACH_API_JWT" \
  -H "x-ai-agent-organization-context: $OUTREACH_ORG_ID" \
| jq '.[] | select(.name | test("X"; "i")) | {id, name}'

# 2. Contacts touched before 24h ago, in that campaign
YESTERDAY=$(date -u -v-1d +%Y-%m-%dT%H:%M:%SZ)
curl -sS "$OUTREACH_API_BASE_URL/api/admin/contacts?campaign_id=$CID&updated_to=$YESTERDAY&sort=updated_at:asc&limit=50" \
  -H "Authorization: Bearer $OUTREACH_API_JWT" \
  -H "x-ai-agent-organization-context: $OUTREACH_ORG_ID" \
| jq '.items[] | {email, phone, latest_contact_state, updated_at}'
```

## "Summarize the last conversation with jane@acme.com"

```bash
CID=$(curl -sS "$OUTREACH_API_BASE_URL/api/admin/contacts?email=jane@acme.com&limit=1" \
  -H "Authorization: Bearer $OUTREACH_API_JWT" \
  -H "x-ai-agent-organization-context: $OUTREACH_ORG_ID" \
| jq -r '.items[0].id')

curl -sS "$OUTREACH_API_BASE_URL/api/admin/contacts/$CID/message-history?limit=50" \
  -H "Authorization: Bearer $OUTREACH_API_JWT" \
  -H "x-ai-agent-organization-context: $OUTREACH_ORG_ID" \
| jq '.messages[] | {ts: .message_timestamp, ch: .conversation_channel, who: .author_type, content}'
```

Then summarize the result in plain language.

## "How many contacts need human input?"

```bash
curl -sS "$OUTREACH_API_BASE_URL/api/admin/contacts?requires_human_input=true&limit=1" \
  -H "Authorization: Bearer $OUTREACH_API_JWT" \
  -H "x-ai-agent-organization-context: $OUTREACH_ORG_ID" \
| jq '.totalItems'
```

## "What states exist in campaign X, and how many contacts in each?"

```bash
STATES=$(curl -sS "$OUTREACH_API_BASE_URL/api/admin/contact-states/distinct?campaign_id=$CID" \
  -H "Authorization: Bearer $OUTREACH_API_JWT" \
  -H "x-ai-agent-organization-context: $OUTREACH_ORG_ID")

echo "$STATES" | jq -r '.[]' | while read state; do
  total=$(curl -sS "$OUTREACH_API_BASE_URL/api/admin/contacts?campaign_id=$CID&latest_contact_state=$state&limit=1" \
    -H "Authorization: Bearer $OUTREACH_API_JWT" \
    -H "x-ai-agent-organization-context: $OUTREACH_ORG_ID" \
  | jq '.totalItems')
  echo "$state: $total"
done
```

## "Show me everyone with their next pending action"

```bash
curl -sS "$OUTREACH_API_BASE_URL/api/admin/campaign-monitoring?campaign_id=$CID" \
  -H "Authorization: Bearer $OUTREACH_API_JWT" \
  -H "x-ai-agent-organization-context: $OUTREACH_ORG_ID" \
| jq '.[] | {email: .contact_email, state: .latest_contact_state, next: .next_task_type, when: .next_task_time}'
```
