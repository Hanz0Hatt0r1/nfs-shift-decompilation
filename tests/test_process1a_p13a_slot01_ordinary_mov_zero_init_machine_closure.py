import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1a_slot01_ordinary_mov_zero_init_frontier.py"
EVIDENCE = ROOT / "evidence" / "p1a_p13a_slot01_ordinary_mov_zero_init_machine_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_zero", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_zero_detector_tracks_zero_register_and_excludes_backedge_loop():
    module = load_module()
    straight = [
        (0x1000, "xor", "eax,eax"),
        (0x1002, "mov", "DWORD PTR [esi],eax"),
        (0x1004, "mov", "DWORD PTR [esi+0x4],eax"),
    ]
    clusters = module.clusters(straight)
    assert len(clusters) == 1
    assert clusters[0][2] == 8
    assert module.clusters(straight + [(0x1006, "jne", "0x1000")]) == []


def test_retail_candidate_set_is_exactly_six():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1A.P13ASlot01OrdinaryMovZeroInitMachineClosure/1"
    assert data["inventory"]["candidate_count"] == 6
    assert data["inventory"]["candidate_functions"] == [
        "FUN_00887580",
        "FUN_00647a10",
        "FUN_0070fae0",
        "FUN_0087aa00",
        "FUN_00886e10",
        "FUN_0088f110",
    ]
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["authority"]["ghidra_sqlite_sha256"] == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"


def test_all_candidates_reject_but_other_zero_init_classes_stay_open():
    data = load_evidence()
    assert all(row["rejected"] is True for row in data["candidate_adjudication"])
    adj = data["adjudication"]
    assert adj["shallow_ordinary_mov_zero_init_depth4_surface_complete"] is True
    assert adj["selected_hdvehicle_slot01_writer_found"] is False
    assert adj["x87_zero_init_surface_complete"] is False
    assert adj["sse_vector_zero_init_surface_complete"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_exact_receiver_domains_are_pinned():
    rows = {row["function"]: row for row in load_evidence()["candidate_adjudication"]}
    assert "0x00c29640" in " ".join(rows["FUN_00887580"]["evidence"])
    assert "DAT_00c104e0" in " ".join(rows["FUN_0070fae0"]["evidence"])
    assert "HDVehicle+0x6730" in " ".join(rows["FUN_0087aa00"]["evidence"])
    assert "0x00c29b98" in " ".join(rows["FUN_0088f110"]["evidence"])
