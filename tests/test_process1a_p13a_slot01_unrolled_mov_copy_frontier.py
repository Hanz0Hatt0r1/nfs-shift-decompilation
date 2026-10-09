import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1a_slot01_unrolled_mov_copy_frontier.py"
EVIDENCE = ROOT / "evidence" / "p1a_p13a_slot01_unrolled_mov_copy_frontier.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_unrolled_mov", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_clobber_and_loop_exclusion():
    module = load_module()
    straight = [
        (0x1000, "mov", "eax,DWORD PTR [ecx]"),
        (0x1003, "mov", "DWORD PTR [edi],eax"),
        (0x1005, "mov", "edx,DWORD PTR [ecx+0x4]"),
        (0x1008, "mov", "DWORD PTR [edi+0x4],edx"),
    ]
    clusters = module.clusters(straight)
    assert len(clusters) == 1
    assert clusters[0][2] == 8

    clobbered = [
        (0x2000, "mov", "eax,DWORD PTR [ecx]"),
        (0x2003, "lea", "eax,[edx+eax*8]"),
        (0x2007, "mov", "DWORD PTR [edi],eax"),
        (0x2009, "mov", "edx,DWORD PTR [ecx+0x4]"),
        (0x200C, "mov", "DWORD PTR [edi+0x4],edx"),
    ]
    assert module.clusters(clobbered) == []

    loop = [
        (0x3000, "mov", "eax,DWORD PTR [ecx]"),
        (0x3003, "mov", "DWORD PTR [edi],eax"),
        (0x3005, "mov", "edx,DWORD PTR [ecx+0x4]"),
        (0x3008, "mov", "DWORD PTR [edi+0x4],edx"),
        (0x300B, "jne", "0x3000"),
    ]
    assert module.clusters(loop) == []


def test_retail_candidate_set_is_exact():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1A.P13ASlot01UnrolledMovCopyFrontierEvidence/1"
    assert data["scan"]["candidate_function_count"] == 11
    assert [(row["depth"], row["function"]) for row in data["candidates"]] == [
        (1, "FUN_0076e560"),
        (2, "FUN_007b0710"),
        (3, "FUN_00403d00"),
        (3, "FUN_004e9380"),
        (3, "FUN_00633290"),
        (3, "FUN_006333f0"),
        (3, "FUN_0075a8d0"),
        (3, "FUN_007b0580"),
        (4, "FUN_0064fef0"),
        (4, "FUN_007b0450"),
        (4, "_LocaleUpdate"),
    ]
    assert data["authority"]["ghidra_sqlite_sha256"] == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def test_navigation_result_stays_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["navigation_frontier_captured"] is True
    assert adj["zero_init_included"] is False
    assert adj["loop_body_transfers_included"] is False
    assert adj["candidate_reachability_proves_selected_hdvehicle_alias"] is False
    assert adj["unrolled_copy_semantics_complete"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
