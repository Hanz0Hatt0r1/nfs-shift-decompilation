import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_root_derived_4330_materializer_persistence_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_materializer_inventory_and_authority():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RootDerived4330MaterializerPersistenceClosure/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["adjudication"]["exact_root_affine_materializer_count"] == 3
    assert data["adjudication"]["escaped_wrapper_materializer_count"] == 1
    assert {item["function"] for item in data["materializer_lifetimes"]} == {
        "FUN_00769520", "FUN_0076b130", "FUN_0076df50", "FUN_00768a4d"
    }


def test_no_materializer_level_store_or_return():
    data = load_evidence()
    for item in data["materializer_lifetimes"]:
        assert item["exact_alias_returned"] is False
        if item["function"] == "FUN_0076df50":
            assert item["memory_store_while_exact_alias_live"] is False
            assert item["non_call_stack_persistence_while_exact_alias_live"] is False
            assert item["alias_kill"] == "0x0076e28e xor ebx,ebx"
            assert item["all_forwarded_consumer_writer_surfaces_already_bounded_negative"] is True
        else:
            assert item["memory_store_before_terminal_use"] is False
            assert item["stack_persistence_before_terminal_use"] is False


def test_fail_closed_frontier_is_preserved():
    adj = load_evidence()["adjudication"]
    assert adj["materializer_level_exact_alias_memory_store_count"] == 0
    assert adj["materializer_level_exact_alias_return_count"] == 0
    assert adj["materializer_level_unbounded_forward_count"] == 0
    assert adj["root_derived_materializer_persistence_return_surface_complete"] is True
    assert adj["downstream_consumer_persistence_return_surface_complete"] is False
    assert adj["global_runtime_derived_4330_alias_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
