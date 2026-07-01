# CLAUDE.md — nextlevel-agentic-skills

This repo is a **library of Claude Code skills**. Every top-level directory is one skill. There is
no application to run — the deliverable of work here is a well-formed skill.

## ⚠️ Public repo — no sensitive info

This repository is public. **Never commit secrets or private data**: API keys, JWTs, passwords,
org IDs, customer/PII data, private URLs or hostnames, or internal-only business logic.

- Skills must read secrets from **environment variables at runtime** (see `outreach-api/SKILL.md`),
  never hardcode them.
- Examples and tests must use **placeholder / fake** values.
- Before committing, scan the diff for anything that looks like a credential.

## Anatomy of a skill

```
my-skill/
  SKILL.md          # required — frontmatter + short instructions
  reference/        # optional — deep docs, schemas (read on demand)
  examples/         # optional — runnable examples / sample output
  scripts/          # optional — validators, helpers
  tests/            # optional — checks the skill's output
```

`SKILL.md` frontmatter:

```yaml
---
name: my-skill                     # kebab-case, matches the directory name
description: One line stating WHEN to use this skill — trigger phrases the user
  would say + what the skill produces. This is the ONLY thing the agent sees when
  deciding to activate; make it specific.
---
```

## How to write a good skill

1. **Description is a trigger, not a summary.** Write it from the user's words ("Use when the user
   asks to build / author / design a conversation flow…") and state the concrete output. Vague
   descriptions never get activated.
2. **Progressive disclosure.** Keep `SKILL.md` short and skimmable. Push schemas, long examples, and
   edge-case docs into `reference/` and link to them — the agent reads those files only when needed.
3. **Make output checkable.** Ship a validator or test (`scripts/` + `tests/`) so generated output can
   be verified, not just produced. Prefer zero-dependency validators.
4. **One skill, one job.** If a skill does two unrelated things, split it.
5. **State preconditions up front** (required env vars, base URLs, auth) and stop-and-ask instead of
   inventing values.
6. **Match the existing style.** Read `conversation-flow-builder/` as the reference implementation
   (full schema + example + field docs + validator + tests).

There is a bundled `write-a-skill` skill in Claude Code — use it (`/write-a-skill`) to scaffold new
skills consistently.

## Top-used skills in this repo

| Skill | Use it when |
|---|---|
| [`conversation-flow-builder`](conversation-flow-builder/) | Building/authoring/designing a NextLevel voice-agent `conversation_flow` (multi-step step-builder JSON). Produces one validated `*.conversation_flow.json`. |
| [`outreach-api`](outreach-api/) | Answering questions about outreach campaigns, contacts, conversations, tasks, or monitoring by querying the AI Outreach API read-only. |

## ✅ When you create a NEW skill, ALSO update this file

Adding a skill is not done until the docs reflect it. On every new skill:

1. Add a row to **Top-used skills** above (name → when to use it).
2. Add a matching row to the **Skills** table in `README.md`.
3. Keep both descriptions consistent with the skill's `SKILL.md` frontmatter `description`.
4. If the new skill introduces a new convention or gotcha worth remembering, add it to
   **How to write a good skill** above.

Do this automatically as part of creating the skill — don't wait to be asked.
