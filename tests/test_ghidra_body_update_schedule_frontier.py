import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_body_update_schedule_frontier.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_body_update_schedule_frontier", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def _function(address):
    return {
        "address": address,
        "name": f"FUN_{address[2:]}",
        "size": 64,
        "external": False,
        "thunk": False,
    }


def _call(source, instruction, target):
    return {
        "from_function": source,
        "from_name": f"FUN_{source[2:]}",
        "instruction": instruction,
        "to": target,
        "to_name": f"FUN_{target[2:]}",
        "indirect": False,
    }


def _fixture(tmp_path):
    module = _load_module()
    outer = module.ANCHORS["outer_update"]
    physics_pass = module.ANCHORS["physics_pass"]
    bridge = "0x00765470"
    tail = "0x00769ef0"
    repeated_helper = "0x007b8810"
    pass_local = "0x007b3e90"
    bridge_local = "0x007b2270"
    generic = "0x0070fe90"

    functions = set(module.ANCHORS.values()) | {
        bridge,
        tail,
        repeated_helper,
        pass_local,
        bridge_local,
        generic,
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

    rows = [
        _call(outer, "0x00770f8f", physics_pass),
        _call(outer, "0x00770fac", bridge),
        _call(outer, "0x00770fb7", repeated_helper),
        _call(outer, "0x00770fbf", physics_pass),
        _call(outer, "0x00770fdc", bridge),
        _call(outer, "0x00770fe7", repeated_helper),
        _call(
            bridge,
            "0x007657b2",
            module.ANCHORS["wheel_shared_triplet_pass"],
        ),
        _call(bridge, "0x007657bd", module.ANCHORS["sdf_solve"]),
        _call(bridge, "0x007657c8", module.ANCHORS["post_solve_writer"]),
        _call(bridge, "0x0076582a", bridge_local),
        _call(physics_pass, "0x0076d120", pass_local),
        _call(physics_pass, "0x0076d12b", module.ANCHORS["contact_factor"]),
        _call(physics_pass, "0x0076d132", module.ANCHORS["wheel_update"]),
        _call(
            physics_pass,
            "0x0076d139",
            module.ANCHORS["contact_response"],
        ),
        _call(physics_pass, "0x0076d2b1", generic),
        _call(physics_pass, "0x0076d2c1", tail),
        _call(tail, "0x0076a1c7", module.ANCHORS["contact_outer"]),
        _call(tail, "0x0076a1e8", module.ANCHORS["motion_read_gate"]),
    ]

    # Make this support helper high-fan-in. It must stay in the complete ordered
    # call list, but should not be auto-selected for targeted instruction export.
    for index in range(5):
        caller = f"0x00600{index:03x}"
        functions.add(caller)
        rows.append(_call(caller, f"0x00610{index:03x}", generic))

    _write_jsonl(
        tmp_path / "functions.jsonl", [_function(x) for x in sorted(functions)]
    )
    _write_jsonl(tmp_path / "callgraph.jsonl", rows)
    return module, bridge, tail, repeated_helper, pass_local, bridge_local, generic


def test_recovers_schedule_without_semantic_promotion(tmp_path):
    module, bridge, tail, repeated_helper, pass_local, bridge_local, generic = (
        _fixture(tmp_path)
    )
    report = module.build_body_update_schedule_frontier(tmp_path)

    assert report["format"] == "SHIFT.GhidraBodyUpdateScheduleFrontier/1"
    assert report["recovered"]["between_pass_bridge"]["address"] == bridge
    assert report["recovered"]["between_pass_bridge"]["promoted"] is False
    assert report["recovered"]["physics_pass_tail"]["address"] == tail
    assert [row["to"] for row in report["between_pass_bridge"]["required_order"]] == [
        module.ANCHORS["wheel_shared_triplet_pass"],
        module.ANCHORS["sdf_solve"],
        module.ANCHORS["post_solve_writer"],
    ]
    assert [row["to"] for row in report["physics_pass"]["required_order"]] == [
        module.ANCHORS["contact_factor"],
        module.ANCHORS["wheel_update"],
        module.ANCHORS["contact_response"],
        tail,
    ]
    assert [row["to"] for row in report["physics_pass_tail"]["required_order"]] == [
        module.ANCHORS["contact_outer"],
        module.ANCHORS["motion_read_gate"],
    ]
    assert report["scope"]["pose_integration_writer_proven"] is False
    assert report["scope"]["motion_triplet_writer_proven"] is False

    targets = report["instruction_export_addresses"]
    assert targets[:3] == [bridge, tail, repeated_helper]
    assert pass_local in targets
    assert bridge_local in targets
    assert generic not in targets


def test_fails_closed_when_outer_update_no_longer_has_two_physics_passes(tmp_path):
    module, *_ = _fixture(tmp_path)
    rows = list(module.read_jsonl(tmp_path / "callgraph.jsonl"))
    kept = [
        row
        for row in rows
        if not (
            row["from_function"] == module.ANCHORS["outer_update"]
            and row["to"] == module.ANCHORS["physics_pass"]
            and row["instruction"] == "0x00770fbf"
        )
    ]
    _write_jsonl(tmp_path / "callgraph.jsonl", kept)
    with pytest.raises(ValueError, match="exactly two direct calls"):
        module.build_body_update_schedule_frontier(tmp_path)


def test_fails_closed_when_between_pass_bridge_is_ambiguous(tmp_path):
    module, *_ = _fixture(tmp_path)
    ambiguous = "0x00760010"
    functions = list(module.read_jsonl(tmp_path / "functions.jsonl"))
    functions.append(_function(ambiguous))
    _write_jsonl(tmp_path / "functions.jsonl", functions)

    rows = list(module.read_jsonl(tmp_path / "callgraph.jsonl"))
    rows.extend(
        [
            _call(module.ANCHORS["outer_update"], "0x00770fb0", ambiguous),
            _call(module.ANCHORS["outer_update"], "0x00770fe0", ambiguous),
            _call(ambiguous, "0x00760020", module.ANCHORS["sdf_solve"]),
            _call(
                ambiguous,
                "0x00760030",
                module.ANCHORS["post_solve_writer"],
            ),
        ]
    )
    _write_jsonl(tmp_path / "callgraph.jsonl", rows)
    with pytest.raises(ValueError, match="exactly one repeated between-pass callee"):
        module.build_body_update_schedule_frontier(tmp_path)


def test_fails_closed_when_solve_and_post_solve_order_reverses(tmp_path):
    module, bridge, *_ = _fixture(tmp_path)
    rows = list(module.read_jsonl(tmp_path / "callgraph.jsonl"))
    for row in rows:
        if row["from_function"] != bridge:
            continue
        if row["to"] == module.ANCHORS["sdf_solve"]:
            row["instruction"] = "0x007657d8"
        elif row["to"] == module.ANCHORS["post_solve_writer"]:
            row["instruction"] = "0x007657c8"
    _write_jsonl(tmp_path / "callgraph.jsonl", rows)
    with pytest.raises(ValueError, match="required direct-call order"):
        module.build_body_update_schedule_frontier(tmp_path)
