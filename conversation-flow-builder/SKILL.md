---
name: conversation-flow-builder
description: Build a NextLevel voice-agent conversation_flow — the visual step-builder JSON that turns a single-prompt agent into a multi-step conversation (steps with their own prompts, natural-language routing between them, collected state, per-step tools, and global nodes). Use when the user asks to build / author / design a conversation flow, a voice-agent workflow, a step-builder flow, a conversation_flow.json, a multi-step agent script, or to convert a call script into a flow. Produces one validated `*.conversation_flow.json` file on disk.
---

# conversation-flow-builder

Author a **`conversation_flow`** — the JSON contract the NextLevel voice worker runs to drive a
multi-step phone/chat conversation. The deliverable of this skill is always **one JSON file written
to disk** that passes the bundled validator.

## What a conversation_flow is

A flow is a graph of **steps**. Each step is its own mini-agent: it has its own `prompt` and its own
scoped `tools`, and the conversation moves between steps by **natural-language routing** — you write a
`when` predicate on each edge and the model calls a `go_to_<target>` tool when that condition is met.
Between steps the worker swaps the active prompt/tools in place. State collected mid-call (`state_fields`)
is readable by later steps as `{state.<field>}`.

Read [`reference/field_reference.md`](reference/field_reference.md) for the full field-by-field docs and
[`reference/workflow_config.schema.json`](reference/workflow_config.schema.json) for the authoritative
JSON Schema. A complete, every-feature example is
[`examples/full_spec_example.json`](examples/full_spec_example.json).

## Build workflow (follow in order)

1. **Gather requirements.** From the user's script/description, identify: the persona + always-on rules
   (→ `shared_prompt`), the distinct conversation phases (→ `steps`), the data to capture
   (→ `state_fields`), any external calls (→ `tools`), and the exits (→ `end` steps or a **global**
   exit). If any of these is unclear, ask before writing.
2. **Sketch the graph.** List step ids, which step is `entry_step`, and the edges (`from → to`, with the
   `when` predicate for each). Mark any destination reachable from *everywhere* (e.g. "say goodbye", "talk
   to a human", "answer an FAQ") as a **global node** instead of wiring an edge from every step.
3. **Write the JSON.** Start from `examples/full_spec_example.json` and adapt. Keep step prompts small —
   they are sent every turn the step is active; put shared persona/rules in `shared_prompt` once.
4. **Validate.** Run the bundled validator (see below). Fix every error. Re-run until clean.
5. **Return the file.** Write it as `<agent_name>.conversation_flow.json` (snake_case) in the location the
   user asked for, and report the path plus a one-paragraph summary of the steps and routing.

## Validate the file (required before returning)

```bash
python <skill-dir>/scripts/validate_flow.py path/to/your.conversation_flow.json
```

Zero third-party dependencies. It mirrors the structural + cross-reference checks the worker enforces at
config-parse time (a flow that passes here will load in the worker), and — if `jsonschema` happens to be
installed — also validates against the bundled schema. Exit code `0` = valid, `1` = errors (each printed
with its JSON path).

## Golden rules (the things builders get wrong)

- **`routing` is required and fully author-controlled.** The worker hard-codes no routing prose. You MUST
  supply all five `routing` fields. A standard block is in the example; copy it verbatim unless you have a
  reason to change the wording. Set `acknowledgment_required: false` to switch steps silently (no filler).
- **`entry_step` must be a regular `llm` step** in `steps[]` — never an `end` step and never a global node.
- **Global nodes = authored once, reachable everywhere.** Put exits/branches that any step can take in
  `global_steps[]` with a single `when`. The runtime adds a `go_to_<id>` to every `llm` step (minus each
  node's `exclude[]`). This is the outgoing-edge analogue of `shared_prompt`. An explicit transition to the
  same id wins over the synthesized one.
- **Collect timing.** A step's `collect` slots are captured only when the model calls that step's
  `go_to_*` tool (they ride the transition as optional params). So give early steps a **wide** `collect`
  if the caller might volunteer data early, and never expect a step to silently auto-advance without a
  user turn — prefer an on-entry question over a silent hop.
- **Two continuation directives.** `continuation_directive` is returned when a filler was spoken;
  `continuation_directive_no_filler` when none was. If `acknowledgment_required` is `false`, only the
  no-filler one ever fires — set both to the same string.
- **Prompts are voice-first.** One question at a time, short sentences, numbers as words if it's a phone
  agent. Never reference step ids or `{tokens}` in spoken text.

## Substitutions available in prompts and `final_message`

- `{state.<field>}` — a collected `state_fields` value (empty string until filled).
- `{Variable}` — runtime variables the worker injects: `{TodayDateTime}`, `{agent_name}`, `{CallType}`,
  `{UserPhone}`, `{RoomName}`, `{UserMessageCount}`, and any lead/metadata fields. Unknown ones render empty.

See [`reference/field_reference.md`](reference/field_reference.md) for everything else.
