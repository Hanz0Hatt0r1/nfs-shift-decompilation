import copy

from native_vehicle_participant_bridge import (
    FORMAT,
    build_native_vehicle_participant_bridge,
)
from physics_participant_registry_update_runtime import (
    build_physics_participant_registry_update,
)
from vehicle_physics_participant_gate_runtime import (
    build_vehicle_physics_participant_gate,
)
from vehicle_physics_participant_process_runtime import (
    build_vehicle_physics_participant_process,
)
from vehicle_physics_selector_context_runtime import (
    build_vehicle_physics_selector_context,
)


def test_phase602_bridge_preserves_manager_selector_separation():
    report = build_native_vehicle_participant_bridge()

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["native_participant_topology_ready"] is True
    assert report["native_participant_ready"] is False
    assert report["native_registry_index"] == -1
    assert report["native_selector_ordinal"] == -1
    assert report["native_process_state"] == -1

    topology = report["topology"]
    assert topology["participant_manager_global"] == "DAT_00c109e0"
    assert topology["selector_global"] == "DAT_00bbc600"
    assert topology["manager_selector_same_object_proven"] is False
    assert topology["manager_slot_stride_bytes"] == 0x1FA0
    assert topology["manager_registry_index_source_offset"] == 0x3C
    assert topology["igphase_selected_pointer_offset"] == 0x450
    assert topology["igphase_selector_ordinal_offset"] == 0x454
    assert topology["igphase_process_state_offset"] == 0x45C
    assert topology["selector_candidate_ready_offset"] == 0x74

    boundary = report["boundary"]
    assert boundary["registry_index_equals_selector_ordinal"] is False
    assert boundary["registry_selector_identity_join_proven"] is False
    assert boundary["participant_pointer_transport"] == "not-performed"
    assert boundary["runtime_participant_instance_observed"] is False
    assert boundary["provider_identity_assigned"] is False
    assert boundary["force_application_assigned"] is False


def test_phase602_bridge_rejects_manager_selector_conflation():
    selector = build_vehicle_physics_selector_context()
    selector = copy.deepcopy(selector)
    selector["context"]["global_instance"] = "DAT_00c109e0"
    selector["separation"]["selector_global"] = "DAT_00c109e0"

    report = build_native_vehicle_participant_bridge(
        selector_context=selector,
    )

    assert report["ready"] is False
    assert "native-participant:selector-global-mismatch" in report[
        "blocking_reasons"
    ]
    assert "native-participant:manager-selector-conflated" in report[
        "blocking_reasons"
    ]


def test_phase602_bridge_rejects_selector_ordinal_registry_index_alias():
    process = build_vehicle_physics_participant_process()
    process = copy.deepcopy(process)
    process["relationship_to_phase505"]["same_slots"] = False

    report = build_native_vehicle_participant_bridge(
        participant_process=process,
    )

    assert report["ready"] is False
    assert "native-participant:phase505-slot-join-missing" in report[
        "blocking_reasons"
    ]


def test_phase602_bridge_rejects_registry_index_source_drift():
    registry = build_physics_participant_registry_update()
    registry = copy.deepcopy(registry)
    registry["participant_callsite"]["participant_index_source"] = (
        "IGPhaseVehicle+0x454"
    )

    report = build_native_vehicle_participant_bridge(
        registry_update=registry,
    )

    assert report["ready"] is False
    assert "native-participant:registry-index-source-mismatch" in report[
        "blocking_reasons"
    ]


def test_phase602_bridge_rejects_unready_source_contract():
    gate = build_vehicle_physics_participant_gate()
    gate = copy.deepcopy(gate)
    gate["ready"] = False
    gate["status"] = "blocked"

    report = build_native_vehicle_participant_bridge(
        participant_gate=gate,
    )

    assert report["ready"] is False
    assert "native-participant:participant_gate:not-ready" in report[
        "blocking_reasons"
    ]
