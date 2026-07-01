#!/usr/bin/env python3
"""Validate a NextLevel ``conversation_flow`` JSON file.

Zero third-party dependencies (stdlib only). This mirrors the structural and
cross-reference checks the voice worker enforces at config-parse time, so a flow
that passes here will load in the worker. If the optional ``jsonschema`` package is
installed, the bundled JSON Schema is applied as an extra pass.

Usage:
    python validate_flow.py path/to/flow.conversation_flow.json

Exit code: 0 = valid, 1 = errors found, 2 = bad invocation / unreadable file.

It is also importable — ``validate(flow_dict) -> list[str]`` returns the errors
(empty list = valid), which the bundled tests use.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

SLUG = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
TOP_KEYS = {
    "schema_version", "entry_step", "routing", "shared_prompt",
    "state_fields", "steps", "global_steps", "tools",
}
ROUTING_KEYS = {
    "acknowledgment_required", "acknowledgment_description",
    "transition_description_template", "continuation_directive",
    "continuation_directive_no_filler",
}
STATE_TYPES = {"string", "number", "boolean"}
HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
MODEL_PROVIDERS = {"openai", "google", "anthropic"}


def _is_slug(value: Any) -> bool:
    return isinstance(value, str) and bool(SLUG.match(value))


def _dupes(errors: List[str], values: List[Any], label: str) -> None:
    seen: Set[Any] = set()
    dup: Set[Any] = set()
    for v in values:
        if v in seen:
            dup.add(v)
        seen.add(v)
    for d in sorted(x for x in dup if isinstance(x, str)):
        errors.append(f"duplicate {label} '{d}'")


def validate(flow: Any) -> List[str]:
    errors: List[str] = []

    def err(msg: str) -> None:
        errors.append(msg)

    if not isinstance(flow, dict):
        return ["top level must be a JSON object"]

    for key in flow:
        if key not in TOP_KEYS:
            err(f"unknown top-level key '{key}'")
    if flow.get("schema_version") != 1:
        err("schema_version must be 1")
    for req in ("entry_step", "routing", "steps"):
        if req not in flow:
            err(f"missing required key '{req}'")

    _check_routing(err, flow.get("routing"))

    field_names = _check_state_fields(err, flow.get("state_fields") or [])

    steps = flow.get("steps") or []
    globals_ = flow.get("global_steps") or []
    tools = flow.get("tools") or []

    step_ids = [s.get("id") for s in steps if isinstance(s, dict)]
    global_ids = [g.get("id") for g in globals_ if isinstance(g, dict)]
    tool_names = [t.get("name") for t in tools if isinstance(t, dict)]

    _dupes(errors, step_ids + global_ids, "step id")
    _dupes(errors, tool_names, "tool name")
    _dupes(errors, field_names, "state_field name")

    id_ns: Set[Any] = set(step_ids) | set(global_ids)
    field_ns: Set[Any] = set(field_names)
    tool_ns: Set[Any] = set(tool_names)
    llm_ids: Set[Any] = (
        {s.get("id") for s in steps if isinstance(s, dict) and s.get("type") == "llm"}
        | {g.get("id") for g in globals_ if isinstance(g, dict) and g.get("type") == "llm"}
    )

    if not steps:
        err("steps must contain at least one step")
    for i, s in enumerate(steps):
        _check_step(err, s, f"steps[{i}]", tool_ns, field_ns, id_ns, is_global=False)
    for i, g in enumerate(globals_):
        _check_step(err, g, f"global_steps[{i}]", tool_ns, field_ns, id_ns, is_global=True, llm_ids=llm_ids)

    _check_entry(err, flow.get("entry_step"), steps, set(step_ids), set(global_ids))

    for i, t in enumerate(tools):
        _check_tool(err, t, f"tools[{i}]")

    return errors


def _check_routing(err, routing: Any) -> None:
    if routing is None:
        return
    if not isinstance(routing, dict):
        err("routing must be an object")
        return
    for m in sorted(ROUTING_KEYS - routing.keys()):
        err(f"routing missing required field '{m}'")
    for e in sorted(routing.keys() - ROUTING_KEYS):
        err(f"routing has unknown field '{e}'")
    tpl = routing.get("transition_description_template")
    if isinstance(tpl, str):
        try:
            tpl.format(when="")
        except (KeyError, IndexError, ValueError):
            err("routing.transition_description_template must be a format string whose only placeholder is {when}")


def _check_state_fields(err, fields: Any) -> List[Any]:
    names: List[Any] = []
    if not isinstance(fields, list):
        err("state_fields must be an array")
        return names
    for i, f in enumerate(fields):
        loc = f"state_fields[{i}]"
        if not isinstance(f, dict):
            err(f"{loc} must be an object")
            continue
        names.append(f.get("name"))
        if not _is_slug(f.get("name")):
            err(f"{loc}.name '{f.get('name')}' is not a valid snake_case slug")
        if f.get("type") not in STATE_TYPES:
            err(f"{loc}.type must be one of {sorted(STATE_TYPES)}")
        if "enum" in f:
            if f.get("type") != "string":
                err(f"{loc}.enum is only allowed for string type")
            elif not f.get("enum"):
                err(f"{loc}.enum must list at least one value")
    return names


def _check_step(err, s: Any, loc: str, tool_ns, field_ns, id_ns, is_global: bool, llm_ids: Optional[Set] = None) -> None:
    if not isinstance(s, dict):
        err(f"{loc} must be an object")
        return
    if not _is_slug(s.get("id")):
        err(f"{loc}.id '{s.get('id')}' is not a valid snake_case slug")
    typ = s.get("type")
    if typ not in ("llm", "end"):
        err(f"{loc}.type must be 'llm' or 'end'")

    if is_global:
        when = s.get("when")
        if not (isinstance(when, str) and when.strip()):
            err(f"{loc}.when is required and must be a non-empty string (global node)")
        for ex in s.get("exclude") or []:
            if ex not in (llm_ids or set()):
                err(f"{loc}.exclude references '{ex}', which is not an llm step")

    if typ == "llm":
        if not (isinstance(s.get("prompt"), str) and s.get("prompt").strip()):
            err(f"{loc}.prompt is required and must be non-empty for an llm step")
        step_tools = s.get("tools") or []
        if len(step_tools) > 16:
            err(f"{loc}.tools has {len(step_tools)} entries (max 16)")
        for tname in step_tools:
            if tname not in tool_ns:
                err(f"{loc}.tools references unknown tool '{tname}'")
        for cname in s.get("collect") or []:
            if cname not in field_ns:
                err(f"{loc}.collect references unknown state_field '{cname}'")
        model = s.get("model")
        if isinstance(model, dict) and model.get("provider") not in MODEL_PROVIDERS:
            err(f"{loc}.model.provider must be one of {sorted(MODEL_PROVIDERS)}")
        trans = s.get("transitions") or []
        if len(trans) > 8:
            err(f"{loc}.transitions has {len(trans)} entries (max 8)")
        for j, tr in enumerate(trans):
            if not isinstance(tr, dict):
                err(f"{loc}.transitions[{j}] must be an object")
                continue
            if tr.get("to") not in id_ns:
                err(f"{loc}.transitions[{j}] targets unknown step '{tr.get('to')}'")
            if not (isinstance(tr.get("when"), str) and tr.get("when").strip()):
                err(f"{loc}.transitions[{j}].when must be a non-empty string")


def _check_entry(err, entry: Any, steps: List, step_ids: Set, global_ids: Set) -> None:
    if entry in global_ids:
        err(f"entry_step '{entry}' must be a regular step, not a global node")
        return
    if entry not in step_ids:
        err(f"entry_step '{entry}' is not a defined step")
        return
    s = next((x for x in steps if isinstance(x, dict) and x.get("id") == entry), None)
    if s is not None and s.get("type") != "llm":
        err(f"entry_step '{entry}' must be an llm step, got '{s.get('type')}'")


def _check_tool(err, t: Any, loc: str) -> None:
    if not isinstance(t, dict):
        err(f"{loc} must be an object")
        return
    if not _is_slug(t.get("name")):
        err(f"{loc}.name '{t.get('name')}' is not a valid snake_case slug")
    kind = t.get("kind")
    if kind == "http":
        if not t.get("description"):
            err(f"{loc}.description is required for an http tool")
        req = t.get("request")
        if not isinstance(req, dict):
            err(f"{loc}.request is required for an http tool")
        else:
            if req.get("method") not in HTTP_METHODS:
                err(f"{loc}.request.method must be one of {sorted(HTTP_METHODS)}")
            if not req.get("url"):
                err(f"{loc}.request.url is required")
            timeout = req.get("timeout_sec", 5)
            if not (isinstance(timeout, (int, float)) and 1 <= timeout <= 30):
                err(f"{loc}.request.timeout_sec must be between 1 and 30")
    elif kind == "agent_tool":
        if not t.get("ref"):
            err(f"{loc}.ref is required for an agent_tool")
    else:
        err(f"{loc}.kind must be 'http' or 'agent_tool'")


def _schema_pass(flow: Any) -> List[str]:
    """Optional extra validation against the bundled JSON Schema (skipped if jsonschema absent)."""
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return []
    schema_path = Path(__file__).resolve().parents[1] / "reference" / "workflow_config.schema.json"
    try:
        schema = json.loads(schema_path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    validator = jsonschema.Draft202012Validator(schema)
    return [f"schema: {e.json_path}: {e.message}" for e in validator.iter_errors(flow)]


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_flow.py <flow.conversation_flow.json>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    try:
        flow = json.loads(path.read_text())
    except OSError as e:
        print(f"✗ cannot read {path}: {e}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"✗ {path.name}: invalid JSON — {e}", file=sys.stderr)
        return 1

    errors = validate(flow) + _schema_pass(flow)
    if errors:
        print(f"✗ {path.name}: {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    steps = flow.get("steps") or []
    globals_ = flow.get("global_steps") or []
    print(
        f"✓ {path.name}: valid conversation_flow "
        f"({len(steps)} steps, {len(globals_)} global node(s), entry '{flow.get('entry_step')}')"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
