import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_vehicle_outer_update_caller_frontier.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_vehicle_outer_update_caller_frontier", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def _function(address, *, convention="__thiscall", external=False, thunk=False):
    return {
        "address": address,
        "name": f"FUN_{address[2:]}",
        "size": 64,
        "external": external,
        "thunk": thunk,
        "calling_convention": convention,
        "signature": f"undefined FUN_{address[2:]}(void)",
        "mnemonic_sha256": address[2:].rjust(64, "0")[-64:],
    }


def _call(source, instruction, target, *, indirect=False):
    return {
        "from_function": source,
        "from_name": f"FUN_{source[2:]}",
        "instruction": instruction,
        "to": target,
        "to_name": f"FUN_{target[2:]}" if target else None,
        "indirect": indirect,
    }


def _fixture(tmp_path):
    module = _load_module()
    anchor = module.OUTER_UPDATE
    caller_a = "0x00710000"
    caller_b = "0x00720000"
    parent = "0x00730000"
    grandparent = "0x00740000"
    shared_a = "0x00800010"
    shared_b = "0x00800020"
    local_a = "0x00800100"
    local_b = "0x00800200"

    functions = {
        anchor,
        caller_a,
        caller_b,
        parent,
        grandparent,
        shared_a,
        shared_b,
        local_a,
        local_b,
    }
    (tmp_path / "binary.json").write_text(
        json.dumps(
            {
                "program_name": "SHIFT.exe",
                "executable_md5": "705af8b420e5eb1e3834ac43d5533c6b",
                "language_id": "x86:LE:32:default",
                "image_base": "0x00400000",
                "pointer_size": 4,
            }
        ),
        encoding="utf-8",
    )
    _write_jsonl(
        tmp_path / "functions.jsonl",
        [_function(address) for address in sorted(functions)],
    )
    calls = [
        _call(caller_a, "0x00710010", anchor),
        _call(caller_a, "0x00710020", shared_a),
        _call(caller_a, "0x00710030", shared_b),
        _call(caller_a, "0x00710040", local_a),
        _call(caller_b, "0x00720010", anchor),
        _call(caller_b, "0x00720020", shared_a),
        _call(caller_b, "0x00720030", shared_b),
        _call(caller_b, "0x00720040", local_b),
        _call(parent, "0x00730010", caller_a),
        _call(parent, "0x00730020", caller_a),
        _call(grandparent, "0x00740010", parent),
    ]
    _write_jsonl(tmp_path / "callgraph.jsonl", calls)
    _write_jsonl(
        tmp_path / "switches.jsonl",
        [
            {
                "status": "computed-jump-candidate",
                "function": caller_b,
                "name": f"FUN_{caller_b[2:]}",
                "instruction": "0x00720008",
                "text": "JMP dword ptr [EAX*0x4 + 0x900000]",
                "destinations": ["0x00720010", "0x00720040"],
            }
        ],
    )
    return module, caller_a, caller_b, parent, grandparent, shared_a, shared_b


def test_builds_direct_caller_and_upstream_frontier(tmp_path):
    module, caller_a, caller_b, parent, grandparent, shared_a, shared_b = _fixture(
        tmp_path
    )
    report = module.build_vehicle_outer_update_caller_frontier(tmp_path)

    assert report["format"] == "SHIFT.GhidraVehicleOuterUpdateCallerFrontier/1"
    assert report["outer_update_anchor"] == module.OUTER_UPDATE
    assert report["direct_caller_count"] == 2
    assert [row["address"] for row in report["direct_callers"]] == [caller_a, caller_b]
    assert report["all_callers_invoke_outer_update_at_same_direct_call_index"] is True
    assert [row["target"] for row in report["shared_ordered_direct_callee_prefix"]] == [
        module.OUTER_UPDATE,
        shared_a,
        shared_b,
    ]

    a, b = report["direct_callers"]
    assert a["direct_incoming_count"] == 2
    assert a["ownership_status"] == "has-direct-upstream-caller"
    assert b["direct_incoming_count"] == 0
    assert b["ownership_status"] == "no-direct-upstream-caller"
    assert len(b["computed_jump_candidates"]) == 1

    assert [(row["address"], row["upstream_depth"]) for row in report["upstream_candidates"]] == [
        (parent, 1),
        (grandparent, 2),
    ]
    assert any(
        row["function"] == caller_b
        and row["status"] == "no-direct-upstream-caller-in-export"
        for row in report["blockers"]
    )
    assert report["instruction_export_addresses"] == [
        caller_a,
        caller_b,
        parent,
        grandparent,
    ]
    assert report["scope"]["direct_caller_is_vehicle_owner_proof"] is False
    assert report["scope"]["input_control_ownership_proven"] is False


def test_upstream_depth_zero_keeps_only_direct_callers(tmp_path):
    module, caller_a, caller_b, *_ = _fixture(tmp_path)
    report = module.build_vehicle_outer_update_caller_frontier(
        tmp_path, upstream_depth=0
    )
    assert report["upstream_candidate_count"] == 0
    assert report["instruction_export_addresses"] == [caller_a, caller_b]


def test_indirect_call_remains_explicit_blocker(tmp_path):
    module, caller_a, *_ = _fixture(tmp_path)
    rows = list(module.read_jsonl(tmp_path / "callgraph.jsonl"))
    rows.append(_call(caller_a, "0x00710050", None, indirect=True))
    _write_jsonl(tmp_path / "callgraph.jsonl", rows)

    report = module.build_vehicle_outer_update_caller_frontier(tmp_path)
    assert any(
        row["function"] == caller_a
        and row["instruction"] == "0x00710050"
        and row["status"] == "unresolved-indirect-call-target"
        for row in report["blockers"]
    )


def test_fails_closed_without_direct_outer_update_caller(tmp_path):
    module, *_ = _fixture(tmp_path)
    rows = [
        row
        for row in module.read_jsonl(tmp_path / "callgraph.jsonl")
        if row.get("to") != module.OUTER_UPDATE
    ]
    _write_jsonl(tmp_path / "callgraph.jsonl", rows)
    with pytest.raises(ValueError, match="no direct callers"):
        module.build_vehicle_outer_update_caller_frontier(tmp_path)


def test_fails_closed_when_caller_invokes_anchor_twice(tmp_path):
    module, caller_a, *_ = _fixture(tmp_path)
    rows = list(module.read_jsonl(tmp_path / "callgraph.jsonl"))
    rows.append(_call(caller_a, "0x00710018", module.OUTER_UPDATE))
    _write_jsonl(tmp_path / "callgraph.jsonl", rows)
    with pytest.raises(ValueError, match="expected exactly one direct call"):
        module.build_vehicle_outer_update_caller_frontier(tmp_path)


def test_requires_switch_export_for_control_flow_audit(tmp_path):
    module, *_ = _fixture(tmp_path)
    (tmp_path / "switches.jsonl").unlink()
    with pytest.raises(FileNotFoundError, match="switches.jsonl"):
        module.build_vehicle_outer_update_caller_frontier(tmp_path)


def test_validates_limits(tmp_path):
    module, *_ = _fixture(tmp_path)
    with pytest.raises(ValueError, match="upstream_depth"):
        module.build_vehicle_outer_update_caller_frontier(tmp_path, upstream_depth=-1)
    with pytest.raises(ValueError, match="max_targets"):
        module.build_vehicle_outer_update_caller_frontier(tmp_path, max_targets=0)
