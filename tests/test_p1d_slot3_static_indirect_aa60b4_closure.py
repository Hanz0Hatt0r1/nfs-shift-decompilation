import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1d_slot3_static_indirect_aa60b4_pe.py"
EVIDENCE = ROOT / "evidence/p1d_slot3_static_indirect_aa60b4_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_static_indirect_aa60b4", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_iat_slot_resolves_kernel32_interlocked_exchange():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1D.Slot3StaticIndirectAA60B4Closure/2"
    assert data["supersedes"] == "SHIFT.P1D.Slot3StaticIndirectAA60B4Closure/1"
    iat = data["iat"]
    assert iat == {
        "dll": "KERNEL32.dll",
        "first_thunk_rva": "0x006a6088",
        "import_descriptor_rva": "0x007776bc",
        "import_hint": 553,
        "import_name": "InterlockedExchange",
        "import_name_rva": "0x00778052",
        "on_disk_first_thunk_value": "0x00778052",
        "on_disk_value_semantics": "IMAGE_IMPORT_BY_NAME RVA, not code VA",
        "original_first_thunk_rva": "0x00777938",
        "runtime_slot_semantics": "loader-resolved KERNEL32!InterlockedExchange address",
        "slot_rva": "0x006a60b4",
        "slot_section": ".rdata",
        "slot_va": "0x00aa60b4",
        "thunk_index": 11,
    }


def test_both_fun00770e80_callsites_are_scalar_interlocked_exchange():
    data = load_evidence()
    assert data["callsites"] == [
        {
            "address": "0x00770ec4",
            "encoding": "ff 15 b4 60 aa 00",
            "operation": "InterlockedExchange((LONG volatile*)(HDVehicle+0x4020), 1)",
            "target_argument": "HDVehicle+0x4020",
            "value_argument": 1,
        },
        {
            "address": "0x00770f41",
            "encoding": "ff 15 b4 60 aa 00",
            "operation": "InterlockedExchange((LONG volatile*)(HDVehicle+0x4020), 2)",
            "target_argument": "HDVehicle+0x4020",
            "value_argument": 2,
        },
    ]
    windows = data["verified_caller_windows"]
    assert windows[0]["bytes"] == "6a018d862040000050ff15b460aa00"
    assert windows[0]["sha256"] == "687df04bb024afe13a22da177fd986c83e4fe3f1edcc273a20cad5e8737a1ce3"
    assert windows[1]["bytes"].startswith("6a02")
    assert "8d862040000050" in windows[1]["bytes"]
    assert windows[1]["bytes"].endswith("ff15b460aa00")
    assert windows[1]["sha256"] == "48505813af30c6aebc2287761d0793038d771593a40cd594dc8c831eb7355273"


def test_global_indirect_and_alias_gates_remain_fail_closed():
    gates = load_evidence()["adjudication"]
    assert gates["fun00770e80_aa60b4_import_indirect_subset_complete"] is True
    assert gates["aa60b4_runtime_unknown_target"] is False
    assert gates["aa60b4_runtime_import"] == "KERNEL32!InterlockedExchange"
    assert gates["aa60b4_on_disk_value_is_code_target"] is False
    assert gates["aa60b4_scalar_state_target"] == "HDVehicle+0x4020"
    assert gates["aa60b4_exact_hdvehicle_root_persistent_store_found"] is False
    assert gates["aa60b4_selected_wheel_alias_found"] is False
    assert gates["other_indirect_entry_ruled_out"] is False
    assert gates["callee_created_aliases_ruled_out"] is False
    assert gates["runtime_generated_pointer_stores_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["p1_3_control_producer_complete"] is False
    assert gates["external_provider_count"] == 7


def test_tool_contract_matches_corrected_evidence():
    module = load_module()
    data = load_evidence()
    assert module.FORMAT == data["format"]
    assert module.SUPERSEDES == data["supersedes"]
    assert module.SLOT_VA == 0x00AA60B4
    assert module.SLOT_RVA == 0x006A60B4
    assert module.IMPORT_DESCRIPTOR_RVA == 0x007776BC
    assert module.ORIGINAL_FIRST_THUNK_RVA == 0x00777938
    assert module.FIRST_THUNK_RVA == 0x006A6088
    assert module.IMPORT_INDEX == 11
    assert module.IMPORT_NAME_RVA == 0x00778052
    assert module.IMPORT_HINT == 0x0229
    assert module.IMPORT_DLL == "KERNEL32.dll"
    assert module.IMPORT_NAME == "InterlockedExchange"
    assert module.CALLSITES == [0x00770EC4, 0x00770F41]
