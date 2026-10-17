import importlib.util
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_function_recovery_index.py"
    )
    spec = importlib.util.spec_from_file_location("build_function_recovery_index", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_composes_recovered_name_candidates_with_direct_manager_getter_callers():
    module = _load_module()
    functions = [
        {"address": "0x00100000", "name": "FUN_00100000", "size": 32, "mnemonic_sha256": "a"},
        {"address": "0x00100010", "name": "FUN_00100010", "size": 48, "mnemonic_sha256": "b"},
        {"address": "0x00100020", "name": "FUN_00100020", "size": 64, "mnemonic_sha256": "c"},
    ]
    calls = [
        {"from_function": "0x00100000", "instruction": "0x00100004", "to": "0x00489ad0", "indirect": False},
        {"from_function": "0x00100000", "instruction": "0x00100018", "to": "0x00489ad0", "indirect": False},
        {"from_function": "0x00100010", "instruction": "0x00100014", "to": "0x00489ad0", "indirect": True},
        {"from_function": "0x00100020", "instruction": "0x00100024", "to": "0x00489ad0", "indirect": False},
    ]
    anchors = {
        "format": "SHIFT.GhidraMethodNameAnchors/1",
        "function_inventory_count": 3,
        "method_string_anchor_count": 3,
        "unique_method_name_candidate_count": 1,
        "ambiguous_method_anchor_function_count": 1,
        "functions": [
            {
                "address": "0x00100000",
                "unique_method_name_candidate": "MWL::SMS::RaceManager::Tick",
                "status": "unique-method-name-anchor-candidate",
                "method_anchors": ["MWL::SMS::RaceManager::Tick"],
                "anchor_string_addresses": ["0x00200000"],
            },
            {
                "address": "0x00100020",
                "unique_method_name_candidate": None,
                "status": "ambiguous-method-name-anchors",
                "method_anchors": ["MWL::SMS::RaceManager::Start", "MWL::SMS::RaceManager::Stop"],
                "anchor_string_addresses": ["0x00200020", "0x00200030"],
            },
        ],
    }

    report = module.compose_index(functions, calls, anchors, {"callgraph.jsonl": "hash"}, module.RETAIL_SHA256)

    assert report["method_name_recovery"]["automatic_function_renaming_performed"] is False
    assert report["method_name_recovery"]["candidates"][1]["method_name_status"] == "ambiguous-method-name-anchors"
    getter = report["manager_root_getter_callers"]
    assert getter["direct_callgraph_callsite_count"] == 3
    assert getter["unique_caller_count"] == 2
    assert getter["caller_with_unique_method_name_candidate_count"] == 1
    assert getter["callers"][0]["direct_call_sites"] == ["0x00100004", "0x00100018"]
    assert getter["callers"][1]["method_name_candidate"] is None
    assert report["scope"]["manager_374_to_hdvehicle_4330_identity_proven"] is False


def test_rejects_another_executable():
    module = _load_module()
    try:
        module.compose_index([], [], {}, {}, "0" * 64)
    except ValueError as exc:
        assert "unexpected SHIFT retail executable" in str(exc)
    else:
        raise AssertionError("a different executable must fail closed")
