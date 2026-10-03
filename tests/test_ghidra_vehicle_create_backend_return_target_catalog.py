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
        / "build_vehicle_create_backend_return_target_catalog.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_create_backend_return_target_catalog", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _write_jsonl(path, values):
    path.write_text("".join(json.dumps(value) + "\n" for value in values), encoding="utf-8")
    return path


def _function(address, name, *, external=False):
    return {
        "address": address,
        "name": name,
        "signature": f"void * {name}(void)",
        "calling_convention": "__fastcall",
        "parameters": [],
        "external": external,
        "size": 48,
        "mnemonic_sha256": "a" * 64,
    }


def _frontier(module, targets=None, *, resolved=True):
    targets = ["0x00639000", "0x0063a000"] if targets is None else targets
    return {
        "format": module.FRONTIER_FORMAT,
        "all_backend_machine_return_origins_resolved": resolved,
        "next_backend_return_target_count": len(targets),
        "next_backend_return_targets": targets,
        "vehicle_create_bridges": [
            {
                "descriptor": 2,
                "vehicle_pointer_source_node": "memory-source:0x00715700:0x00715730:ESI:64",
                "allocation_request_value": 56,
                "create_backend_return_frontier_state": "verified",
                "backend_return_value_semantics_state": "unknown",
            }
        ],
    }


def _fixture(tmp_path, *, functions=None, frontier=None):
    module = _load_module()
    frontier_path = _write_json(
        tmp_path / "frontier.json",
        _frontier(module) if frontier is None else frontier,
    )
    root = tmp_path / "ghidra"
    root.mkdir()
    if functions is None:
        functions = [
            _function("0x00639000", "FUN_00639000"),
            _function("0x0063a000", "FUN_0063a000"),
            _function("0x00639100", "FUN_00639100"),
            _function("0x00630000", "FUN_00630000"),
        ]
    _write_jsonl(root / "functions.jsonl", functions)
    _write_jsonl(
        root / "callgraph.jsonl",
        [
            {
                "from_function": "0x00630000",
                "instruction": "0x00630020",
                "to": "0x00639000",
                "to_name": "FUN_00639000",
                "indirect": False,
            },
            {
                "from_function": "0x00639000",
                "instruction": "0x00639010",
                "to": "0x00639100",
                "to_name": "FUN_00639100",
                "indirect": False,
            },
            {
                "from_function": "0x00639000",
                "instruction": "0x00639014",
                "to": "0x00639999",
                "to_name": None,
                "indirect": True,
            },
        ],
    )
    _write_jsonl(
        root / "strings_xrefs.jsonl",
        [
            {
                "address": "0x00aec0e8",
                "value": "Unable to allocate %d bytes of memory from the pool (%s)",
                "xrefs": ["0x00639020"],
                "functions": ["0x00639000"],
            },
            {
                "address": "0x00abc100",
                "value": "ordinary target text",
                "xrefs": ["0x0063a010"],
                "functions": ["0x0063a000"],
            },
        ],
    )
    return module, frontier_path, root


def test_catalogs_exact_targets_and_emits_static_instruction_worklist(tmp_path):
    module, frontier, root = _fixture(tmp_path)
    report = module.build_vehicle_create_backend_return_target_catalog(frontier, root)

    assert report["format"] == "SHIFT.VehicleCreateBackendReturnTargetCatalog/1"
    assert report["target_count"] == 2
    assert report["all_targets_present_in_functions"] is True
    assert report["all_targets_instruction_export_eligible"] is True
    assert report["instruction_export_addresses"] == ["0x00639000", "0x0063a000"]

    first = report["targets"][0]
    assert first["address"] == "0x00639000"
    assert first["name"] == "FUN_00639000"
    assert first["incoming_direct_calls"] == [
        {
            "from": "0x00630000",
            "instruction": "0x00630020",
            "to": "0x00639000",
            "to_name": "FUN_00639000",
        }
    ]
    assert first["outgoing_direct_calls"] == [
        {
            "from": "0x00639000",
            "instruction": "0x00639010",
            "to": "0x00639100",
            "to_name": "FUN_00639100",
        }
    ]
    assert first["allocation_diagnostic_text_reference_present"] is True
    assert first["returned_allocation_pointer_role_proven"] is False
    assert report["scope"]["allocation_diagnostic_text_is_return_role_proof"] is False

    joined = report["vehicle_create_bridges"][0]
    assert joined["vehicle_pointer_source_node"] == "memory-source:0x00715700:0x00715730:ESI:64"
    assert joined["allocation_request_value"] == 56


