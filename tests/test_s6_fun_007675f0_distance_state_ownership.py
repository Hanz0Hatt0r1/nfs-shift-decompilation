from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007675f0_distance_state_ownership.json"
SETUP_HEADER = ROOT / "native_runtime/include/shift_fun_007675f0_distance_state_setup.hpp"
KERNEL_HEADER = ROOT / "native_runtime/include/shift_contact_outer_kernel.hpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"
CHAIN_SOURCE = ROOT / "native_runtime/src/fun_00770e80_contact_outer_provider_chain.cpp"


def test_distance_state_evidence_preserves_pc_owner_and_scope() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007675f0DistanceStateOwnership/1"
    assert payload["ready"] is True
    assert payload["source"]["function"] == "FUN_007675f0"
    assert payload["source"]["source_line"] == 759784
    state = payload["retail_state"]
    assert state["owner"] == "HDVehicle"
    assert state["offset"] == "0x4080"
    assert state["pass_1_consumes_pass_0_result"] is True
    setup = payload["setup_seed"]
    assert setup["upstream_initializer_proven"] is False
    assert setup["selected_value_promoted"] is False
    assert setup["legacy_seed_is_retail_evidence"] is False
    assert payload["remaining_external_field_count"] == 7
    assert payload["scope"]["external_provider_count_after"] == 7
    assert payload["scope"]["provider_count_reduced"] is False


def test_production_session_payload_has_no_normal_previous_distance_field() -> None:
    header = KERNEL_HEADER.read_text(encoding="utf-8")
    session_struct = header.split("struct ContactOuterSessionInput", 1)[1].split(
        "struct Fun007675f0BodyMotion", 1
    )[0]
    assert "double previous_distance_state" not in session_struct
    assert "compatibility_previous_distance_seed_present" in session_struct
    assert "compatibility_previous_distance_seed" in session_struct
    assert "ContactOuterSessionInput(const ContactOuterKernelInput& legacy)" in session_struct

    session_header = SESSION_HEADER.read_text(encoding="utf-8")
    assert "std::function<physics::ContactOuterSessionInput(std::size_t pass_index)>" in session_header
    assert "Fun007675f0DistanceStateSetup contact_outer_distance_setup" in session_header
    assert "double contact_outer_distance_state_" in session_header


def test_session_commits_and_rolls_back_hdvehicle_4080_state() -> None:
    source = SESSION_SOURCE.read_text(encoding="utf-8")
    chain = CHAIN_SOURCE.read_text(encoding="utf-8")
    setup = SETUP_HEADER.read_text(encoding="utf-8")

    assert "HDVehicle+0x4080" in setup
    assert "validate_fun_007675f0_distance_state_setup" in setup
    assert "contact_outer_distance_state_ = next_state" in source
    assert "contact_outer_distance_state_commit_count" in source
    assert "compose_fun_007675f0_external_input" in source
    assert "distance state used before explicit setup seed" in source
    assert source.count("contact_outer_distance_state_ = distance_state_before") >= 3
    assert source.count("providers_.contact_outer_distance_setup = distance_setup_before") >= 3

    commit = chain.index("distance_state_commit(state->result.filtered_distance_state)")
    result_present = chain.index("state->result_present = true")
    assert result_present < commit
    assert "contact_outer_distance_state_commit_count" in chain
