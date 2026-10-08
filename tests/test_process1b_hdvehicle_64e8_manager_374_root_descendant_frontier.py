import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_root_descendant_frontier.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_authority_are_pinned():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager374RootDescendantFrontier/1"
    assert p["ready"] is True
    assert p["authority"]["platform"] == "PC retail 1.02"
    assert p["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def test_only_one_fun_00489b00_direct_call_preserves_exact_manager_root():
    p = _payload()["direct_calls"]
    assert p["total"] == 19
    rows = p["exact_manager_root_receiver_calls"]
    assert len(rows) == 1
    assert rows[0]["callsite"] == "0x00489ba0"
    assert rows[0]["resolved_target"] == "FUN_00d610c0"
    assert rows[0]["target_mnemonic_sha256"] == "5179b20172367b4afe38710d15add64a58b1c27309435fa6325419619382b5e2"


def test_root_descendant_switches_to_manager_2d8_or_selected_object_domains():
    d = _payload()["resolved_root_descendant"]
    assert d["root_to_subobject_transition"] == "lea edi,[ecx+0x2d8]"
    assert d["direct_manager_root_plus_0x374_store"] is False
    assert d["manager_root_receiver_preserved_to_any_direct_callee"] is False
    assert len(d["observed_direct_calls"]) == 10
    assert all("manager root" not in row.lower() for row in d["observed_direct_calls"])


def test_adjudication_closes_only_receiver_preserving_active_dispatch_descendants():
    a = _payload()["adjudication"]
    assert a["FUN_00489b00_exact_root_receiver_direct_descendant_count"] == 1
    assert a["FUN_00489b00_exact_root_receiver_direct_descendant_reaches_manager_374"] is False
    assert a["FUN_00d610c0_preserves_manager_root_to_descendants"] is False
    assert a["active_dispatch_receiver_preserving_root_descendant_surface_complete"] is True
    assert a["participants_vtable_plus_0x0c_indirect_surface_complete"] is False
    assert a["unrelated_manager_alias_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["exact_hdvehicle_64e8_non_sentinel_writer_proven"] is False
    assert a["external_provider_count"] == 7