def test_indirect_callgraph_edges_are_not_promoted_to_direct_context(tmp_path):
    module, frontier, root = _fixture(tmp_path)
    report = module.build_vehicle_create_backend_return_target_catalog(frontier, root)
    first = report["targets"][0]
    assert all(row["to"] != "0x00639999" for row in first["outgoing_direct_calls"])


def test_absent_target_is_reported_and_not_emitted_for_instruction_export(tmp_path):
    module = _load_module()
    functions = [_function("0x00639000", "FUN_00639000")]
    module, frontier, root = _fixture(tmp_path, functions=functions)
    report = module.build_vehicle_create_backend_return_target_catalog(frontier, root)

    assert report["all_targets_present_in_functions"] is False
    assert report["all_targets_instruction_export_eligible"] is False
    assert report["instruction_export_addresses"] == ["0x00639000"]
    missing = report["targets"][1]
    assert missing["present"] is False
    assert missing["blockers"] == ["target_absent_from_functions_jsonl"]


def test_external_target_is_cataloged_but_not_instruction_export_eligible(tmp_path):
    module = _load_module()
    functions = [
        _function("0x00639000", "FUN_00639000"),
        _function("0x0063a000", "EXT_0063a000", external=True),
        _function("0x00639100", "FUN_00639100"),
        _function("0x00630000", "FUN_00630000"),
    ]
    module, frontier, root = _fixture(tmp_path, functions=functions)
    report = module.build_vehicle_create_backend_return_target_catalog(frontier, root)
    external = report["targets"][1]
    assert external["present"] is True
    assert external["external"] is True
    assert external["instruction_export_eligible"] is False
    assert external["blockers"] == ["target_is_external_function"]
    assert report["instruction_export_addresses"] == ["0x00639000"]


def test_diagnostic_text_is_preserved_as_discovery_evidence_only(tmp_path):
    module, frontier, root = _fixture(tmp_path)
    report = module.build_vehicle_create_backend_return_target_catalog(frontier, root)
    first = report["targets"][0]
    assert first["allocation_diagnostic_text_reference_present"] is True
    assert first["exact_string_references"][0]["allocation_diagnostic_text_match"] is True
    assert first["returned_allocation_pointer_role_proven"] is False
    assert report["scope"]["returned_allocation_pointer_role_proven"] is False
    assert report["scope"]["allocator_abi_proven"] is False


def test_unresolved_backend_return_frontier_fails_closed(tmp_path):
    module = _load_module()
    frontier_value = _frontier(module, resolved=False)
    module, frontier, root = _fixture(tmp_path, frontier=frontier_value)
    with pytest.raises(ValueError, match="not fully resolved"):
        module.build_vehicle_create_backend_return_target_catalog(frontier, root)


def test_frontier_target_order_and_identity_drift_fail_closed(tmp_path):
    module = _load_module()
    unsorted = _frontier(module, targets=["0x0063a000", "0x00639000"])
    module, frontier, root = _fixture(tmp_path, frontier=unsorted)
    with pytest.raises(ValueError, match="targets must be sorted"):
        module.build_vehicle_create_backend_return_target_catalog(frontier, root)

    duplicate = _frontier(module, targets=["0x00639000", "0x00639000"])
    _write_json(frontier, duplicate)
    with pytest.raises(ValueError, match="duplicate targets"):
        module.build_vehicle_create_backend_return_target_catalog(frontier, root)


def test_missing_required_ghidra_file_fails_closed(tmp_path):
    module, frontier, root = _fixture(tmp_path)
    (root / "callgraph.jsonl").unlink()
    with pytest.raises(FileNotFoundError, match="callgraph.jsonl"):
        module.build_vehicle_create_backend_return_target_catalog(frontier, root)


def test_targets_writer_preserves_exact_sorted_addresses(tmp_path):
    module, frontier, root = _fixture(tmp_path)
    report = module.build_vehicle_create_backend_return_target_catalog(frontier, root)
    output = tmp_path / "targets.txt"
    module._write_targets(output, report)
    assert output.read_text(encoding="utf-8") == "0x00639000\n0x0063a000\n"
