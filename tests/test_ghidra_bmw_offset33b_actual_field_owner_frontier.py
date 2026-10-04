from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_offset33b_actual_field_owner_frontier.py"
SPEC = importlib.util.spec_from_file_location("bmw_actual_field_owner", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _input(tmp_path: Path, *, consume_actual: bool = True, consume_old: bool = False) -> Path:
    path = tmp_path / "memory.json"
    report = {
        "format": MODULE.INPUT_FORMAT,
        "ready": True,
        "producer": {
            "function": MODULE.PRODUCER,
            "mnemonic_sha256": MODULE.PRODUCER_MNEMONIC_SHA256,
        },
        "known_semantic_reductions": {
            "additional_mass_first_bootstrap": {
                "proof_format": MODULE.ACTUAL_ZERO_FORMAT,
                "proof_object_base": "actual PhysicsParticipant",
                "manager_record_plus_0xba0_reused": False,
                "numeric_value_proven": True,
                "value": 0.0,
            }
        },
        "analysis": {
            "exact_object_field_worklist": [
                {
                    "base_origin_expression_set": ["entry:ECX"],
                    "displacement": 0x33A8,
                    "load_width": 8,
                    "load_node_ids": ["0x0076b300:0"],
                    "load_instructions": ["0x0076b300"],
                    "feeds_offset33b_fields": ["HDVehicle+0x33b0"],
                    "semantic_owner_or_resource": None,
                    "semantic_field_name": None,
                    "semantic_join_ready": False,
                },
                {
                    "base_origin_expression_set": ["memory:[entry:ECX+0x3fe8]"],
                    "displacement": 0x500,
                    "load_width": 4,
                    "load_node_ids": ["0x0076b320:0"],
                    "load_instructions": ["0x0076b320"],
                    "feeds_offset33b_fields": ["HDVehicle+0x33b8"],
                    "semantic_owner_or_resource": None,
                    "semantic_field_name": None,
                    "semantic_join_ready": False,
                },
                {
                    "base_origin_expression_set": ["entry:EAX", "derived:unknown"],
                    "displacement": 0x120,
                    "load_width": 8,
                    "load_node_ids": ["0x0076b340:0"],
                    "load_instructions": ["0x0076b340"],
                    "feeds_offset33b_fields": ["HDVehicle+0x33c0"],
                    "semantic_owner_or_resource": None,
                    "semantic_field_name": None,
                    "semantic_join_ready": False,
                },
            ]
        },
        "handoff": {
            "offset33b_store_provenance_ready": True,
            "offset33b_memory_LOAD_frontier_ready": True,
            "offset33b_exact_memory_field_worklist_ready": True,
            "offset33b_actual_additional_mass_bootstrap_zero_proof_consumed": consume_actual,
            "offset33b_additional_mass_bootstrap_zero_proof_consumed": consume_old,
            "offset33b_additional_mass_machine_LOAD_join_ready": False,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "historical_manager_record_zero_proof_consumed": consume_old,
            "actual_object_allocator_zero_proof_consumed": consume_actual,
        },
    }
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_classifies_direct_indirect_and_unresolved_owner_domains(tmp_path):
    report = MODULE.analyze(_input(tmp_path))
    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    analysis = report["analysis"]
    assert analysis["direct_HDVehicle_field_count"] == 1
    assert analysis["indirect_owner_slot_count"] == 1
    assert analysis["unresolved_owner_group_count"] == 1
    direct = analysis["direct_HDVehicle_fields"][0]
    assert direct["exact_owner_field_reference"] == "HDVehicle+0x33a8"
    assert direct["owner_join_ready"] is True
    indirect = analysis["indirect_owner_slots"][0]
    assert indirect["owner_join_ready"] is False
    assert indirect["HDV_VDF_SDF_tire_identity_assumed"] is False
    assert report["known_semantic_reductions"]["historical_manager_record_zero_used"] is False
    assert report["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False


def test_rejects_historical_zero_proof_consumption(tmp_path):
    with pytest.raises(ValueError, match="historical manager-record zero proof was consumed"):
        MODULE.analyze(_input(tmp_path, consume_old=True))


def test_requires_actual_object_zero_proof_consumption(tmp_path):
    with pytest.raises(ValueError, match="offset33b_actual_additional_mass_bootstrap_zero_proof_consumed is not ready"):
        MODULE.analyze(_input(tmp_path, consume_actual=False))


def test_rejects_wrong_actual_zero_proof_format(tmp_path):
    path = _input(tmp_path)
    report = json.loads(path.read_text(encoding="utf-8"))
    report["known_semantic_reductions"]["additional_mass_first_bootstrap"]["proof_format"] = "SHIFT.BMWOffset33bAdditionalMassBootstrapZero/1"
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="additional-mass reduction proof format drift"):
        MODULE.analyze(path)


def test_rejects_preclaimed_semantic_field(tmp_path):
    path = _input(tmp_path)
    report = json.loads(path.read_text(encoding="utf-8"))
    report["analysis"]["exact_object_field_worklist"][0]["semantic_field_name"] = "guessed"
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="unexpectedly preclaims semantic identity"):
        MODULE.analyze(path)
