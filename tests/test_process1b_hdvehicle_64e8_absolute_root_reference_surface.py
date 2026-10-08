import json
from pathlib import Path


EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_absolute_root_reference_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_authority_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8AbsoluteRootReferenceSurface/1"
    assert data["ready"] is True
    assert data["authority"]["platform"] == "PC retail 1.02"
    assert data["authority"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )


def test_exact_absolute_root_reference_set_is_closed():
    data = load_evidence()
    refs = data["absolute_root_references"]
    assert [entry["instruction"] for entry in refs] == [
        "0x00702715",
        "0x0070274d",
        "0x00702776",
        "0x007027ac",
    ]
    assert {entry["function"] for entry in refs} == {
        "FUN_00702710",
        "FUN_00702720",
        "FUN_00702770",
    }
    assert data["adjudication"]["absolute_reference_surface_complete"] is True


def test_absolute_root_consumers_do_not_reach_plus_0x21b8():
    data = load_evidence()
    proof = data["bounded_callee_proof"]
    assert proof["FUN_00771e40"]["direct_store_max_root_offset"] == "+0x2178"
    assert proof["FUN_00771e40"]["writes_target_plus_0x21b8"] is False
    assert proof["FUN_00771e40"]["forwards_exact_root_to_other_callees"] is False
    assert proof["FUN_00772350"]["forwards_exact_root_only_to"] == ["FUN_00771e40"]
    assert proof["FUN_00772350"]["writes_target_plus_0x21b8"] is False
    assert data["adjudication"]["absolute_root_reference_path_writes_hdvehicle_plus_0x64e8"] is False


def test_frontier_stays_fail_closed():
    data = load_evidence()
    adjudication = data["adjudication"]
    assert adjudication["non_literal_hdvehicle_64e8_writer_surface_complete"] is False
    assert adjudication["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adjudication["last_literal_0x004b86cf_rejected"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7
