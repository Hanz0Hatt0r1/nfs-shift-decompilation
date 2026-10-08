import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_378_selection_frontier.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_authority():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager378SelectionFrontier/1"
    assert p["ready"] is True
    assert p["authority"]["platform"] == "PC retail 1.02"
    assert p["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def test_exact_singleton_root_and_selection_path():
    p = _payload()
    proof = p["selection_machine_proof"]
    assert p["target"]["manager_getter"] == "FUN_00489ad0"
    assert p["target"]["selection_function"] == "FUN_0045da80"
    assert "0x0045da84 call FUN_00489ad0" in proof["instructions"]
    assert "0x0045daa3 lea ecx,[esi+0x2a0]" in proof["instructions"]
    assert "0x0045daa9 call FUN_0054ed00" in proof["instructions"]
    assert "0x0045daae mov [esi+0x378],eax" in proof["instructions"]
    assert proof["adjudication"]["receiver_is_exact_singleton_manager"] is True
    assert proof["adjudication"]["accessor_return_is_written_to_manager_378"] is True


def test_collection_accessor_formula():
    p = _payload()
    accessor = p["collection_accessor"]
    assert accessor["function"] == "FUN_0054ed00"
    assert accessor["normal_return_formula"] == "collection_base(+0x30) + index * stride(+0x00)"
    assert accessor["manager_normalized_fields"] == {
        "stride": "manager+0x2a0",
        "count": "manager+0x2c8",
        "base": "manager+0x2d0",
    }


def test_374_378_are_distinct_and_only_compared_for_identity():
    p = _payload()
    relation = p["manager_374_378_relation"]
    assert relation["same_storage"] is False
    assert relation["values_can_be_compared_for_identity"] is True
    assert relation["hdvehicle_4330_identity_proven"] is False
    assert len(relation["proven_comparison_sites"]) >= 2


def test_fail_closed_semantic_gates():
    p = _payload()["adjudication"]
    assert p["manager_2a0_entry_identity_to_hdvehicle_4330_complete"] is False
    assert p["manager_374_identity_to_hdvehicle_4330_complete"] is False
    assert p["exact_hdvehicle_64e8_non_sentinel_writer_proven"] is False
    assert p["retail_input_control_provenance_proven"] is False
    assert p["p1_3_control_producer_complete"] is False
    assert p["external_provider_count"] == 7
