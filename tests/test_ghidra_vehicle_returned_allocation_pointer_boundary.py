import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_vehicle_returned_allocation_pointer_boundary.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_returned_allocation_pointer_boundary", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _fixture(
    tmp_path,
    *,
    static_complete=True,
    static_allocation=True,
    static_function="FUN_00638020",
    source_allocation=True,
    catalog_all_eligible=True,
):
    module = _load_module()
    targets = ["0x00639000", "0x0063a000"]

    frontier = _write(
        tmp_path / "frontier.json",
        {
            "format": module.FRONTIER_FORMAT,
            "all_backend_machine_return_origins_resolved": True,
            "next_backend_return_target_count": 2,
            "next_backend_return_targets": targets,
            "backends": [
                {
                    "address": module.ALLOCATION_BACKEND_ADDRESS,
                    "name": module.ALLOCATION_BACKEND,
                    "exit_count": 1,
                    "machine_return_origins_resolved": True,
                    "allocated_pointer_return_proven": False,
                },
                {
                    "address": "0x006382b0",
                    "name": "FUN_006382b0",
                    "exit_count": 1,
                    "machine_return_origins_resolved": True,
                    "allocated_pointer_return_proven": False,
                },
            ],
            "vehicle_create_bridges": [
                {
                    "descriptor": 2,
                    "vehicle_pointer_source_node": "memory-source:0x00715700:0x00715730:ESI:64",
                    "allocation_request_value": 56,
                    "create_backend_return_frontier_state": "verified",
                    "backend_return_value_semantics_state": "unknown",
                }
            ],
        },
    )

    target_rows = [
        {
            "address": targets[0],
            "present": True,
            "instruction_export_eligible": True,
            "returned_allocation_pointer_role_proven": False,
        },
        {
            "address": targets[1],
            "present": True,
            "instruction_export_eligible": catalog_all_eligible,
            "returned_allocation_pointer_role_proven": False,
        },
    ]
    eligible = [row["address"] for row in target_rows if row["instruction_export_eligible"]]
    catalog = _write(
        tmp_path / "catalog.json",
        {
            "format": module.CATALOG_FORMAT,
            "target_count": 2,
            "targets": target_rows,
            "all_targets_present_in_functions": True,
            "all_targets_instruction_export_eligible": catalog_all_eligible,
            "instruction_export_address_count": len(eligible),
            "instruction_export_addresses": eligible,
        },
    )

    static = _write(
        tmp_path / "static.json",
        {
            "format": module.STATIC_FORMAT,
            "static_evidence_chain_complete": static_complete,
            "proven_physical_roles": {
                "allocation_size": {
                    "proven": static_allocation,
                    "function": static_function,
                    "entry_storage": "EDX:4",
                    "semantic_anchor": "allocation diagnostic `%d`",
                }
            },
            "scope": {
                "allocator_abi_proven": False,
                "operator_new_identity_proven": False,
            },
        },
    )

    allocation_profile = (
        {
            "proven_callsite_count": 3,
            "source_argument_indices": [0],
            "source_argument_index_consistent": True,
            "source_argument_index": 0,
            "observed_source_expressions": ["size"],
            "caller_count": 3,
            "callers": ["FUN_00100000"],
        }
        if source_allocation
        else None
    )
    source = _write(
        tmp_path / "source.json",
        {
            "format": module.SOURCE_FORMAT,
            "allocation_size_role_proven": source_allocation,
            "semantic_profiles_consistent": True,
            "wrapper_profiles": [
                {
                    "wrapper": module.CREATE_HELPER,
                    "allocation_size": allocation_profile,
                    "released_pointer": None,
                    "proven_source_roles": ["allocation-size"] if source_allocation else [],
                    "unresolved_source_roles": ["pool-selector", "alignment", "ownership"],
                    "blockers": [],
                }
            ],
            "scope": {
                "allocator_abi_proven": False,
                "operator_new_identity_proven": False,
                "ownership_semantics_proven": False,
            },
        },
    )
    return module, frontier, catalog, static, source


def test_strong_argument_and_machine_evidence_still_leaves_return_semantics_unknown(tmp_path):
    module, frontier, catalog, static, source = _fixture(tmp_path)
    report = module.build_vehicle_returned_allocation_pointer_boundary(
        frontier, catalog, static, source
    )

    assert report["format"] == "SHIFT.VehicleReturnedAllocationPointerBoundary/1"
    assert report["allocation_backend_machine_return_origin_state"] == "verified"
    assert report["static_allocation_facts"]["allocation_size_role_proven"] is True
    assert report["source_allocation_size_role_proven"] is True
    assert report["required_instruction_targets"] == ["0x00639000", "0x0063a000"]
    assert report["returned_allocation_pointer_role_state"] == "unknown"
    assert report["returned_allocation_pointer_role_proven"] is False
    assert "returned_allocation_pointer_semantic_role_not_proven" in report["blockers"]

    requirements = {row["id"]: row for row in report["proof_requirements"]}
    assert requirements["machine-return-origin"]["satisfied"] is True
    assert requirements["allocation-size-physical-role"]["satisfied"] is True
    assert requirements["allocation-size-source-role"]["satisfied"] is True
    assert requirements["inner-target-instruction-worklist"]["satisfied"] is True
    assert requirements["returned-allocation-pointer-semantic-role"]["satisfied"] is False

    joined = report["vehicle_create_bridges"][0]
    assert joined["vehicle_pointer_source_node"] == "memory-source:0x00715700:0x00715730:ESI:64"
    assert joined["allocation_request_value"] == 56
    assert joined["returned_allocation_pointer_role_state"] == "unknown"
    assert joined["returned_allocation_pointer_role_proven"] is False
    assert report["scope"]["operator_new_identity_proven"] is False
    assert report["scope"]["same_runtime_object_as_vehicle_update_proven"] is False


