# nextlevel-agentic-skills

Reusable [Claude Code](https://claude.com/claude-code) **skills** for building on the NextLevel
voice-agent platform. Each subdirectory is one skill (a `SKILL.md` plus bundled reference, examples,
and scripts) that any Claude Code agent can invoke to do a task consistently.

## Skills

| Skill | What it does |
|---|---|
| [`conversation-flow-builder`](conversation-flow-builder/) | Build a voice-agent `conversation_flow` — the multi-step "step builder" JSON (steps, natural-language routing, collected state, tools, global nodes). Produces one validated `*.conversation_flow.json` file. Ships the full schema, a full-spec example, field-by-field docs, a zero-dependency validator, and a test suite. |
| [`outreach-api`](outreach-api/) | Query the AI Outreach FastAPI server read-only via `curl` — campaigns, contacts, conversations, tasks, webhook events, and monitoring data. Reads auth from env vars; never performs writes. |

## What is a skill?

A skill is a folder Claude Code loads on demand. It contains a `SKILL.md` with YAML frontmatter —
a `name` and a `description` that tells the agent **when** to use it. When your request matches a
skill's description, the agent activates it and follows its instructions. Detail lives in bundled
files (schemas, examples, scripts) that are read only when needed.

## Using a skill

**Per project** — symlink (or copy) the skill into the project's `.claude/skills/`:

```bash
mkdir -p .claude/skills
ln -s /path/to/nextlevel-agentic-skills/conversation-flow-builder .claude/skills/conversation-flow-builder
```

**Globally** — put it under `~/.claude/skills/` instead. Claude Code auto-discovers it and
activates it when a request matches the skill's `description` (e.g. "build a conversation flow for …").

You can also invoke a skill explicitly by name: `/conversation-flow-builder`.

## Contributing a skill

See [`CLAUDE.md`](CLAUDE.md) for the conventions. In short: create a directory with a `SKILL.md`
whose frontmatter has a `name` and a trigger-focused `description`, keep `SKILL.md` short, push
detail into bundled files (progressive disclosure), ship a validator/test so the output can be
checked, and add a row to the table above.
