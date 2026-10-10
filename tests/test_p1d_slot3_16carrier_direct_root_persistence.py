import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1d_slot3_16carrier_direct_root_persistence_pe.py"
EVIDENCE = ROOT / "evidence/p1d_slot3_16carrier_direct_root_persistence.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_16carrier_root_persistence", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_16_carriers_are_machine_pinned():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3SixteenCarrierDirectRootPersistence/1"
    scope = data["scope"]
    assert scope["carrier_count"] == 16
    assert len(scope["functions"]) == 16
    assert scope["stable_exact_root_register_intervals_seeded_from_merged_machine_contracts"] is True
    for row in scope["functions"].values():
        assert row["instruction_count"] > 0
        assert row["decoded_byte_count"] > 0
        assert len(row["machine_bytes_sha256"]) == 64


def test_direct_exact_root_storage_is_stack_only():
    surface = json.loads(EVIDENCE.read_text(encoding="utf-8"))["direct_exact_root_value_surface"]
    assert surface["memory_store_count"] == 2
    assert surface["nonstack_or_unknown_memory_store_count"] == 0
    assert surface["push_count"] == 0
    assert [(x["function"], x["address"], x["storage"]) for x in surface["memory_stores"]] == [
        ("FUN_00758b50", "0x00758b9b", "stack-local"),
        ("FUN_00763570", "0x00763590", "stack-local"),
    ]


def test_exact_root_register_copies_do_not_widen_beyond_ecx():
    surface = json.loads(EVIDENCE.read_text(encoding="utf-8"))["direct_exact_root_value_surface"]
    assert surface["register_copy_count"] == 23
    assert surface["register_copy_destinations"] == ["ecx"]
    assert all(row["destination"] == "ecx" for row in surface["register_copies"])


def test_fun00758b50_stack_bridge_is_explicit():
    bridge = json.loads(EVIDENCE.read_text(encoding="utf-8"))["scope"]["fun00758b50_stack_bridge"]
    assert bridge["store"].startswith("0x00758b9b")
    assert bridge["restore"].startswith("0x00758d70")


def test_global_gates_remain_fail_closed():
    gates = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert gates["machine_direct_exact_root_storage_16_carrier_subset_complete"] is True
    assert gates["machine_direct_exact_root_nonstack_store_found"] is False
    assert gates["machine_direct_exact_root_push_found"] is False
    assert gates["machine_direct_exact_root_new_gpr_alias_beyond_ecx_receiver_reload_found"] is False
    assert gates["machine_register_alias_storage_ruled_out"] is False
    assert gates["derived_alias_storage_ruled_out"] is False
    assert gates["runtime_generated_pointer_stores_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"] == 7


def test_tool_contract_matches_evidence_shape():
    module = load_module()
    assert module.FORMAT == "SHIFT.P1D.Slot3SixteenCarrierDirectRootPersistence/1"
    assert len(module.SPECS) == 16
    assert len(module.EXPECTED_STORES) == 2
    assert len(module.EXPECTED_COPY_ADDRESSES) == 23
