import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_delayed_stack_alias_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_upstream():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374DelayedStackAliasSurface/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["upstream_contract"] == "SHIFT.HDVehicle64e8Manager374GetterLocalAliasSurface/1"


def test_exact_four_delayed_alias_functions_are_pinned():
    data = load_evidence()
    funcs = data["surface"]["functions"]
    assert data["surface"]["candidate_count"] == 4
    assert {entry["function"] for entry in funcs} == {
        "FUN_00492520",
        "FUN_00496680",
        "FUN_004bad20",
        "FUN_0051df70",
    }
    assert {entry["getter_callsite"] for entry in funcs} == {
        "0x00492591",
        "0x004966c3",
        "0x004bad36",
        "0x0051df7a",
    }


def test_delayed_aliases_do_not_escape_or_write_manager_target():
    for entry in load_evidence()["surface"]["functions"]:
        assert entry["root_forwarded_to_callee"] is False
        assert entry["root_written_through"] is False
        assert entry["target_plus_0x374_write"] is False


def test_participant_entry_writes_are_not_promoted_to_manager_root():
    data = load_evidence()
    bad20 = next(entry for entry in data["surface"]["functions"] if entry["function"] == "FUN_004bad20")
    assert bad20["participant_entry_writes"] == ["entry+0x219c", "entry+0x21a0"]
    assert bad20["participant_entry_writes_are_manager_root_writes"] is False


def test_frontier_stays_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["delayed_register_to_stack_alias_count"] == 4
    assert adj["surface_complete_for_this_pattern"] is True
    assert adj["surface_can_write_manager_plus_0x374"] is False
    assert adj["object_field_or_global_storage_of_manager_root_complete"] is False
    assert adj["unrelated_manager_root_reconstruction_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
