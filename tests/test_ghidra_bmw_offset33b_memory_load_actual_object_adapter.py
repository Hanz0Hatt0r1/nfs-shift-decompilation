from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_offset33b_memory_load_provenance_actual_object.py"
SPEC = importlib.util.spec_from_file_location("bmw_memory_actual_adapter", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _proof(tmp_path: Path, *, fmt: str | None = None, manager_reused: bool = False) -> Path:
    path = tmp_path / "actual_zero.json"
    path.write_text(
        json.dumps(
            {
                "format": fmt or MODULE.ACTUAL_ADDITIONAL_MASS_FORMAT,
                "ready": True,
                "object_graph": {
                    "actual_participant_allocation_size": 0x2B90,
                    "embedded_vehicle_offset": 0x340,
                    "participant_additional_mass_offset": 0xBA0,
                    "vehicle_additional_mass_offset": 0x860,
                    "manager_record_plus_0xba0_is_not_the_proven_storage": True,
                },
                "allocation_proof": {
                    "requested_flags": 0x20,
                    "zero_fill_operation": "memset(allocation, 0, requested_size)",
                },
                "proven_value": {"type": "float32", "bits": "0x00000000", "value": 0.0},
                "handoff": {
                    "offset33b_actual_additional_mass_bootstrap_zero_ready": True,
                    "offset33b_additional_mass_term_can_be_elided_for_first_bootstrap": True,
                    "BMW_numeric_offset33b_ready": False,
                    "vehicle_world_transform_ready": False,
                },
                "scope": {"retracted_manager_record_zero_claim_reused": manager_reused},
            }
        ),
        encoding="utf-8",
    )
    return path


def test_accepts_only_actual_object_allocator_zero_proof(tmp_path):
    report = MODULE.validate_actual_additional_mass_proof(_proof(tmp_path))
    assert report["format"] == MODULE.ACTUAL_ADDITIONAL_MASS_FORMAT
    assert report["proven_value"]["value"] == 0.0


def test_rejects_historical_contract_format(tmp_path):
    with pytest.raises(ValueError, match="expected SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1"):
        MODULE.validate_actual_additional_mass_proof(
            _proof(tmp_path, fmt="SHIFT.BMWOffset33bAdditionalMassBootstrapZero/1")
        )


def test_rejects_manager_record_reuse(tmp_path):
    with pytest.raises(ValueError, match="retracted manager-record zero claim was reused"):
        MODULE.validate_actual_additional_mass_proof(_proof(tmp_path, manager_reused=True))


def test_adapter_marks_output_as_actual_object_only(tmp_path, monkeypatch):
    proof = _proof(tmp_path)

    def fake_legacy(store, instructions, proof_path):
        normalized = MODULE._legacy._validate_additional_mass_proof(proof_path)
        root = normalized["proof"]["offset33b_root"]
        alias = normalized["proof"]["storage_alias"]
        return {
            "format": MODULE.FORMAT,
            "ready": True,
            "known_semantic_reductions": {
                "additional_mass_first_bootstrap": {
                    "semantic_name": root["semantic_name"],
                    "participant_storage": root["participant_storage"],
                    "vehicle_alias_storage": root["vehicle_alias_storage"],
                    "participant_offset": alias["participant_additional_mass_offset"],
                    "vehicle_offset": alias["vehicle_additional_mass_offset"],
                    "value_type": root["value_type"],
                    "value": root["value"],
                    "numeric_value_proven": True,
                    "term_elidable_for_first_bootstrap": True,
                    "machine_LOAD_pointer_identity_joined": False,
                }
            },
            "handoff": {
                "offset33b_additional_mass_bootstrap_zero_proof_consumed": True,
                "BMW_numeric_offset33b_ready": False,
            },
            "scope": {},
            "inputs": {"additional_mass_proof": str(proof_path)},
        }

    monkeypatch.setattr(MODULE._legacy, "analyze_bmw_offset33b_memory_load_provenance", fake_legacy)
    report = MODULE.analyze(tmp_path / "stores.json", tmp_path / "instructions.jsonl", proof)

    reduction = report["known_semantic_reductions"]["additional_mass_first_bootstrap"]
    assert reduction["proof_format"] == MODULE.ACTUAL_ADDITIONAL_MASS_FORMAT
    assert reduction["proof_object_base"] == "actual PhysicsParticipant"
    assert reduction["manager_record_plus_0xba0_reused"] is False
    assert report["handoff"]["offset33b_additional_mass_bootstrap_zero_proof_consumed"] is False
    assert report["handoff"]["offset33b_actual_additional_mass_bootstrap_zero_proof_consumed"] is True
    assert report["scope"]["historical_manager_record_zero_proof_consumed"] is False
    assert report["scope"]["actual_object_allocator_zero_proof_consumed"] is True
    assert "additional_mass_proof" not in report["inputs"]
    assert report["inputs"]["actual_additional_mass_proof"] == str(proof)
