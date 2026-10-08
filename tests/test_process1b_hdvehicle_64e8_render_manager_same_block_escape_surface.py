import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_same_block_escape_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_exact_outer_root():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerSameBlockEscapeSurface/1"
    assert data["ready"] is True
    assert data["exact_outer_global"] == "0x00bc185c"
    assert data["upstream_contract"] == "SHIFT.HDVehicle64e8Manager374VSlot0cDispatchClosure/1"


def test_exact_direct_load_inventory_is_pinned():
    scan = load_evidence()["scan"]
    assert scan["direct_load_count"] == 112
    assert scan["seed_register_counts"] == {
        "eax": 43,
        "ecx": 47,
        "edx": 5,
        "ebx": 4,
        "esi": 10,
        "edi": 3,
    }


def test_same_block_escape_surface_is_zero():
    scan = load_evidence()["scan"]
    assert scan["push_escape_count"] == 0
    assert scan["stack_store_escape_count"] == 0
    assert scan["nonstack_memory_store_escape_count"] == 0
    assert scan["total_same_block_escape_count"] == 0


def test_remaining_frontier_stays_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["same_basic_block_direct_load_escape_surface_complete"] is True
    assert adj["same_basic_block_direct_load_can_create_persistent_exact_outer_alias"] is False
    assert adj["cross_block_or_callee_created_alias_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
