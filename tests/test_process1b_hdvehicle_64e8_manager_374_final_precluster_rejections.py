import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_final_precluster_rejections.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_upstream_worklist():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374FinalPreclusterRejections/2"
    assert data["ready"] is True
    assert data["corrects"] == "SHIFT.HDVehicle64e8Manager374FinalPreclusterRejections/1"
    assert data["upstream"]["remaining_literal_site_count"] == 5


def test_00865013_target_base_is_entry_ecx_not_first_argument():
    data = load_evidence()
    row = data["correction"]
    assert row["site"] == "0x00865013"
    assert row["function"] == "FUN_00864c10"
    assert data["adjudication"]["prior_00865013_first_stack_argument_claim_rejected"] is True
    assert row["entry_receiver_chain"][0] == "0x00864c40 mov edi,ecx"
    assert "0x00864d63 mov esi,[ebp-0x34]" in row["entry_receiver_chain"]
    assert "0x00864db5 mov esi,[ebp-0x34] restores entry ECX again" in row["entry_receiver_chain"]
    assert row["machine_window"]["sha256"] == "8ae83797d2f0a6bd6120737d84df25ce8a50ff1f4ad35122997277e2acea033a"
    assert row["can_write_manager_plus_0x374"] is False


def test_00865013_caller_this_vptr_rejects_manager_identity():
    row = load_evidence()["correction"]
    callers = row["direct_callers"]
    assert callers["count"] == 2
    assert callers["callsites"] == ["0x0085b6f2", "0x0085c38f"]
    ident = row["caller_this_identity"]
    assert ident["vptr"] == "0x00b1d508"
    assert ident["slot_0x18"] == "0x0085b6e0"
    assert ident["slot_0x1c"] == "0x0085c370"
    assert ident["participants_manager_root_vptr"] == "0x00ab9190"
    assert ident["participants_manager_subobject_vptr"] == "0x00ab916c"
    assert ident["receiver_is_participants_manager_root"] is False
    assert ident["receiver_is_participants_manager_subobject"] is False


def test_0097ed06_is_nonzero_producer_negative_only():
    row = load_evidence()["rejections"][1]
    assert row["site"] == "0x0097ed06"
    assert row["zero_source"] == "0x0097ecbe xor ebx,ebx"
    assert row["receiver_identity_required_for_nonzero_producer_rejection"] is False
    assert row["receiver_identity_complete"] is False
    assert row["can_place_hdvehicle_plus_0x4330_into_manager_plus_0x374"] is False


def test_only_fmod_literal_sites_remain_and_global_gates_stay_closed():
    adj = load_evidence()["adjudication"]
    assert adj["closed_site_count_this_contract"] == 2
    assert adj["remaining_literal_site_count"] == 3
    assert adj["remaining_literal_sites"] == ["0x0097da09", "0x0097daf8", "0x0097dc63"]
    assert adj["literal_manager_374_receiver_provenance_complete"] is False
    assert adj["computed_address_manager_374_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
