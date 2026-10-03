import importlib.util
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "promote_body_writer_bridge_provenance.py"
    )
    spec = importlib.util.spec_from_file_location(
        "promote_body_writer_bridge_provenance", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _candidate(kind, register, read_instructions, write_instructions):
    return {
        "kind": kind,
        "function": "0x00700000",
        "function_name": "FUN_00700000",
        "base_register": register,
        "read_offsets": [0x48] if kind == "accumulator-to-motion" else [0x78],
        "read_offsets_hex": ["0x48"] if kind == "accumulator-to-motion" else ["0x78"],
        "write_offsets": [0x78] if kind == "accumulator-to-motion" else [0x00],
        "write_offsets_hex": ["0x78"] if kind == "accumulator-to-motion" else ["0x0"],
        "read_evidence": [
            {
                "instruction": address,
                "instruction_text": "synthetic read",
                "access": "read",
                "displacement": 0x48 if kind == "accumulator-to-motion" else 0x78,
                "displacement_hex": "0x48" if kind == "accumulator-to-motion" else "0x78",
                "lanes": ["accumulator_a"] if kind == "accumulator-to-motion" else ["motion_triplet"],
                "pcode_memory_ops": ["LOAD"],
            }
            for address in read_instructions
        ],
        "write_evidence": [
            {
                "instruction": address,
                "instruction_text": "synthetic write",
                "access": "write",
                "displacement": 0x78 if kind == "accumulator-to-motion" else 0x00,
                "displacement_hex": "0x78" if kind == "accumulator-to-motion" else "0x0",
                "lanes": ["motion_triplet"] if kind == "accumulator-to-motion" else ["origin"],
                "pcode_memory_ops": ["STORE"],
            }
            for address in write_instructions
        ],
        "same_function": True,
        "same_base_register": True,
        "body_pointer_proven": False,
        "persistent_writer_proven": False,
        "promoted": False,
    }


def _candidate_report(candidates):
    return {
        "format": "SHIFT.BodyWriterBridgeCandidates/1",
        "candidates": candidates,
    }


def _provenance(entries):
    return {
        "format": "SHIFT.GhidraBodyPointerProvenance/1",
        "entries": entries,
    }


def _entry(start, end, *, register="ECX", identity="BODY"):
    return {
        "function": "0x00700000",
        "instruction_start": start,
        "instruction_end": end,
        "base_register": register,
        "object_identity": identity,
        "evidence_level": "callsite-plus-dataflow",
        "sources": ["fixture pointer provenance"],
    }


def test_promotes_only_when_all_participating_instructions_have_body_provenance():
    module = _load_module()
    candidates = _candidate_report(
        [
            _candidate(
                "accumulator-to-motion",
                "ECX",
                ["0x00700010"],
                ["0x00700020"],
            )
        ]
    )
    provenance = _provenance([_entry("0x00700010", "0x00700020")])

    report = module.promote_body_writer_bridge_provenance(candidates, provenance)
    assert report["format"] == "SHIFT.BodyWriterBridgeProvenance/1"
    assert report["candidate_count"] == 1
    assert report["body_lane_access_pattern_proven_count"] == 1
    candidate = report["candidates"][0]
    assert candidate["body_pointer_proven"] is True
    assert candidate["body_lane_access_pattern_proven"] is True
    assert candidate["promotion_status"] == "body-lane-access-pattern-proven"
    assert candidate["persistent_writer_proven"] is False
    assert report["scope"]["native_pose_port_ready"] is False


def test_partial_instruction_coverage_fails_closed():
    module = _load_module()
    candidates = _candidate_report(
        [
            _candidate(
                "accumulator-to-motion",
                "ECX",
                ["0x00700010"],
                ["0x00700020"],
            )
        ]
    )
    provenance = _provenance([_entry("0x00700010", "0x00700010")])

    report = module.promote_body_writer_bridge_provenance(candidates, provenance)
    candidate = report["candidates"][0]
    assert candidate["body_pointer_proven"] is False
    assert candidate["body_lane_access_pattern_proven"] is False
    assert report["unresolved_candidate_count"] == 1
    by_instruction = {
        row["instruction"]: row for row in candidate["instruction_pointer_provenance"]
    }
    assert by_instruction["0x00700010"]["body_pointer_proven"] is True
    assert by_instruction["0x00700020"]["body_pointer_proven"] is False


def test_non_body_alias_is_retained_but_does_not_promote():
    module = _load_module()
    candidates = _candidate_report(
        [
            _candidate(
                "motion-to-pose",
                "ESI",
                ["0x00700030"],
                ["0x00700040"],
            )
        ]
    )
    provenance = _provenance(
        [
            _entry(
                "0x00700030",
                "0x00700040",
                register="ESI",
                identity="wheel-BODY-compatible",
            )
        ]
    )

    report = module.promote_body_writer_bridge_provenance(candidates, provenance)
    candidate = report["candidates"][0]
    assert candidate["body_lane_access_pattern_proven"] is False
    matches = candidate["instruction_pointer_provenance"][0]["matches"]
    assert matches[0]["object_identity"] == "wheel-BODY-compatible"


def test_wrong_register_does_not_prove_candidate():
    module = _load_module()
    candidates = _candidate_report(
        [
            _candidate(
                "accumulator-to-motion",
                "ECX",
                ["0x00700010"],
                ["0x00700020"],
            )
        ]
    )
    provenance = _provenance(
        [_entry("0x00700010", "0x00700020", register="ESI")]
    )

    report = module.promote_body_writer_bridge_provenance(candidates, provenance)
    assert report["body_lane_access_pattern_proven_count"] == 0
    assert all(
        row["matches"] == []
        for row in report["candidates"][0]["instruction_pointer_provenance"]
    )


def test_combined_bridge_requires_both_body_proven_stages():
    module = _load_module()
    candidates = _candidate_report(
        [
            _candidate(
                "accumulator-to-motion",
                "ECX",
                ["0x00700010"],
                ["0x00700020"],
            ),
            _candidate(
                "motion-to-pose",
                "ECX",
                ["0x00700020"],
                ["0x00700030"],
            ),
        ]
    )
    provenance = _provenance([_entry("0x00700010", "0x00700030")])

    report = module.promote_body_writer_bridge_provenance(candidates, provenance)
    assert report["combined_bridge_group_count"] == 1
    assert report["combined_body_lane_access_pattern_proven_count"] == 1
    group = report["combined_bridge_groups"][0]
    assert group["combined_body_lane_access_pattern_proven"] is True
    assert group["persistent_writer_proven"] is False


def test_rejects_wrong_candidate_format():
    module = _load_module()
    with pytest.raises(ValueError, match="expected SHIFT.BodyWriterBridgeCandidates/1"):
        module.promote_body_writer_bridge_provenance(
            {"format": "WRONG", "candidates": []},
            _provenance([]),
        )


def test_rejects_reversed_provenance_range():
    module = _load_module()
    candidates = _candidate_report(
        [
            _candidate(
                "accumulator-to-motion",
                "ECX",
                ["0x00700010"],
                ["0x00700020"],
            )
        ]
    )
    provenance = _provenance([_entry("0x00700020", "0x00700010")])
    with pytest.raises(ValueError, match="instruction range is reversed"):
        module.promote_body_writer_bridge_provenance(candidates, provenance)
