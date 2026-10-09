import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_DIR = ROOT / "tools" / "ghidra"
TOOL = TOOL_DIR / "analyze_p1a_slot01_straight_zero_init.py"
EVIDENCE = ROOT / "evidence" / "p1a_p13a_slot01_straight_zero_init_machine_closure.json"
EXPECTED = [
    "FUN_00887580", "FUN_00647a10", "FUN_0070fae0",
    "FUN_0087aa00", "FUN_00886e10", "FUN_0088f110",
]


def load_module():
    sys.path.insert(0, str(TOOL_DIR))
    try:
        spec = importlib.util.spec_from_file_location("p1a_zero_init", TOOL)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def test_detector_tracks_register_zero_and_excludes_backward_loop_body():
    module = load_module()
    straight = [
        (0x1000, "xor", "ebx,ebx"),
        (0x1002, "mov", "DWORD PTR [esi+0x10],ebx"),
        (0x1005, "mov", "DWORD PTR [esi+0x14],ebx"),
    ]
    assert len(module.zero_clusters(straight)) == 1
    looped = straight + [(0x1008, "jmp", "0x1002")]
    assert module.zero_clusters(looped) == []


def test_authoritative_candidate_set_and_receiver_domains_are_pinned():
    module = load_module()
    assert list(module.EXPECTED_CANDIDATES) == EXPECTED
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.INDEX_SHA256 == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
    assert "0x00c29640" in module.SEMANTIC["FUN_00887580"][1]
    assert "0x00c104e0" in module.SEMANTIC["FUN_0070fae0"][1]
    assert "HDVehicle+0x6754" in module.SEMANTIC["FUN_0087aa00"][1]
    assert "0x00c29d4c" in module.SEMANTIC["FUN_00886e10"][1]
    assert "0x00c29b98" in module.SEMANTIC["FUN_0088f110"][1]


def test_captured_evidence_closes_only_shallow_zero_init_subset():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1A.P13ASlot01StraightZeroInitMachineClosure/1"
    assert payload["candidate_count"] == 6
    assert [row["function"] for row in payload["candidates"]] == EXPECTED
    assert all(row["rejected"] is True for row in payload["candidate_adjudication"])
    adj = payload["adjudication"]
    assert adj["shallow_straight_zero_init_depth4_surface_complete"] is True
    assert adj["shallow_straight_zero_init_rejected_count"] == 6
    assert adj["selected_hdvehicle_target_writer_found"] is False
    assert adj["sse_vector_copy_init_ruled_out"] is False
    assert adj["deeper_direct_alias_paths_ruled_out"] is False
    assert adj["indirect_or_callback_alias_paths_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
