import importlib.util
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_body_pointer_provenance_worklist.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_body_pointer_provenance_worklist", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _bridge_candidate(function="0x00700000", kind="accumulator-to-motion", base="ecx"):
    return {
        "kind": kind,
        "function": function,
        "function_name": f"FUN_{function[2:]}",
        "base_register": base,
        "read_evidence": [
            {
                "instruction": "0x00700010",
                "instruction_text": "FLD qword ptr [ECX + 0x48]",
                "displacement": 0x48,
                "displacement_hex": "0x48",
                "lanes": ["accumulator_a"],
                "pcode_memory_ops": ["LOAD"],
            },
            {
                "instruction": "0x00700010",
                "instruction_text": "FLD qword ptr [ECX + 0x48]",
                "displacement": 0x48,
                "displacement_hex": "0x48",
                "lanes": ["accumulator_a"],
                "pcode_memory_ops": ["LOAD"],
            },
        ],
        "write_evidence": [
            {
                "instruction": "0x00700020",
                "instruction_text": "FSTP qword ptr [ECX + 0x78]",
                "displacement": 0x78,
                "displacement_hex": "0x78",
                "lanes": ["motion_triplet"],
                "pcode_memory_ops": ["STORE"],
            }
        ],
    }


def _bridge(candidates):
    return {"format": "SHIFT.BodyWriterBridgeCandidates/1", "candidates": candidates}


def _join_candidate(function="0x00700000", kind="accumulator-to-motion", base="ECX", relation="callgraph-frontier", depth=1):
    return {
        "kind": kind,
        "function": function,
        "function_name": f"FUN_{function[2:]}",
        "base_register": base,
        "frontier_relation": relation,
        "min_depth": depth,
        "connected_subsystems": ["physics", "vehicle"],
        "adjacent_proven_slice_addresses": ["0x007b4110"],
        "slice_callers": [{"from_function": "0x007b4110"}],
        "ordered_slice_calls": [],
        "multi_anchor_caller_candidate": True,
        "indirect_call_sites": [],
    }


def _join(candidates):
    return {"format": "SHIFT.BodyWriterBridgeFrontierJoin/1", "candidates": candidates}


def test_builds_instruction_level_fail_closed_tasks():
    module = _load_module()
    report = module.build_body_pointer_provenance_worklist(
        _bridge([_bridge_candidate()]),
        _join([_join_candidate()]),
    )

    assert report["format"] == "SHIFT.BodyPointerProvenanceWorklist/1"
    assert report["candidate_work_item_count"] == 1
    assert report["function_work_item_count"] == 1
    assert report["instruction_provenance_task_count"] == 2
    assert report["function_targets"] == ["0x00700000"]

    candidate = report["candidates"][0]
    assert candidate["base_register"] == "ECX"
    assert candidate["frontier_relation"] == "callgraph-frontier"
    assert candidate["persistent_writer_proven"] is False
    assert candidate["instructions"][0]["roles"] == ["read"]
    assert candidate["instructions"][1]["roles"] == ["write"]
    assert candidate["instructions"][1]["provenance_required"] == {
        "function": "0x00700000",
        "base_register": "ECX",
        "instruction_start": "0x00700020",
        "instruction_end": "0x00700020",
        "required_object_identity": "BODY",
        "status": "unresolved",
    }
    assert report["scope"]["native_pose_port_ready"] is False


def test_orders_slice_root_before_frontier_before_outside():
    module = _load_module()
    candidates = [
        _bridge_candidate("0x00700030", base="EDI"),
        _bridge_candidate("0x00700010", base="ECX"),
        _bridge_candidate("0x00700020", base="ESI"),
    ]
    joins = [
        _join_candidate("0x00700030", base="EDI", relation="outside-selected-frontier", depth=None),
        _join_candidate("0x00700010", base="ECX", relation="proven-slice-root", depth=0),
        _join_candidate("0x00700020", base="ESI", relation="callgraph-frontier", depth=2),
    ]
    report = module.build_body_pointer_provenance_worklist(_bridge(candidates), _join(joins))
    assert [row["function"] for row in report["candidates"]] == [
        "0x00700010",
        "0x00700020",
        "0x00700030",
    ]


def test_requires_exact_function_register_kind_join_key():
    module = _load_module()
    report = module.build_body_pointer_provenance_worklist(
        _bridge([_bridge_candidate(base="ECX")]),
        _join([_join_candidate(base="ESI")]),
    )
    assert report["candidate_work_item_count"] == 0
    assert report["unmatched_candidate_count"] == 1
    assert report["function_targets"] == []


def test_duplicate_join_key_is_reported_without_changing_first_context():
    module = _load_module()
    first = _join_candidate(relation="callgraph-frontier", depth=1)
    duplicate = _join_candidate(relation="callgraph-frontier", depth=2)
    report = module.build_body_pointer_provenance_worklist(
        _bridge([_bridge_candidate()]),
        _join([first, duplicate]),
    )
    assert report["duplicate_join_key_count"] == 1
    assert report["candidates"][0]["min_depth"] == 1


def test_rejects_empty_access_evidence():
    module = _load_module()
    candidate = _bridge_candidate()
    candidate["write_evidence"] = []
    with pytest.raises(ValueError, match="write_evidence must be a non-empty list"):
        module.build_body_pointer_provenance_worklist(
            _bridge([candidate]),
            _join([_join_candidate()]),
        )


def test_rejects_wrong_formats():
    module = _load_module()
    with pytest.raises(ValueError, match="SHIFT.BodyWriterBridgeCandidates/1"):
        module.build_body_pointer_provenance_worklist(
            {"format": "WRONG", "candidates": []},
            _join([]),
        )
    with pytest.raises(ValueError, match="SHIFT.BodyWriterBridgeFrontierJoin/1"):
        module.build_body_pointer_provenance_worklist(
            _bridge([]),
            {"format": "WRONG", "candidates": []},
        )
