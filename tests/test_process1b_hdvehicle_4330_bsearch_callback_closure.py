import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "p1b_hdvehicle_4330_bsearch_callback_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_two_machine_proven_bsearch_registrations():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1B.HDVehicle4330BsearchCallbackClosure/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["bsearch"]["target"] == "0x0090421d"
    assert data["bsearch"]["physical_callsite_count"] == 2
    assert data["bsearch"]["callsites"] == ["0x0053c2da", "0x00a5df75"]
    assert [row["comparator"] for row in data["registrations"]] == ["0x0053c280", "0x00a5df20"]
    assert data["registrations"][0]["decompiler_unaff_retaddr_is_artifact"] is True


def test_no_p1b_carrier_comparator_and_global_gates_stay_closed():
    data = load_evidence()
    assert data["exact_carrier_comparator_hits"] == []
    adj = data["adjudication"]
    assert adj["bsearch_physical_callsite_surface_complete"] is True
    assert adj["bsearch_comparator_provenance_complete"] is True
    assert adj["bsearch_exact_p1b_carrier_hit_found"] is False
    assert adj["bsearch_exact_p1b_carrier_hit_count"] == 0
    assert adj["remaining_callback_api_families_ruled_out"] is False
    assert adj["runtime_generated_or_copied_function_pointers_ruled_out"] is False
    assert adj["computed_or_encoded_code_pointers_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
