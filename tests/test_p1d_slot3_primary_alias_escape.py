import importlib.util
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "verify_p1d_slot3_primary_alias_escape.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_primary_alias_escape.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1d_slot3_primary_alias", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rel32_helper_recovers_target():
    module = load_tool()
    site = 0x1000
    target = 0x123456
    disp = target - (site + 5)
    raw = b"\xe8" + struct.pack("<i", disp)
    assert module.rel32_target(site, raw) == target


def test_evidence_pins_primary_selected_wheel_handoff():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.P13DSlot3PrimaryAliasEscape/1"
    assert data["authority"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    loop = data["primary_loop"]
    assert loop["vehicle_root_capture"] == "0x00758b98 EDI=entry ECX=HDVehicle"
    assert loop["loop_seed"] == "0x00758bb4 ESI=HDVehicle+0x848"
    assert loop["loop_stride"] == "0x00758d7d ESI+=0xa80"
    assert loop["selected_wheel_materialization"] == (
        "0x00758ccf ECX=ESI-0x448=HDVehicle+0x400+slot*0xa80"
    )
    assert loop["selected_wheel_direct_call"] == "0x00758d6b -> FUN_00755950"
    assert loop["exact_selected_wheel_root_forwarded_to_other_direct_callee"] is False


def test_consumer_target_is_read_only_and_root_does_not_escape():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    consumer = data["consumer"]
    assert consumer["entry_root_copy"] == "0x00755956 EDX=ECX"
    assert consumer["target_read"] == "0x00755958 fld qword [EDX+0x538]"
    assert consumer["direct_writes"] == [
        "0x0075596a qword [EDX+0x528]",
        "0x00755975 qword [EDX+0x530]",
        "0x00755988 qword [EDX+0x548]",
    ]
    assert consumer["writes_overlap_target_0x538_0x53f"] is False
    assert consumer["only_direct_callee"] == "0x00755983 -> FUN_007555b0"
    assert consumer["callee_receiver"] == "0x00755964 ECX=EDX+0x80"
    assert consumer["exact_wheel_root_forwarded_to_callee"] is False


def test_fail_closed_global_alias_gates_remain_open():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    adj = data["adjudication"]
    assert adj["primary_loop_exact_wheel_root_one_hop_forwarding_complete"] is True
    assert adj["primary_loop_exact_wheel_root_only_direct_target_is_FUN_00755950"] is True
    assert adj["FUN_00755950_target_field_is_read_only"] is True
    assert adj["FUN_00755950_exact_wheel_root_does_not_escape_to_direct_callee"] is True
    assert adj["global_interprocedural_wheel_alias_surface_complete"] is False
    assert adj["escaped_alias_store_surface_complete"] is False
    assert adj["slot3_writer_provenance_proven"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7


def test_machine_anchor_and_call_sets_are_exact():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    anchors = {row["address"]: row["bytes"] for row in data["machine_anchors"]["byte_windows"]}
    assert anchors["0x00758ccf"] == "8d8eb8fbffff"
    assert anchors["0x00755958"] == "dd8238050000"
    assert anchors["0x00755964"] == "8d8a80000000"
    calls = {row["site"]: row["target"] for row in data["machine_anchors"]["rel32_calls"]}
    assert calls["0x00758d6b"] == "0x00755950"
    assert calls["0x00755983"] == "0x007555b0"
