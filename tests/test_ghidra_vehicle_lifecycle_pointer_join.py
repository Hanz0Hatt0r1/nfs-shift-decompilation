import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_vehicle_lifecycle_pointer_join.py"
    )
    spec = importlib.util.spec_from_file_location("build_vehicle_lifecycle_pointer_join", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture(tmp_path, *, alias_state="verified", include_node=True, function="0x00102000"):
    module = _load_module()
    vtable = "0x00402200"
    receiver_instruction = "0x00102030" if function == "0x00102000" else "0x00102130"
    store_instruction = "0x00102010" if function == "0x00102000" else "0x00102110"
    source_node = f"memory-source:{function}:{receiver_instruction}:ESI:64"

    pointer = {
        "format": module.POINTER_FORMAT,
        "upper_caller": "0x007155e9",
        "nodes": (
            [
                {
                    "id": source_node,
                    "kind": "register-relative-load",
                    "function": function,
                    "instruction": receiver_instruction,
                    "base_register": "ESI",
                    "displacement": 64,
                    "object_identity_proven": False,
                }
            ]
            if include_node
            else []
        ),
        "edges": [],
    }
    pointer_path = tmp_path / "pointer.json"
    _write(pointer_path, pointer)

    alias = {
        "format": module.ALIAS_FORMAT,
        "candidate_count": 1,
        "verified_same_pointer_table_store_count": 1 if alias_state == "verified" else 0,
        "verified_same_pointer_offset_zero_table_store_count": 1 if alias_state == "verified" else 0,
        "candidates": [
            {
                "function": function,
                "function_name": f"FUN_{function[2:]}",
                "receiver_source_instruction": receiver_instruction,
                "receiver_source_base_register": "ESI",
                "receiver_source_displacement": 64,
                "receiver_source_displacement_hex": "0x40",
                "vtable_store_instruction": store_instruction,
                "store_shape": {
                    "instruction": store_instruction,
                    "status": "exact-literal-heuristic-table-address-store",
                    "evidence_state": "verified",
                    "stored_address": vtable,
                    "stored_address_matches_reference": True,
                    "destination_base_register": "ESI",
                    "destination_displacement": 0,
                    "destination_displacement_hex": "0x0",
                },
                "base_register_value_continuity": {
                    "status": (
                        "linear-base-register-value-stable"
                        if alias_state == "verified"
                        else "control-flow-or-call-barrier"
                    ),
                    "evidence_state": alias_state,
                },
                "destination_base_matches_receiver_source_base": True,
                "same_pointer_table_store_state": alias_state,
                "same_pointer_offset_zero_table_store_verified": alias_state == "verified",
                "heuristic_table_identity_state": "ambiguous",
                "class_identity_proven": False,
            }
        ],
    }
    alias_path = tmp_path / "alias.json"
    _write(alias_path, alias)

    lifecycle = {
        "format": module.LIFECYCLE_FORMAT,
        "targets": [
            {
                "class_name": "Child",
                "descriptor": 2,
                "own_vtable": int(vtable, 16),
                "initializer_candidate": "FUN_00102000",
                "initializer_writes_own_vtable": True,
                "initializer_callers": [
                    {"function": "FUN_00103000", "ghidra_direct_call": True}
                ],
                "own_vtable_writer_functions": ["FUN_00102000", "FUN_00102100"],
                "teardown_transition_candidates": [
                    {
                        "function": "FUN_00102100",
                        "evidence_kind": "own-vtable-write-followed-by-call-to-ancestor-vtable-writer",
                    }
                ],
                "complete": True,
                "missing": [],
            }
        ],
    }
    lifecycle_path = tmp_path / "lifecycle.json"
    _write(lifecycle_path, lifecycle)
    return module, pointer_path, alias_path, lifecycle_path, source_node


def test_joins_verified_same_pointer_alias_to_unique_lifecycle_vtable(tmp_path):
    module, pointer, alias, lifecycle, source_node = _fixture(tmp_path)
    report = module.build_vehicle_lifecycle_pointer_join(pointer, alias, lifecycle)

    assert report["format"] == "SHIFT.VehicleLifecyclePointerJoin/1"
    assert report["candidate_count"] == 1
    assert report["verified_lifecycle_pointer_join_count"] == 1
    row = report["candidates"][0]
    assert row["stored_table_address"] == "0x00402200"
    assert row["receiver_source_node"] == source_node
    assert row["receiver_source_node_present_in_pointer_closure"] is True
    assert row["pointer_closure_join_state"] == "verified"
    assert row["class_name"] == "Child"
    assert row["class_vtable_match_state"] == "verified"
    assert row["lifecycle_role"]["role"] == "initializer-candidate"
    assert row["verified_lifecycle_pointer_join"] is True
    assert row["vptr_semantics_proven"] is False
    assert row["constructor_semantics_proven"] is False
    assert row["whole_lifetime_class_identity_proven"] is False
    assert set(report["next_instruction_export_addresses"]) == {
        "0x00102100",
        "0x00103000",
    }


def test_missing_exact_pointer_closure_node_keeps_join_unknown(tmp_path):
    module, pointer, alias, lifecycle, _ = _fixture(tmp_path, include_node=False)
    report = module.build_vehicle_lifecycle_pointer_join(pointer, alias, lifecycle)
    row = report["candidates"][0]
    assert row["same_pointer_table_store_state"] == "verified"
    assert row["pointer_closure_join_state"] == "unknown"
    assert row["verified_lifecycle_pointer_join"] is False
    assert any(
        item["id"] == "alias-receiver-source-absent-from-pointer-closure"
        for item in report["blockers"]
    )


def test_ambiguous_local_alias_is_not_promoted_by_class_match(tmp_path):
    module, pointer, alias, lifecycle, _ = _fixture(tmp_path, alias_state="ambiguous")
    report = module.build_vehicle_lifecycle_pointer_join(pointer, alias, lifecycle)
    row = report["candidates"][0]
    assert row["class_vtable_match_state"] == "verified"
    assert row["pointer_closure_join_state"] == "ambiguous"
    assert row["join_evidence_state"] == "ambiguous"
    assert report["verified_lifecycle_pointer_join_count"] == 0
    assert any(
        item["id"] == "local-table-pointer-alias-not-verified"
        for item in report["blockers"]
    )


def test_duplicate_class_vtable_stays_ambiguous(tmp_path):
    module, pointer, alias, lifecycle, _ = _fixture(tmp_path)
    payload = json.loads(lifecycle.read_text(encoding="utf-8"))
    duplicate = dict(payload["targets"][0])
    duplicate["class_name"] = "OtherChild"
    duplicate["descriptor"] = 3
    payload["targets"].append(duplicate)
    _write(lifecycle, payload)

    report = module.build_vehicle_lifecycle_pointer_join(pointer, alias, lifecycle)
    assert report["candidate_count"] == 2
    assert report["verified_lifecycle_pointer_join_count"] == 0
    assert all(row["class_vtable_match_state"] == "ambiguous" for row in report["candidates"])
    assert any(item["id"] == "class-vtable-match-not-unique" for item in report["blockers"])


def test_stored_table_absent_from_lifecycle_evidence_stays_unknown(tmp_path):
    module, pointer, alias, lifecycle, _ = _fixture(tmp_path)
    payload = json.loads(lifecycle.read_text(encoding="utf-8"))
    payload["targets"] = []
    _write(lifecycle, payload)

    report = module.build_vehicle_lifecycle_pointer_join(pointer, alias, lifecycle)
    assert report["candidate_count"] == 1
    row = report["candidates"][0]
    assert row["class_name"] is None
    assert row["class_vtable_match_state"] == "unknown"
    assert row["verified_lifecycle_pointer_join"] is False
    assert any(item["id"] == "stored-table-absent-from-lifecycle-evidence" for item in report["blockers"])


def test_teardown_candidate_role_remains_semantically_ambiguous(tmp_path):
    module, pointer, alias, lifecycle, _ = _fixture(tmp_path, function="0x00102100")
    report = module.build_vehicle_lifecycle_pointer_join(pointer, alias, lifecycle)
    row = report["candidates"][0]
    assert row["verified_lifecycle_pointer_join"] is True
    assert row["lifecycle_role"]["role"] == "teardown-transition-candidate"
    assert row["lifecycle_role"]["evidence_state"] == "ambiguous"
    assert row["destructor_semantics_proven"] is False


def test_verified_alias_with_unverified_store_shape_fails_closed(tmp_path):
    module, pointer, alias, lifecycle, _ = _fixture(tmp_path)
    payload = json.loads(alias.read_text(encoding="utf-8"))
    payload["candidates"][0]["store_shape"]["evidence_state"] = "ambiguous"
    _write(alias, payload)

    with pytest.raises(ValueError, match="verified alias lacks verified exact literal table STORE"):
        module.build_vehicle_lifecycle_pointer_join(pointer, alias, lifecycle)


def test_verified_alias_without_base_match_fails_closed(tmp_path):
    module, pointer, alias, lifecycle, _ = _fixture(tmp_path)
    payload = json.loads(alias.read_text(encoding="utf-8"))
    payload["candidates"][0]["destination_base_matches_receiver_source_base"] = False
    _write(alias, payload)

    with pytest.raises(ValueError, match="verified alias lacks base-register match"):
        module.build_vehicle_lifecycle_pointer_join(pointer, alias, lifecycle)


def test_input_format_drift_fails_closed(tmp_path):
    module, pointer, alias, lifecycle, _ = _fixture(tmp_path)
    payload = json.loads(alias.read_text(encoding="utf-8"))
    payload["format"] = "SHIFT.VehicleVtablePointerAlias/0"
    _write(alias, payload)

    with pytest.raises(ValueError, match="expected SHIFT.VehicleVtablePointerAlias/1"):
        module.build_vehicle_lifecycle_pointer_join(pointer, alias, lifecycle)
