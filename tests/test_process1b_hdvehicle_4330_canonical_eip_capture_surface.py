import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_canonical_eip_capture.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_canonical_eip_capture_surface.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1b_4330_eip", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_evidence_pins_single_security_candidate():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330CanonicalEipCaptureSurface/1"
    surface = data["canonical_call_next_pop_surface"]
    assert surface["candidate_count"] == 1
    assert surface["candidates"] == [{
        "call": "0x00d31404",
        "pop": "0x00d31409",
        "pop_register": "ebp",
        "section": ".secu",
    }]
    assert surface["derived_value"] == "0x00d31000"
    assert surface["derived_value_identity"] == ".secu section base"
    assert surface["exact_4330_carrier_pointer_derived"] is False


def test_only_canonical_subset_closes():
    adj = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert adj["canonical_call_next_pop_eip_capture_surface_complete"] is True
    assert adj["canonical_call_next_pop_candidate_count"] == 1
    assert adj["canonical_call_next_pop_can_derive_exact_carrier"] is False
    assert adj["noncanonical_eip_capture_surface_complete"] is False
    assert adj["runtime_computed_carrier_pointers_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_instruction_parser_rejects_unaligned_raw_false_positive():
    module = load_tool()
    text = """Disassembly of section .text:\n  1000: e8 11 22 33 00        call 0x333216\n  1005: 5d                    pop ebp\n"""
    _, instructions = module.parse_objdump(text)
    assert module.find_call_next_pop(instructions) == []


def test_instruction_parser_surfaces_call_next_pop():
    module = load_tool()
    text = """Disassembly of section .secu:\n  d31404: e8 00 00 00 00        call 0xd31409\n  d31409: 5d                    pop ebp\n"""
    sections, instructions = module.parse_objdump(text)
    assert sections == {".secu"}
    assert module.find_call_next_pop(instructions) == [{
        "section": ".secu",
        "call": "0x00d31404",
        "pop": "0x00d31409",
        "pop_register": "ebp",
    }]


def test_tool_pins_retail_window_and_hash():
    module = load_tool()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.WINDOW_VA == 0x00D31400
    assert len(bytes.fromhex(module.WINDOW_HEX)) == 0x43
