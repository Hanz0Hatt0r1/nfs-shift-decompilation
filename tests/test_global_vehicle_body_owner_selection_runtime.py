from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from global_vehicle_body_owner_selection_runtime import (
    GlobalVehicleBodyOwnerIdentityHandoff,
    RETAIL_BODY_OWNER_POINTER_FIELD_OFFSET,
    RETAIL_GLOBAL_VEHICLE_ADDRESS,
    blocked_identity_fixture,
    build_selection,
    contract,
    retail_positive_handoff,
    synthetic_positive_handoff,
)


def test_current_retail_composed_identity_selects_exact_body_zero() -> None:
    assert build_selection(retail_positive_handoff()) == {
        "selection_proven": True,
        "body_index": 0,
    }


def test_blocked_fixture_remains_fail_closed() -> None:
    with pytest.raises(ValueError, match="not retail-ready"):
        build_selection(blocked_identity_fixture())


def test_committed_process1_retail_evidence_matches_reference_producer() -> None:
    evidence = json.loads(
        Path("evidence/global_vehicle_body_owner_identity_retail.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["format"] == "SHIFT.GlobalVehicleBodyOwnerIdentity/1"
    join = evidence["identity_join"]
    handoff = evidence["handoff"]
    assert int(join["global_vehicle_address"], 16) == RETAIL_GLOBAL_VEHICLE_ADDRESS
    assert int(join["BODY_array_owner_pointer_field_offset"], 16) == (
        RETAIL_BODY_OWNER_POINTER_FIELD_OFFSET
    )
    assert join["BODY_array_owner_is_global_vehicle_base"] is False
    assert join["BODY_array_owner_pointer_loaded_from_global_vehicle_base"] is True
    assert handoff["vehicle_BODY_selection_ready"] is True
    assert handoff["selected_BODY_index"] == 0
    assert handoff["phase698_positive_selection_admissible"] is True
    assert handoff["phase700_runtime_handoff_admissible"] is True


def test_obsolete_update_child_gate_is_rejected() -> None:
    bad = replace(
        retail_positive_handoff(),
        phase703_update_child_equality_gate_required=True,
    )
    with pytest.raises(ValueError, match="obsolete update-child equality gate"):
        build_selection(bad)


def test_readiness_flags_must_move_transactionally() -> None:
    bad = replace(retail_positive_handoff(), phase700_runtime_handoff_admissible=False)
    with pytest.raises(ValueError, match="readiness flags disagree"):
        build_selection(bad)


def test_blocked_identity_cannot_preclaim_body_zero() -> None:
    with pytest.raises(ValueError, match="preclaims a BODY index"):
        build_selection(GlobalVehicleBodyOwnerIdentityHandoff(selected_body_index=0))


def test_positive_identity_cannot_select_non_chassis_body() -> None:
    with pytest.raises(ValueError, match="must select BODY 0"):
        build_selection(replace(synthetic_positive_handoff(), selected_body_index=9))


def test_contract_tracks_process1_and_remaining_transform_boundary() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.NativeGlobalVehicleBodyOwnerSelection/1"
    assert payload["process1_contract"] == "SHIFT.GlobalVehicleBodyOwnerIdentity/1"
    assert payload["current_retail_global_vehicle_BODY_owner_identity_ready"] is True
    assert payload["current_retail_selected_BODY_index"] == 0
    assert payload["retail_global_vehicle_address"] == RETAIL_GLOBAL_VEHICLE_ADDRESS
    assert payload["retail_BODY_owner_pointer_field_offset"] == (
        RETAIL_BODY_OWNER_POINTER_FIELD_OFFSET
    )
    assert payload["BODY_array_owner_is_global_vehicle_base"] is False
    assert payload["BODY_array_owner_pointer_loaded_from_global_vehicle_base"] is True
    assert payload["retail_BMW_chassis_BODY_index"] == 0
    assert payload["obsolete_update_child_equality_gate_required"] is False
    assert payload["synthetic_positive_identity_is_retail_proof"] is False
    assert payload["phase698_selector_reused"] is True
    assert payload["phase700_runtime_handoff_reused"] is True
    assert payload["phase646_dynamic_transform_transport_available"] is True
    assert payload["phase649_persistent_vulkan_upload_available"] is True
    assert payload["BODY0_bind_frame_proof_ready"] is False
    assert payload["fixed_step_auto_schedule"] is False
    assert payload["original_game_executed"] is False
    assert payload["new_runtime_capture_required"] is False
