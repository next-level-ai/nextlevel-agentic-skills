# conversation_flow — field reference

Every field of the `conversation_flow` contract, what it means, and how the worker uses it. The
machine-readable version is [`workflow_config.schema.json`](workflow_config.schema.json); a complete
example is [`../examples/full_spec_example.json`](../examples/full_spec_example.json).

**Runtime in one paragraph.** The flow is a graph of steps. One step is active at a time; its `prompt`
is the system prompt and its `tools` are in scope. After each user turn the model may call a
`go_to_<target>` tool (built from an outgoing transition's `when`) to move to another step — the worker
then swaps the prompt/tools in place. There is no separate router LLM call; routing rides the reply turn,
so it works identically in voice and text. When absent, the agent runs its classic single prompt.

---

## Top-level keys

| Key | Required | Type | Meaning |
|---|---|---|---|
| `schema_version` | ✅ | `1` | Contract version. Must be `1`. |
| `entry_step` | ✅ | step id | Where every conversation starts. **Must be a regular `llm` step** in `steps[]` — not an `end` step, not a global node. |
| `routing` | ✅ | object | Wording for the `go_to_*` transition tools + the post-transition directive. All five sub-fields required (see below). |
| `shared_prompt` | — | string | A global prompt **prefix** prepended to every step's prompt. Put persona / always-on rules here once. |
| `state_fields` | — | array | Typed slots collected during the call, readable later as `{state.<name>}`. |
| `steps` | ✅ | array (≥1) | The explicit graph: `llm` and `end` steps. |
| `global_steps` | — | array | Global nodes reachable from every `llm` step without an explicit edge. |
| `tools` | — | array | Tool definitions (`http` or `agent_tool`) referenced by `steps[].tools`. |

Step ids share **one namespace** across `steps[]` and `global_steps[]`; all must be unique. Tool names
and state-field names must each be unique. All ids/names are **snake_case slugs**: `^[a-z][a-z0-9_]{0,63}$`.

---

## `routing` (all five required)

The worker hard-codes no routing prose — you author it, and it is sent to the model on relevant turns.

| Field | Type | Meaning |
|---|---|---|
| `acknowledgment_required` | bool | If `true`, each non-end `go_to_*` tool has a required `acknowledgment` filler arg the model writes and the worker speaks immediately to mask the step-swap latency. `false` ⇒ no filler, steps switch silently. |
| `acknowledgment_description` | string | Description of that filler arg, written for the LLM (e.g. "A brief phrase to say now while switching"). Required even when `acknowledgment_required` is `false`. |
| `transition_description_template` | string | Description of each `go_to_*` tool. Must be a Python `str.format` string whose **only** placeholder is `{when}` (filled with the transition's predicate). E.g. `"Call as soon as {when}."` |
| `continuation_directive` | string | Returned as the `go_to_*` tool result **when a filler was spoken** — steers the continuation reply (e.g. "don't re-greet"). |
| `continuation_directive_no_filler` | string | Returned **when no filler was spoken** (`acknowledgment_required:false`, or the model omitted it). If you never use fillers, set this equal to `continuation_directive`. |

Any `llm` step may carry a partial `routing` **override** (same fields, all optional) that applies to
transitions **leaving** that step; omitted fields inherit the flow-level value.

---

## `state_fields[]`

Typed slots. Extraction is LLM-driven; the worker coerces values and drops ones that don't parse.

| Field | Type | Meaning |
|---|---|---|
| `name` | slug | Referenced by `steps[].collect` and read in prompts as `{state.<name>}`. |
| `type` | `string` \| `number` \| `boolean` | Value type. |
| `description` | string | Used verbatim in the extraction prompt — write it for the LLM. |
| `enum` | string[] | Optional closed set of allowed values. **string type only.** |

Collected state is also handed to the end-of-call metadata extractor under `workflow_state`.

---

## `steps[]` — `llm` step

`{ id, type:"llm", prompt, model?, routing?, tools[], collect[], transitions[] }`

| Field | Type | Meaning |
|---|---|---|
| `prompt` | string | Step system prompt. Supports `{Variable}` and `{state.<field>}`. Keep it small — sent every turn the step is active. Prefixed with `shared_prompt` if set. |
| `model` | object | Optional per-step LLM override `{provider, name, settings}`. Provider ∈ openai/google/anthropic. *(Parsed but not applied in v1 — steps use the agent's model.)* |
| `routing` | object | Optional partial routing override for transitions leaving this step. |
| `tools` | slug[] (≤16) | Names of `tools[]` entries in scope while active. **Empty ⇒ the agent's full tool set.** |
| `collect` | slug[] | `state_fields` this step extracts. Captured when the model calls this step's `go_to_*` (they ride the transition as optional params). |
| `transitions` | array (≤8) | Outgoing edges `{to, when}`, evaluated in order; first match wins. Empty ⇒ terminal conversational step (stays here until an end step / global exit). |

**transition** = `{ to: <existing step id>, when: <natural-language predicate> }`. Write `when` as a
condition over the conversation, e.g. `"the caller has confirmed the booking details"`.

## `steps[]` — `end` step

`{ id, type:"end", final_message?, terminate_call? }`

| Field | Type | Meaning |
|---|---|---|
| `final_message` | string \| null | Fixed line spoken via TTS before ending (no LLM call). Supports `{Variable}`/`{state.<field>}`. |
| `terminate_call` | bool (default `true`) | `true`: hang up through the normal terminate path (cleanup, extractors, billing fire). `false`: speak `final_message` and go silent (widget flows where the frontend closes). |

---

## `global_steps[]` — global nodes

Zero or more steps reachable from **every** `llm` step without an explicit edge — the outgoing-edge
analogue of `shared_prompt`. Canonical use: a single exit (`say_goodbye`) any step can take, so the
agent can end (or branch) anywhere without wiring an edge per step.

A global node is a normal `llm` or `end` step **plus**:

| Field | Type | Meaning |
|---|---|---|
| `when` | string (**required**) | The single routing predicate, authored **once**. The runtime fills it into each in-scope step's `transition_description_template` as `{when}` — as if every `llm` step carried a `{to:<id>, when:<this>}` transition. |
| `exclude` | slug[] | `llm` steps that should **not** reach this node (default: every `llm` step can). Each entry must name an existing `llm` step. |

Rules:
- A `global_end_step` also takes `final_message` / `terminate_call`; a `global_llm_step` also takes
  `prompt` / `model` / `routing` / `tools` / `collect` / `transitions`.
- **Explicit wins over global**: if an `llm` step has its own transition to a global id, that explicit
  `when` is used and no duplicate tool is synthesized.
- A global node never targets itself; `entry_step` may not be a global node.
- A `global_llm_step` you land on becomes the ordinary active step — there is **no automatic return**;
  author its `transitions[]` if it should hand back.
- **Tool budget**: a step's effective routing tools = its explicit transitions (≤8) **plus** every
  in-scope global node. Keep the global set small — each costs context every turn.

---

## `tools[]`

### `http` — inline REST tool

`{ name, kind:"http", description, parameters?, param_mapping?, pre_execution_speech?, pre_execution_speech_allow_interruption?, request }`

| Field | Type | Meaning |
|---|---|---|
| `description` | string | What the tool does / when to call it. Sent to the LLM — keep concise. |
| `parameters` | JSON Schema | The LLM-provided arguments (object schema). |
| `param_mapping` | `{arg: target}` | Routes each arg into the request, e.g. `{"postcode":"body_json.postcode"}`. Omitted ⇒ every declared parameter defaults to `body_json.<name>`. Targets: `body_json.*`, `headers.*`, `query_params.*`. |
| `pre_execution_speech` | string | Spoken the moment the tool is called, **before** the request runs (masks latency; static string). |
| `pre_execution_speech_allow_interruption` | bool (default `true`) | Whether the caller may interrupt it. |
| `request` | object | `{ method, url, headers?, body?, timeout_sec? }`. `url` used verbatim; `body` is the static JSON base; `timeout_sec` 1–30 (default 5). |

### `agent_tool` — reference to an existing agent tool

`{ name, kind:"agent_tool", ref }` — `ref` is the `llm_function_name` of a tool already configured on
the agent (`custom_tool_configurations`). Because tools run natively, session tools like
`escalate_to_human_phone_call` and `terminate_call` **are allowed** here (a transfer step typically refs
`escalate_to_human_phone_call`).

---

## Substitution tokens (prompts, `final_message`)

- `{state.<field>}` — a collected slot; substituted first. Unfilled ⇒ empty string.
- `{Variable}` — runtime variables the worker injects: `{TodayDateTime}`, `{agent_name}`, `{CallType}`,
  `{UserPhone}`, `{InboundPhone}`/`{OutboundPhone}`, `{RoomName}`, `{UserMessageCount}`, and any
  lead/metadata fields (e.g. `{outreach_contact_name}`). Unknown placeholders render empty.

---

## Authoring gotchas (design around these)

1. **Front-loaded data.** If the caller might volunteer name/postcode/etc. early, give the early steps a
   **wide** `collect` — a slot is only recorded when the model passes it into that step's `go_to_*` call.
2. **No silent auto-advance.** A step won't fire its `go_to_*` without a user turn to respond to. Prefer an
   on-entry question ("Shall I check dates?") over expecting a silent hop; merge always-sequential steps.
3. **Keep prompts voice-first.** Short sentences, one question at a time, never mention step ids or raw
   `{tokens}` in spoken text.
4. **`shared_prompt` carries persona once.** Each `step.prompt` *replaces* the base system prompt, so
   global rules live in `shared_prompt`; each step prompt is only its task-specific delta.
