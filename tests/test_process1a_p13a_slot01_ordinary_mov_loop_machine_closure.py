import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1a_slot01_ordinary_mov_loop_frontier.py"
EVIDENCE = ROOT / "evidence" / "p1a_p13a_slot01_ordinary_mov_loop_machine_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_mov_loop", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_clobber_aware_loop_detector_only_keeps_real_carrier_or_zero_store():
    module = load_module()
    real_copy = [
        (0x1000, "mov", "eax,DWORD PTR [esi]"),
        (0x1002, "mov", "DWORD PTR [edi],eax"),
        (0x1004, "add", "edi,0x4"),
        (0x1007, "jne", "0x1000"),
    ]
    loops = module.candidate_loops(real_copy)
    assert len(loops) == 1
    assert loops[0]["hits"][0]["kind"] == "memory-transfer"

    clobbered = [
        (0x2000, "mov", "edx,DWORD PTR [ecx+eax*4]"),
        (0x2004, "lea", "edx,[esi+edx*8]"),
        (0x2008, "mov", "DWORD PTR [edi+eax*4],edx"),
        (0x200C, "add", "eax,0x1"),
        (0x200F, "jne", "0x2000"),
    ]
    assert module.candidate_loops(clobbered) == []


def test_retail_inventory_is_exactly_five_functions():
    data = load_evidence()
    inv = data["inventory"]
    assert inv["candidate_function_count"] == 5
    assert inv["candidate_functions"] == [
        "FUN_00765c40",
        "FUN_00764266",
        "FUN_00a62940",
        "FUN_0090db22",
        "FUN_00a62fd0",
    ]
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["authority"]["ghidra_sqlite_sha256"] == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"


def test_all_five_are_rejected_but_slot_gates_remain_closed():
    data = load_evidence()
    assert all(row["rejected"] is True for row in data["candidate_adjudication"])
    adj = data["adjudication"]
    assert adj["shallow_ordinary_mov_copy_init_depth4_surface_complete"] is True
    assert adj["selected_hdvehicle_slot01_writer_found"] is False
    assert adj["nonloop_unrolled_mov_surface_complete"] is False
    assert adj["deeper_direct_paths_ruled_out"] is False
    assert adj["indirect_copy_dispatch_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_receiver_domains_pin_the_two_nontrivial_service_helpers():
    rows = {row["function"]: row for row in load_evidence()["candidate_adjudication"]}
    assert "receiver+0x6730" in " ".join(rows["FUN_00a62940"]["proof"])
    assert "index*0x30" in " ".join(rows["FUN_00a62fd0"]["proof"])
    assert "EBP-0xd0" in " ".join(rows["FUN_00764266"]["proof"])
