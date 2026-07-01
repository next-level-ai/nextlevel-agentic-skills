"""Test example for a produced conversation_flow.

Shows how to check a flow with the bundled validator: the full-spec example must be
clean, and each negative case demonstrates one class of error an author can hit.
Run: `pytest` (or `python -m pytest`) from the skill directory. No third-party deps.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_flow import validate  # noqa: E402

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "full_spec_example.json"


def load():
    return json.loads(EXAMPLE.read_text())


def test_full_spec_example_is_valid():
    assert validate(load()) == []


def test_rejects_unknown_top_level_key():
    flow = load()
    flow["surprise"] = True
    assert any("unknown top-level key 'surprise'" in e for e in validate(flow))


def test_rejects_missing_routing_field():
    flow = load()
    del flow["routing"]["continuation_directive"]
    assert any("routing missing required field 'continuation_directive'" in e for e in validate(flow))


def test_rejects_bad_transition_template():
    flow = load()
    flow["routing"]["transition_description_template"] = "Call when {oops}."
    assert any("only placeholder is {when}" in e for e in validate(flow))


def test_rejects_duplicate_step_id():
    flow = load()
    flow["steps"].append({"id": "greet", "type": "end"})
    assert any("duplicate step id 'greet'" in e for e in validate(flow))


def test_rejects_id_collision_between_step_and_global():
    flow = load()
    flow["global_steps"].append({"id": "greet", "type": "end", "when": "done"})
    assert any("duplicate step id 'greet'" in e for e in validate(flow))


def test_rejects_entry_pointing_at_global_node():
    flow = load()
    flow["entry_step"] = "say_goodbye"
    assert any("must be a regular step, not a global node" in e for e in validate(flow))


def test_rejects_entry_pointing_at_end_step():
    flow = load()
    flow["entry_step"] = "wrap_up"
    assert any("must be an llm step" in e for e in validate(flow))


def test_rejects_unknown_transition_target():
    flow = load()
    flow["steps"][0]["transitions"].append({"to": "ghost", "when": "x"})
    assert any("targets unknown step 'ghost'" in e for e in validate(flow))


def test_rejects_unknown_tool_reference():
    flow = load()
    flow["steps"][1]["tools"].append("ghost_tool")
    assert any("unknown tool 'ghost_tool'" in e for e in validate(flow))


def test_rejects_unknown_collect_field():
    flow = load()
    flow["steps"][0]["collect"].append("ghost_field")
    assert any("unknown state_field 'ghost_field'" in e for e in validate(flow))


def test_rejects_enum_on_non_string_field():
    flow = load()
    flow["state_fields"].append({"name": "flag", "type": "boolean", "description": "x", "enum": ["a"]})
    assert any("enum is only allowed for string type" in e for e in validate(flow))


def test_rejects_global_node_without_when():
    flow = load()
    del flow["global_steps"][0]["when"]
    assert any("when is required" in e for e in validate(flow))


def test_rejects_global_exclude_unknown_step():
    flow = load()
    flow["global_steps"][0]["exclude"] = ["ghost"]
    assert any("exclude references 'ghost'" in e for e in validate(flow))


def test_rejects_invalid_slug_id():
    flow = load()
    flow["steps"][0]["id"] = "Has Spaces"
    flow["entry_step"] = "Has Spaces"
    assert any("is not a valid snake_case slug" in e for e in validate(flow))


def test_rejects_http_tool_missing_url():
    flow = load()
    http_tool = next(t for t in flow["tools"] if t["kind"] == "http")
    del http_tool["request"]["url"]
    assert any("request.url is required" in e for e in validate(flow))


if __name__ == "__main__":
    # Runnable without pytest: execute every test_* and report.
    fns = {k: v for k, v in dict(globals()).items() if k.startswith("test_") and callable(v)}
    failed = 0
    for name, fn in fns.items():
        try:
            fn()
            print(f"ok   {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
