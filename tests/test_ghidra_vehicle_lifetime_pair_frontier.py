import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_vehicle_lifetime_pair_frontier.py"
    )
    spec = importlib.util.spec_from_file_location("build_vehicle_lifetime_pair_frontier", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture(tmp_path, *, lifecycle_state="verified", ghidra_paired=True, paired=True):
    module = _load_module()
    lifecycle = {
        "format": module.LIFECYCLE_JOIN_FORMAT,
        "candidate_count": 1,
        "verified_lifecycle_pointer_join_count": 1 if lifecycle_state == "verified" else 0,
        "candidates": [
            {
                "function": "0x00102000",
                "vtable_store_instruction": "0x00102010",
                "stored_table_address": "0x00402200",
                "same_pointer_table_store_state": lifecycle_state,
                "receiver_source_node": "memory-source:0x00102000:0x00102030:ESI:64",
                "receiver_source_node_present_in_pointer_closure": True,
                "pointer_closure_join_state": lifecycle_state,
                "class_name": "Child",
                "descriptor": 2,
                "class_vtable_match_state": "verified",
                "join_evidence_state": lifecycle_state,
                "verified_lifecycle_pointer_join": lifecycle_state == "verified",
            }
        ],
    }
    lifecycle_path = tmp_path / "vehicle_lifecycle.json"
    _write(lifecycle_path, lifecycle)

    pair = {
        "format": module.PAIR_FORMAT,
        "class_count": 1,
        "paired_lifetime_shape_count": 1 if paired else 0,
        "ghidra_paired_lifetime_shape_count": 1 if ghidra_paired else 0,
        "classes": [
            {
                "class_name": "Child",
                "descriptor": 2,
                "paired_lifetime_shape": paired,
                "ghidra_paired_lifetime_shape": ghidra_paired,
                "factory_functions": ["FUN_00103000"],
                "initializer_candidates": ["FUN_00102000"],
                "preinitializer_helpers": ["FUN_00104000"],
                "unambiguous_preinitializer_helper": "FUN_00104000",
                "deleting_wrapper_functions": ["FUN_00105000"],
                "teardown_transition_functions": ["FUN_00102100"],
                "release_helpers": ["FUN_00106000"],
                "unambiguous_release_helper": "FUN_00106000",
                "nearest_ancestor_with_unique_vtable": "Parent",
                "own_vtable": 0x00402200,
                "ancestor_vtable": 0x00402100,
                "lifetime_evidence_blockers": [],
                "create_shapes": [],
                "delete_shapes": [],
            }
        ],
    }
    pair_path = tmp_path / "pairs.json"
    _write(pair_path, pair)
    return module, lifecycle_path, pair_path


def test_verifies_descriptor_vtable_and_ghidra_paired_lifetime_frontier(tmp_path):
    module, lifecycle, pair = _fixture(tmp_path)
    report = module.build_vehicle_lifetime_pair_frontier(lifecycle, pair)

    assert report["format"] == "SHIFT.VehicleLifetimePairFrontier/1"
    assert report["candidate_count"] == 1
    assert report["verified_frontier_count"] == 1
    row = report["candidates"][0]
    assert row["descriptor"] == 2
    assert row["stored_table_address"] == "0x00402200"
    assert row["descriptor_vtable_match_state"] == "verified"
    assert row["lifetime_pair_state"] == "verified"
    assert row["frontier_evidence_state"] == "verified"
    assert row["verified_vehicle_lifetime_pair_frontier"] is True
    assert row["factory_functions"] == ["0x00103000"]
    assert row["initializer_candidates"] == ["0x00102000"]
    assert row["deleting_wrapper_functions"] == ["0x00105000"]
    assert row["teardown_transition_functions"] == ["0x00102100"]
    assert row["allocation_transfer_proven"] is False
    assert row["same_runtime_object_across_lifetime_proven"] is False
    assert set(report["next_instruction_export_addresses"]) == {
        "0x00102000",
        "0x00102100",
        "0x00103000",
        "0x00105000",
    }


def test_source_only_pair_is_inferred_not_verified(tmp_path):
    module, lifecycle, pair = _fixture(tmp_path, ghidra_paired=False, paired=True)
    report = module.build_vehicle_lifetime_pair_frontier(lifecycle, pair)
    row = report["candidates"][0]
    assert row["lifetime_pair_state"] == "inferred"
    assert row["frontier_evidence_state"] == "inferred"
    assert row["verified_vehicle_lifetime_pair_frontier"] is False


def test_unpaired_lifetime_shape_stays_unknown(tmp_path):
    module, lifecycle, pair = _fixture(tmp_path, ghidra_paired=False, paired=False)
    report = module.build_vehicle_lifetime_pair_frontier(lifecycle, pair)
    row = report["candidates"][0]
    assert row["lifetime_pair_state"] == "unknown"
    assert row["frontier_evidence_state"] == "unknown"


def test_ambiguous_vehicle_lifecycle_join_cannot_be_strengthened(tmp_path):
    module, lifecycle, pair = _fixture(tmp_path, lifecycle_state="ambiguous")
    report = module.build_vehicle_lifetime_pair_frontier(lifecycle, pair)
    row = report["candidates"][0]
    assert row["lifetime_pair_state"] == "verified"
    assert row["frontier_evidence_state"] == "ambiguous"
    assert row["verified_vehicle_lifetime_pair_frontier"] is False


def test_descriptor_match_with_wrong_vtable_is_not_accepted(tmp_path):
    module, lifecycle, pair = _fixture(tmp_path)
    payload = json.loads(pair.read_text(encoding="utf-8"))
    payload["classes"][0]["own_vtable"] = 0x00409900
    _write(pair, payload)

    report = module.build_vehicle_lifetime_pair_frontier(lifecycle, pair)
    row = report["candidates"][0]
    assert row["descriptor"] == 2
    assert row["lifetime_pair_class_name"] is None
    assert row["descriptor_vtable_match_state"] == "unknown"
    assert row["verified_vehicle_lifetime_pair_frontier"] is False
    assert any(item["id"] == "descriptor-vtable-lifetime-pair-absent" for item in report["blockers"])


def test_duplicate_exact_descriptor_vtable_rows_stay_ambiguous(tmp_path):
    module, lifecycle, pair = _fixture(tmp_path)
    payload = json.loads(pair.read_text(encoding="utf-8"))
    duplicate = dict(payload["classes"][0])
    duplicate["class_name"] = "OtherChild"
    payload["classes"].append(duplicate)
    _write(pair, payload)

    report = module.build_vehicle_lifetime_pair_frontier(lifecycle, pair)
    assert report["candidate_count"] == 2
    assert report["verified_frontier_count"] == 0
    assert all(row["descriptor_vtable_match_state"] == "ambiguous" for row in report["candidates"])
    assert any(item["id"] == "descriptor-vtable-lifetime-pair-not-unique" for item in report["blockers"])


def test_class_name_mismatch_is_metadata_conflict_not_identity_key(tmp_path):
    module, lifecycle, pair = _fixture(tmp_path)
    payload = json.loads(pair.read_text(encoding="utf-8"))
    payload["classes"][0]["class_name"] = "RenamedMetadata"
    _write(pair, payload)

    report = module.build_vehicle_lifetime_pair_frontier(lifecycle, pair)
    row = report["candidates"][0]
    assert row["descriptor_vtable_exact_pair_count"] == 1
    assert row["class_name_metadata_match"] is False
    assert row["descriptor_vtable_match_state"] == "ambiguous"
    assert row["verified_vehicle_lifetime_pair_frontier"] is False
    assert any(item["id"] == "class-name-metadata-disagrees" for item in report["blockers"])


def test_missing_vehicle_descriptor_emits_blocker_without_guessing(tmp_path):
    module, lifecycle, pair = _fixture(tmp_path)
    payload = json.loads(lifecycle.read_text(encoding="utf-8"))
    payload["candidates"][0]["descriptor"] = None
    _write(lifecycle, payload)

    report = module.build_vehicle_lifetime_pair_frontier(lifecycle, pair)
    assert report["candidate_count"] == 0
    assert any(item["id"] == "vehicle-lifecycle-descriptor-missing" for item in report["blockers"])


def test_invalid_function_address_in_pair_fails_closed(tmp_path):
    module, lifecycle, pair = _fixture(tmp_path)
    payload = json.loads(pair.read_text(encoding="utf-8"))
    payload["classes"][0]["factory_functions"] = ["not-an-address"]
    _write(pair, payload)

    with pytest.raises(ValueError, match="factory_functions: invalid function address"):
        module.build_vehicle_lifetime_pair_frontier(lifecycle, pair)


def test_input_format_drift_fails_closed(tmp_path):
    module, lifecycle, pair = _fixture(tmp_path)
    payload = json.loads(pair.read_text(encoding="utf-8"))
    payload["format"] = "SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/0"
    _write(pair, payload)

    with pytest.raises(ValueError, match="expected SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1"):
        module.build_vehicle_lifetime_pair_frontier(lifecycle, pair)
