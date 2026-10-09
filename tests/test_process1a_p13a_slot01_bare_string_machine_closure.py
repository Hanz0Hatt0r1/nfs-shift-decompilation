import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1a_slot01_bare_string_frontier.py"
EVIDENCE = ROOT / "evidence" / "p1a_p13a_slot01_bare_string_machine_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_bare_string", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parser_accepts_only_canonical_bare_string_encodings():
    module = load_module()
    text = """
      1000: a5 movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
      1001: 66 a5 movs WORD PTR es:[edi],WORD PTR ds:[esi]
      1003: f3 a5 rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
      1005: f2 0f 10 c0 movsd xmm0,xmm0
      1009: a4 movs BYTE PTR es:[edi],BYTE PTR ds:[esi]
    """
    rows = module.parse_bare_string_sites(text)
    assert [(x["address"], x["bytes"]) for x in rows] == [
        ("0x00001000", "a5"),
        ("0x00001001", "66a5"),
        ("0x00001009", "a4"),
    ]


def test_machine_anchors_pin_stack_and_global_cases():
    module = load_module()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.EXPECTED_BYTES[0x009109CB] == "8dbd7affffff"
    assert module.EXPECTED_BYTES[0x009109D1] == "a5"
    assert module.EXPECTED_BYTES[0x0063441C] == "66a5"
    assert module.EXPECTED_REL32_TARGETS[0x007710B2] == 0x0090328A
    assert module.EXPECTED_REL32_TARGETS[0x00910827] == 0x009108CA


def test_two_candidates_close_only_bare_string_subset():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["inventory"]["whole_image_canonical_bare_string_site_count"] == 594
    assert data["inventory"]["mapped_bare_string_site_count"] == 369
    assert data["inventory"]["mapped_bare_string_function_count"] == 76
    assert data["inventory"]["candidate_functions"] == ["FUN_009108ca", "FUN_00634240"]
    assert all(item["rejected"] for item in data["candidate_adjudication"])
    adjudication = data["adjudication"]
    assert adjudication["shallow_canonical_bare_string_depth4_surface_complete"] is True
    assert adjudication["shallow_canonical_bare_string_selected_hdvehicle_writer_found"] is False
    assert adjudication["all_nonrep_custom_copy_init_ruled_out"] is False
    assert adjudication["slot0_selected_root_alias_callee_bulk_copy_complete"] is False
    assert adjudication["slot1_selected_root_alias_callee_bulk_copy_complete"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7
