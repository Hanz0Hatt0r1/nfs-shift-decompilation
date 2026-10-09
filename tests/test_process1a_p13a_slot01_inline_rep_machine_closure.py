import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1a_slot01_inline_rep_frontier.py"
EVIDENCE = ROOT / "evidence" / "p1a_p13a_slot01_inline_rep_machine_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_inline_rep", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rep_parser_only_accepts_rep_movs_stos():
    module = load_module()
    text = """
      1000: f3 a5  rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
      1002: f3 ab  rep stos DWORD PTR es:[edi],eax
      1004: 90     nop
      1005: f2 ae  repnz scas BYTE PTR es:[edi],al
    """
    sites = module.parse_rep_sites(text)
    assert [(x["address"], x["kind"]) for x in sites] == [
        ("0x00001000", "movs"),
        ("0x00001002", "stos"),
    ]


def test_shortest_path_frontier_is_depth_bounded():
    module = load_module()
    graph = {
        "ROOT": [("A", "0x1"), ("X", "0x2")],
        "A": [("B", "0x3")],
        "B": [("C", "0x4")],
        "C": [("D", "0x5")],
        "X": [("D", "0x6")],
    }
    distance, parent, parent_site = module.bfs(graph, "ROOT", 2)
    assert distance["D"] == 2
    path = module.path_to("ROOT", "D", distance, parent, parent_site)
    assert path == {"depth": 2, "nodes": ["ROOT", "X", "D"], "callsites": ["0x2", "0x6"]}
    assert "C" not in distance


def test_machine_anchor_contract_pins_numeric_collision_case():
    module = load_module()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.INDEX_SHA256 == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
    assert module.EXPECTED_BYTES[0x00887733] == "b94096c200"
    assert module.EXPECTED_BYTES[0x0088766F] == "8dbea0030000"
    assert module.EXPECTED_BYTES[0x00887675] == "b96e000000"
    assert module.EXPECTED_BYTES[0x0088767A] == "f3ab"
    assert module.EXPECTED_REL32_TARGETS[0x00887738] == 0x00887580
    assert module.EXPECTED_REL32_TARGETS[0x00887604] == 0x00886E10


def test_exact_five_candidate_closure_stays_fail_closed_globally():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1A.P13ASlot01InlineRepMachineClosure/1"
    assert data["inventory"]["distinct_shallow_candidate_count"] == 5
    assert data["inventory"]["candidate_functions"] == [
        "FUN_00764266",
        "FUN_00887580",
        "FUN_00634240",
        "FUN_007b7840",
        "FUN_00886e10",
    ]
    rows = {row["function"]: row for row in data["candidate_adjudication"]}
    assert set(rows) == set(data["inventory"]["candidate_functions"])
    assert all(row["rejected"] is True for row in rows.values())
    singleton = rows["FUN_00887580"]
    assert any("+0x538" in line and "numerically includes" in line for line in singleton["evidence"])
    assert any("Numeric overlap is not object identity" in line for line in singleton["evidence"])
    adj = data["adjudication"]
    assert adj["shallow_inline_rep_depth4_surface_complete"] is True
    assert adj["shallow_inline_rep_candidate_count"] == 5
    assert adj["shallow_inline_rep_rejected_count"] == 5
    assert adj["shallow_inline_rep_selected_hdvehicle_writer_found"] is False
    assert adj["inline_or_custom_bulk_copy_ruled_out_globally"] is False
    assert adj["slot0_selected_root_alias_callee_bulk_copy_complete"] is False
    assert adj["slot1_selected_root_alias_callee_bulk_copy_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
