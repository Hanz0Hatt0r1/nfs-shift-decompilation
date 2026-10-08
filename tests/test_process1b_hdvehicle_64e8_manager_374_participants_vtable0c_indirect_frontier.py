import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_participants_vtable0c_indirect_frontier.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_retail_authority_are_pinned():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager374ParticipantsVtable0cIndirectFrontier/1"
    assert p["ready"] is True
    assert p["authority"]["platform"] == "PC retail 1.02"
    assert p["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def test_vtable_0c_indirect_calls_split_into_exact_receiver_domains():
    p = _payload()
    assert p["participants_callback"]["function"] == "FUN_0048a7f0"
    assert p["participants_callback"]["indirect_call_count"] == 6
    domains = p["indirect_receiver_domains"]
    assert domains["heap_helper_calls"] == ["0x0048aba4", "0x0048abdd", "0x0048ac1b"]
    assert domains["manager_derived_calls"] == ["0x0048ac8c", "0x0048aca6", "0x0048acc4"]
    assert domains["manager_derived_receiver"] == "participants+0x418 == manager+0x438"


def test_manager_438_constructor_and_virtual_target_are_exact():
    m = _payload()["manager_438_object"]
    assert m["constructor"] == "FUN_007de7f0"
    assert m["vptr"] == "0x00b10728"
    assert m["indirect_slot_offset"] == "+0x3c"
    assert m["slot_index"] == 15
    assert m["resolved_target"] == "FUN_007da470"
    assert m["resolved_target_mnemonic_sha256"] == "66b835ea6ec200f10df83381dc390405e280b2641de9ac2287263b7b952b9fb5"


def test_resolved_target_direct_body_does_not_recover_parent_or_store_374():
    b = _payload()["resolved_target_body"]
    assert b["parent_recovery_from_manager_438_observed"] is False
    assert b["direct_manager_plus_0x374_store_observed"] is False
    assert b["same_receiver_direct_callee"] == "FUN_007d8e00"
    assert b["same_receiver_deeper_surface_complete"] is False


def test_direct_root_side_path_does_not_forward_ecx_semantically():
    d = _payload()["direct_root_side_path"]
    assert d["receiver"] == "participants-0x20 == manager root"
    assert d["resolved_target"] == "FUN_00d60e50"
    assert d["direct_manager_plus_0x374_store_observed"] is False
    assert d["apparent_root_forward_to_0x00487350_is_semantically_false"] is True
    assert "does not consume incoming ECX" in d["reason"]


def test_adjudication_stays_fail_closed_for_deeper_and_heap_surfaces():
    a = _payload()["adjudication"]
    assert a["participants_vtable_0x0c_indirect_receiver_inventory_complete"] is True
    assert a["manager_438_indirect_target_resolved"] is True
    assert a["manager_438_resolved_target_direct_body_reaches_manager_374"] is False
    assert a["direct_root_side_path_direct_body_reaches_manager_374"] is False
    assert a["manager_438_deeper_same_receiver_surface_complete"] is False
    assert a["heap_helper_indirect_target_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["exact_hdvehicle_64e8_non_sentinel_writer_proven"] is False
    assert a["external_provider_count"] == 7
