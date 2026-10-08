import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_participants_registry_vtable.json"
COORD = ROOT / "coordination" / "decomp_blockers.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_exact_vtable_entries():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager374ParticipantsRegistryVtable/1"
    assert p["ready"] is True
    assert p["participants_subobject"]["vtable_address"] == "0x00ab916c"
    entries = p["vtable"]["entries"]
    assert len(entries) == 9
    assert entries[2] == {
        "slot": 2,
        "entry": "0x00ab9174",
        "raw_hex": "f0714800",
        "target": "FUN_004871f0",
    }
    assert entries[5]["target"] == "FUN_00488970"


def test_registry_virtual_paths_normalize_to_manager_374_clear():
    paths = _payload()["registry_dispatch"]["clear_paths"]
    assert len(paths) == 2
    assert paths[0]["path"] == "FUN_0065b990 -> FUN_00648640 -> vslot +0x8 -> FUN_004871f0"
    assert paths[0]["normalized_write"] == "manager+0x374 = 0"
    assert "vslot +0x14" in paths[1]["path"]
    assert paths[1]["normalized_write"] == "manager+0x374 = 0"


def test_nonzero_pointer_publication_stays_fail_closed():
    p = _payload()
    a = p["adjudication"]
    assert a["escaped_participants_alias_can_clear_manager_374"] is True
    assert a["escaped_participants_alias_nonzero_manager_374_writer_proven"] is False
    assert a["manager_374_clear_writer_proven"] is True
    assert a["manager_374_selected_hdvehicle_writer_proven"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["retail_input_control_provenance_proven"] is False
    assert a["external_provider_count"] == 7


def test_exact_manager_root_helper_candidate_is_retained_not_promoted():
    c = _payload()["separate_helper_candidate"]
    assert c["thunk"] == "thunk_FUN_00d60660"
    assert c["thunk_address"] == "0x00487240"
    assert c["body_address"] == "0x00d60660"
    assert c["direct_callers"] == ["FUN_00465860@0x00465bae", "FUN_00468ed0@0x004690b5"]
    assert c["receiver_at_both_callers"] == "FUN_00489ad0() manager root"
    assert c["decompiler_contains_manager_374_assignment"] is True
    assert c["status"] == "machine-branch-proof-required-before-nonzero-writer-promotion"


def test_coordination_advances_to_machine_proof_candidate():
    graph = json.loads(COORD.read_text(encoding="utf-8"))
    p13 = next(row for row in graph["workstreams"] if row["id"] == "P1.3")
    node = next(row for row in p13["children"] if row["id"] == "P1.3.manager374")
    assert node["status"] == "participants-registry-clear-proven-nonzero-helper-candidate-open"
    assert node["manager_374_clear_writer_proven"] is True
    assert node["nonzero_helper_candidate"] == "thunk_FUN_00d60660 -> FUN_00d60660"
    assert "exact instruction" in node["next"].lower()
