import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_participants_active_dispatch_nested_frontier.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_authority_are_pinned():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager374ParticipantsActiveDispatchNestedFrontier/1"
    assert p["ready"] is True
    assert p["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert p["upstream_contract"] == "SHIFT.HDVehicle64e8Manager374ParticipantsLifecycleZeroWriters/1"


def test_active_bmanager_dispatch_resolves_exact_participants_callbacks():
    d = _payload()["bmanager_dispatch"]
    assert d["selector"] == "FUN_00647d80"
    assert d["default_slot_offset"] == "+0x18"
    assert d["alternate_slot_offset"] == "+0x1c"
    assert d["default_target"] == "FUN_0048ade0"
    assert d["alternate_target"] == "FUN_0048aee0"
    assert [row["mnemonic_sha256"] for row in d["targets"]] == [
        "47701b60c5aa4c4fb3f900182be11cefe30fffbd1326987bb62cc3a239b539ea",
        "a87d922e4b44b5b03ef78a286beec1f0a4e7b236f0c5e0a705f8e8bc95064b7e",
    ]


def test_only_exact_manager_root_forwarder_is_fun_00489b00():
    r = _payload()["root_forwarding"]
    assert r["only_exact_manager_root_forwarder_from_active_dispatch_callbacks"] == "FUN_00489b00"
    assert r["default_callsite"] == "0x0048adfb"
    assert r["alternate_callsite"] == "0x0048aeec"
    assert r["receiver_expression"] == "participants_subobject - 0x20 == manager root"
    assert r["forwarded_function_mnemonic_sha256"] == "94efca356ec792c61afe2610b40ce2f0e58cb5b230e50f5575689025d56039f5"
    assert r["direct_store_to_manager_plus_0x374"] is False


def test_slice_is_negative_but_deeper_frontier_remains_fail_closed():
    a = _payload()["adjudication"]
    assert a["active_dispatch_callbacks_direct_target_store_reaches_manager_374"] is False
    assert a["active_dispatch_exact_root_forwarder_count"] == 1
    assert a["active_dispatch_root_forwarder_direct_body_reaches_manager_374"] is False
    assert a["active_dispatch_direct_nested_surface_complete"] is True
    assert a["deeper_callees_of_FUN_00489b00_complete"] is False
    assert a["other_participants_lifecycle_nested_callees_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["exact_hdvehicle_64e8_non_sentinel_writer_proven"] is False
    assert a["external_provider_count"] == 7
