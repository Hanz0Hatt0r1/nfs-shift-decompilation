import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_2a0_selector_machine_proof.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_root():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager2a0SelectorMachineProof/1"
    assert p["ready"] is True
    assert p["function"]["name"] == "FUN_0045da80"
    assert p["machine_proof"]["singleton_getter_call"] == "0x0045da84 CALL 0x00489ad0"
    assert p["machine_proof"]["singleton_capture"] == "0x0045da8c MOV ESI,EAX"


def test_exact_collection_selection_path():
    p = _payload()
    m = p["machine_proof"]
    assert m["collection_receiver"] == "0x0045daa3 LEA ECX,[ESI+0x2a0]"
    assert m["index_accessor_call"] == "0x0045daa9 CALL FUN_0054ed00"
    assert m["selected_entry_store"] == "0x0045daae MOV [ESI+0x378],EAX"
    assert p["adjudication"]["singleton_manager_root_proven"] is True
    assert p["adjudication"]["manager_plus_0x2a0_indexed_selection_proven"] is True
    assert p["adjudication"]["manager_plus_0x378_receives_selected_entry_or_zero"] is True


def test_accessor_is_read_only_and_identity_remains_open():
    p = _payload()
    assert p["collection_accessor"]["function"] == "FUN_0054ed00"
    assert p["collection_accessor"]["mutation"] is False
    assert p["adjudication"]["manager_plus_0x2a0_insertion_producer_proven"] is False
    assert p["adjudication"]["selected_entry_identity_is_hdvehicle_4330"] is False


def test_semantic_gates_stay_fail_closed():
    a = _payload()["adjudication"]
    assert a["manager_plus_0x374_join_complete"] is False
    assert a["exact_hdvehicle_64e8_non_sentinel_writer_proven"] is False
    assert a["retail_input_control_provenance_proven"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
