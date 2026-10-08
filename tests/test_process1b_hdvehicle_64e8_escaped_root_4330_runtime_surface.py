import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_escaped_root_4330_runtime_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_root_is_pinned_by_wrappers():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8EscapedRoot4330RuntimeSurface/1"
    assert data["root_provenance"]["exact_hdvehicle_root"] == "0x00c13700"
    wrappers = data["root_provenance"]["wrappers"]
    assert {w["function"] for w in wrappers} == {"FUN_00702720", "FUN_00702770"}
    assert all("0x00c13700" in w["root_instruction"] for w in wrappers)


def test_runtime_plus_4330_path_is_exact_and_target_negative():
    data = load_evidence()
    path = data["plus_0x4330_path"]
    assert path["materialization"] == "0x00768c16 lea ecx,[esi+0x4330]"
    assert path["callee"] == "FUN_00772570"
    assert path["callee_evidence"]["direct_target_write"] is False
    assert path["callee_evidence"]["only_same_receiver_callee"] == "FUN_00771db0"
    assert path["descendant"]["target_plus_0x21b8_access"] is False
    assert path["descendant"]["same_receiver_forwarding"] is False


def test_frontier_remains_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["escaped_root_to_plus_0x4330_identity_proven"] is True
    assert adj["runtime_path_writes_plus_0x21b8"] is False
    assert adj["runtime_path_surface_complete"] is True
    assert adj["global_non_literal_hdvehicle_64e8_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