def test_incomplete_static_chain_is_reported_without_changing_semantic_boundary(tmp_path):
    module, frontier, catalog, static, source = _fixture(tmp_path, static_complete=False)
    report = module.build_vehicle_returned_allocation_pointer_boundary(
        frontier, catalog, static, source
    )
    assert "static_memory_evidence_chain_incomplete" in report["blockers"]
    assert report["returned_allocation_pointer_role_proven"] is False


def test_missing_allocation_size_roles_are_independent_blockers(tmp_path):
    module, frontier, catalog, static, source = _fixture(
        tmp_path, static_allocation=False, source_allocation=False
    )
    report = module.build_vehicle_returned_allocation_pointer_boundary(
        frontier, catalog, static, source
    )
    assert "allocation_size_physical_role_not_proven" in report["blockers"]
    assert "FUN_00886900_source_allocation_size_role_not_proven" in report["blockers"]
    assert "returned_allocation_pointer_semantic_role_not_proven" in report["blockers"]


def test_static_allocation_role_must_remain_at_exact_backend(tmp_path):
    module, frontier, catalog, static, source = _fixture(
        tmp_path, static_function="FUN_006382b0"
    )
    report = module.build_vehicle_returned_allocation_pointer_boundary(
        frontier, catalog, static, source
    )
    assert "allocation_size_role_not_at_FUN_00638020" in report["blockers"]


def test_noneligible_inner_target_is_preserved_as_instruction_blocker(tmp_path):
    module, frontier, catalog, static, source = _fixture(
        tmp_path, catalog_all_eligible=False
    )
    report = module.build_vehicle_returned_allocation_pointer_boundary(
        frontier, catalog, static, source
    )
    assert report["required_instruction_targets"] == ["0x00639000"]
    assert "one_or_more_return_origin_targets_not_instruction_export_eligible" in report["blockers"]
    assert report["returned_allocation_pointer_role_proven"] is False


def test_target_catalog_must_match_exact_return_origin_frontier(tmp_path):
    module, frontier, catalog, static, source = _fixture(tmp_path)
    payload = json.loads(catalog.read_text(encoding="utf-8"))
    payload["targets"][1]["address"] = "0x0063b000"
    payload["instruction_export_addresses"][1] = "0x0063b000"
    _write(catalog, payload)
    with pytest.raises(ValueError, match="does not match"):
        module.build_vehicle_returned_allocation_pointer_boundary(
            frontier, catalog, static, source
        )


def test_catalog_cannot_preclaim_return_pointer_semantics(tmp_path):
    module, frontier, catalog, static, source = _fixture(tmp_path)
    payload = json.loads(catalog.read_text(encoding="utf-8"))
    payload["targets"][0]["returned_allocation_pointer_role_proven"] = True
    _write(catalog, payload)
    with pytest.raises(ValueError, match="unexpectedly claims"):
        module.build_vehicle_returned_allocation_pointer_boundary(
            frontier, catalog, static, source
        )


def test_backend_frontier_cannot_preclaim_return_pointer_semantics(tmp_path):
    module, frontier, catalog, static, source = _fixture(tmp_path)
    payload = json.loads(frontier.read_text(encoding="utf-8"))
    payload["backends"][0]["allocated_pointer_return_proven"] = True
    _write(frontier, payload)
    with pytest.raises(ValueError, match="unexpectedly claims"):
        module.build_vehicle_returned_allocation_pointer_boundary(
            frontier, catalog, static, source
        )


def test_duplicate_create_helper_source_profile_fails_closed(tmp_path):
    module, frontier, catalog, static, source = _fixture(tmp_path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["wrapper_profiles"].append(dict(payload["wrapper_profiles"][0]))
    _write(source, payload)
    with pytest.raises(ValueError, match="duplicate FUN_00886900"):
        module.build_vehicle_returned_allocation_pointer_boundary(
            frontier, catalog, static, source
        )


def test_targets_out_preserves_exact_remaining_instruction_targets(tmp_path):
    module, frontier, catalog, static, source = _fixture(tmp_path)
    report = module.build_vehicle_returned_allocation_pointer_boundary(
        frontier, catalog, static, source
    )
    output = tmp_path / "targets.txt"
    output.write_text(
        "".join(address + "\n" for address in report["required_instruction_targets"]),
        encoding="utf-8",
    )
    assert output.read_text(encoding="utf-8") == "0x00639000\n0x0063a000\n"
