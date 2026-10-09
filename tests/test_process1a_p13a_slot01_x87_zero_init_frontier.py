import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1a_slot01_x87_zero_init_frontier.py"
EVIDENCE = ROOT / "evidence" / "p1a_p13a_slot01_x87_zero_init_frontier.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_x87_zero", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_fldz_fst_sequence_is_detected_and_backedge_body_is_excluded():
    module = load_module()
    straight = [
        (0x1000, "fldz", ""),
        (0x1002, "fst", "DWORD PTR [esi]"),
        (0x1004, "fstp", "DWORD PTR [esi+0x4]"),
    ]
    clusters = module.clusters(straight)
    assert len(clusters) == 1
    assert clusters[0][2] == 8
    assert module.clusters(straight + [(0x1006, "jne", "0x1000")]) == []


def test_retail_candidate_set_is_exactly_eighteen():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1A.P13ASlot01X87ZeroInitFrontierEvidence/1"
    assert data["scan"]["candidate_function_count"] == 18
    assert [(row["depth"], row["function"]) for row in data["candidates"]] == [
        (0, "FUN_00763570"),
        (0, "FUN_00770e80"),
        (1, "FUN_00755a60"),
        (1, "FUN_00760b50"),
        (1, "FUN_00766510"),
        (1, "FUN_0076e560"),
        (2, "FUN_0075c0d0"),
        (2, "FUN_007aa940"),
        (2, "FUN_007b8630"),
        (3, "FUN_0075ada0"),
        (4, "FUN_00647a10"),
        (4, "FUN_0070fae0"),
        (4, "FUN_0075afc0"),
        (4, "FUN_0076f030"),
        (4, "FUN_007876e0"),
        (4, "FUN_007ade70"),
        (4, "FUN_007b7840"),
        (4, "FUN_0088f110"),
    ]
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["authority"]["ghidra_sqlite_sha256"] == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"


def test_frontier_is_navigation_only_and_global_gates_stay_closed():
    adj = load_evidence()["adjudication"]
    assert adj["navigation_frontier_captured"] is True
    assert adj["x87_zero_init_semantics_complete"] is False
    assert adj["sse_vector_copy_init_complete"] is False
    assert adj["deeper_direct_aliases_ruled_out"] is False
    assert adj["indirect_callback_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
