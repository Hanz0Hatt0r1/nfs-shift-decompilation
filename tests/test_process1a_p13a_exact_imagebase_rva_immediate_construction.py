import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1a_exact_imagebase_rva_construction.py"
EVIDENCE = ROOT / "evidence" / "p1a_p13a_exact_imagebase_rva_immediate_construction_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_imagebase_rva", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_synthetic_same_function_exact_imagebase_and_carrier_rva_is_detected():
    module = load_module()
    lines = [
        "  00500000: b8 00 00 40 00        mov    eax,0x400000\n",
        "  00500005: 05 50 8b 35 00        add    eax,0x358b50\n",
    ]
    out = module.scan_instruction_lines(lines, [(0x00500000, "SYNTHETIC")])
    assert len(out["imagebase_rows"]) == 1
    assert len(out["carrier_rva_rows"]) == 1
    assert out["carrier_rva_rows"][0]["carrier"] == "FUN_00758b50"
    assert out["same_function_candidates"] == [
        {
            "function": "SYNTHETIC",
            "imagebase_sites": ["0x00500000"],
            "carrier_rva_sites": ["0x00500005"],
            "carriers": ["FUN_00758b50"],
        }
    ]


def test_retail_surface_counts_and_materializers_are_exact():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1A.P13AExactImagebaseRvaImmediateConstructionClosure/1"
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["authority"]["ghidra_sqlite_sha256"] == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
    assert data["scope"]["carrier_count"] == 16
    scan = data["scan"]
    assert scan["disassembled_instruction_count"] == 2847850
    assert scan["exact_imagebase_scalar_use_count"] == 52
    assert scan["exact_imagebase_mnemonic_counts"] == {
        "and": 2,
        "cmp": 4,
        "mov": 7,
        "or": 8,
        "push": 5,
        "sub": 1,
        "test": 25,
    }
    assert scan["exact_imagebase_value_materializing_use_count"] == 13
    assert scan["exact_carrier_rva_scalar_use_count"] == 0
    assert scan["same_function_exact_imagebase_plus_carrier_rva_candidate_count"] == 0
    assert [row["address"] for row in data["imagebase_value_materializers"]] == [
        "0x0065228e",
        "0x00652360",
        "0x00652420",
        "0x00652bab",
        "0x007367ec",
        "0x007368a4",
        "0x00869017",
        "0x00904817",
        "0x0091868a",
        "0x0091869e",
        "0x009186a4",
        "0x009814e4",
        "0x0098dd1c",
    ]
    assert all(row["exact_rva_scalar_hit_count"] == 0 for row in data["carrier_rva_surface"])
    assert data["same_function_candidates"] == []


def test_only_exact_immediate_subset_closes_and_global_gates_remain_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["p13a_exact_imagebase_plus_exact_carrier_rva_immediate_subset_complete"] is True
    assert adj["p13a_exact_imagebase_plus_exact_carrier_rva_candidate_found"] is False
    assert adj["manual_imagebase_plus_exact_rva_immediate_construction_ruled_out"] is True
    assert adj["manual_imagebase_plus_rva_pointer_construction_ruled_out"] is False
    assert adj["encoded_or_reconstructed_carrier_pointers_ruled_out"] is False
    assert adj["runtime_generated_or_copied_carrier_pointers_ruled_out"] is False
    assert adj["runtime_callback_registration_ruled_out"] is False
    assert adj["incoming_indirect_entry_ruled_out"] is False
    assert adj["runtime_generated_selected_wheel_pointer_stores_ruled_out"] is False
    assert adj["stored_or_escaped_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
