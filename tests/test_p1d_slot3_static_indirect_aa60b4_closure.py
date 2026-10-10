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


def test_static_slot_resolves_image_target():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3StaticIndirectAA60B4Closure/1"
    slot = data["static_slot"]
    assert slot["address"] == "0x00aa60b4"
    assert slot["section"] == ".rdata"
    assert slot["section_readonly_in_image"] is True
    assert slot["value"] == "0x00778052"


def test_both_fun00770e80_callsites_share_static_slot():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert [(x["address"], x["encoding"], x["caller_exact_root_register"]) for x in data["callsites"]] == [
        ("0x00770ec4", "ff 15 b4 60 aa 00", "ESI=HDVehicle"),
        ("0x00770f41", "ff 15 b4 60 aa 00", "ESI=HDVehicle"),
    ]


def test_exact_root_chain_is_bounded_and_has_no_selected_wheel_alias():
    chain = json.loads(EVIDENCE.read_text(encoding="utf-8"))["target_chain"]
    assert chain["target_fragment_instruction_count"] == 9
    assert chain["fun0063f350_instruction_count"] == 62
    assert chain["fun0063f300_instruction_count"] == 34
    assert chain["target_fragment_exact_root_forward"].startswith("0x00778056")
    assert chain["fun0063f350_exact_root_forward"].startswith("0x0063f37b")
    assert chain["exact_root_persistent_store_found"] is False
    assert chain["selected_wheel_root_materialization_found"] is False


def test_global_indirect_and_alias_gates_remain_fail_closed():
    gates = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert gates["fun00770e80_aa60b4_static_indirect_subset_complete"] is True
    assert gates["aa60b4_runtime_unknown_target"] is False
    assert gates["aa60b4_exact_hdvehicle_root_persistent_store_found"] is False
    assert gates["aa60b4_selected_wheel_alias_found"] is False
    assert gates["other_indirect_entry_ruled_out"] is False
    assert gates["callee_created_aliases_ruled_out"] is False
    assert gates["runtime_generated_pointer_stores_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"] == 7


def test_tool_contract_matches_evidence():
    module = load_module()
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert module.FORMAT == data["format"]
    assert module.SLOT_VA == 0x00AA60B4
    assert module.STATIC_TARGET == 0x00778052
    assert module.CALLSITES == [0x00770EC4, 0x00770F41]
