import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_scheduler_authority_has_strict_outer_retail_seam():
    policy = (ROOT / "native_runtime/src/runtime_loop_policy.hpp").read_text(
        encoding="utf-8"
    )
    selected_rate_handoff = (
        ROOT / "native_runtime/src/selected_session_physics_tweaker_rate_handoff.hpp"
    ).read_text(encoding="utf-8")
    selected_execution = (
        ROOT / "native_runtime/src/selected_session_retail_vehicle_execution.hpp"
    ).read_text(encoding="utf-8")
    session_header = (
        ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
    ).read_text(encoding="utf-8")
    session_source = (
        ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"
    ).read_text(encoding="utf-8")

    assert "enum class RuntimeSchedulerAuthority" in policy
    assert "HostDevelopment" in policy
    assert "RetailEvidence" in policy
    assert "kNativeContinuousFixedDt = 1.0 / 60.0" in policy
    assert "kHostDevelopmentFixedDt = kNativeContinuousFixedDt" in policy
    assert "RetailOuterSchedulerContract" in policy
    assert "kRetailOuterNominalFrequencyHz = 30.0" in policy
    assert "kRetailOuterGatePeriodMs = 33" in policy
    assert "kRetailNormalOuterIncrementSeconds" in policy
    assert "kRetailSteadySchedulerInvocationsPerDispatch = 1" in policy
    assert "kRetailLoadedInnerRateMaxHz = 65535.0" in policy
    assert "make_retail_outer_scheduler_contract" in policy
    assert "loaded PhysicsTweaker tick rate is required before inner substeps" in policy
    assert "ready_inner_substep_count" in policy
    assert "std::trunc(scaled + 0.5)" in policy
    assert "commit_ready_inner_substeps" in policy
    assert "pending_accumulator_seconds - consumed_seconds" in policy
    assert "Do not clamp that residual to zero" in policy
    assert "positive uint16-shaped integer" in policy

    assert "SelectedSessionPhysicsTweakerRateHandoff" in selected_rate_handoff
    assert "admit_selected_session_physics_tweaker_rate" in selected_rate_handoff
    assert "kSelectedSessionPhysicsTweakerArchiveSha256" in selected_rate_handoff
    assert "kSelectedSessionPhysicsTweakerDecodedSha256" in selected_rate_handoff
    assert "decoded_sha256_verified_this_run" in selected_rate_handoff
    assert "scheduler.admit_loaded_inner_rate" in selected_rate_handoff
    assert "forbidden substitute" in selected_rate_handoff

    assert "SelectedSessionRetailVehicleExecution" in selected_execution
    assert "kMaterializedSelectedSessionPhysicsTweakerRateHandoff" in selected_execution
    assert "make_retail_outer_scheduler_contract" in selected_execution
    assert "admit_selected_session_physics_tweaker_rate" in selected_execution
    assert "execute_retail_outer_dispatch" in selected_execution
    assert "rendered frame or host 1/60 tick" in selected_execution

    assert "NativeVehicleRetailInnerBatchResult" in session_header
    assert "execute_ready_retail_inner_batch" in session_header
    assert "execute_retail_outer_dispatch" in session_header
    assert "scheduler.ready_inner_substep_count()" in session_source
    assert "scheduler.inner_substep_seconds()" in session_source
    assert "execute_explicit_step(runtime, inner_substep_seconds)" in session_source
    assert "scheduler.commit_ready_inner_substeps(recovered_substep_count)" in session_source
    assert "scheduler.admit_outer_dispatch()" in session_source
    assert "execute_ready_retail_inner_batch(runtime, scheduler)" in session_source
    assert "scheduler_before_dispatch" in session_source
    assert "runtime.outer_update = outer_update_before" in session_source
    assert "scheduler = scheduler_before" in session_source
    assert "scheduler = scheduler_before_dispatch" in session_source
    assert "does not connect dispatch admission to a render frame" in session_source
    assert "No constructor/default rate or host 1/60 fallback exists" in session_source

    # Generic scheduler/session code must not hardcode 180 Hz. The numeric value
    # remains confined to the hash-verified generated materialized handoff.
    for forbidden in (
        "kRetailInnerRateHz = 180",
        "kRetailLoadedInnerRateHz = 180",
        "loaded_inner_rate_hz = 180",
        "admit_loaded_inner_rate(180",
        "admit_loaded_inner_rate(180.0",
    ):
        assert forbidden not in policy
        assert forbidden not in selected_rate_handoff
        assert forbidden not in selected_execution
        assert forbidden not in session_source
    assert "constructor default is intentionally not encoded here" in policy
    assert "host 1/60 pacing cannot satisfy retail scheduler/cadence authority" in policy


def test_process2_scheduler_authority_consumes_exact_pc_rate_and_executes_inner_batch():
    packet = json.loads(
        (ROOT / "evidence/process2_runtime_scheduler_authority.json").read_text(
            encoding="utf-8"
        )
    )
    execution = json.loads(
        (ROOT / "evidence/s5_selected_session_retail_vehicle_execution.json").read_text(
            encoding="utf-8"
        )
    )

    assert packet["format"] == "SHIFT.Process2RuntimeSchedulerAuthority/1"
    assert packet["status"] == "retail-outer-and-exact-inner-execution-admitted"
    assert packet["input"]["retail_scheduler_cadence_handoff_present"] is True
    assert packet["input"]["retail_scheduler_cadence_handoff"] == "SHIFT.RetailOuterUpdateCadence/1"
    assert packet["input"]["selected_rate_materializer_contract"] == "SHIFT.SelectedSessionPhysicsTweakerRate/1"
    assert packet["input"]["selected_rate_positive_artifact"] == "evidence/s5_selected_physics_tweaker_rate.json"
    assert packet["input"]["selected_rate_materialized_native_handoff"] == "native_runtime/src/materialized_selected_session_physics_tweaker_rate.hpp"
    assert packet["input"]["selected_rate_typed_native_handoff_ready"] is True
    assert packet["input"]["selected_session_execution_contract"] == "SHIFT.SelectedSessionRetailVehicleExecution/1"
    assert packet["input"]["selected_session_execution_artifact"] == "evidence/s5_selected_session_retail_vehicle_execution.json"
    assert packet["input"]["selected_session_execution_seam"] == "native_runtime/src/selected_session_retail_vehicle_execution.hpp"
    assert packet["input"]["outer_nominal_frequency_hz"] == 30.0
    assert packet["input"]["outer_gate_period_ms"] == 33
    assert packet["input"]["steady_scheduler_invocations_per_dispatch"] == 1
    assert packet["input"]["recovered_inner_substep_count_expression"] == "TRUNC(rate * accumulator + 0.5)"
    assert packet["input"]["recovered_post_batch_accumulator_expression"] == "accumulator - substep_count / rate"
    assert packet["input"]["loaded_rate_shape"] == "positive integral uint16"
    assert packet["input"]["loaded_inner_rate_present"] is True
    assert packet["input"]["loaded_inner_rate_hz"] == 180
    assert packet["input"]["loaded_inner_substep_seconds"] == 1 / 180
    assert packet["input"]["normal_outer_substep_count"] == 6

    output = packet["output"]
    assert output["scheduler_authority_explicit"] is True
    assert output["host_scheduler_authority"] == "HostDevelopment"
    assert output["retail_outer_scheduler_authority"] == "RetailEvidence"
    assert output["host_1_60_is_retail_cadence"] is False
    assert output["retail_host_fallback_rejected"] is True
    assert output["retail_outer_authority_seam_ready"] is True
    assert output["retail_outer_cadence_admitted"] is True
    assert output["selected_rate_materializer_can_emit_typed_native_handoff"] is True
    assert output["selected_rate_native_handoff_exact_resource_identity_locked"] is True
    assert output["selected_rate_native_handoff_forbidden_substitutes_rejected"] is True
    assert output["selected_rate_exact_pc_value_materialized"] is True
    assert output["retail_inner_substep_count_commit_seam_ready"] is True
    assert output["retail_inner_substep_provider_batch_bridge_ready"] is True
    assert output["provider_batch_uses_recovered_inner_substep_seconds"] is True
    assert output["provider_batch_internal_state_rollback_ready"] is True
    assert output["retail_outer_dispatch_provider_transaction_ready"] is True
    assert output["retail_outer_dispatch_pre_admission_rollback_ready"] is True
    assert output["selected_session_execution_seam_ready"] is True
    assert output["selected_session_normal_outer_substeps"] == 6
    assert output["selected_session_two_dispatch_persistent_steps"] == 12
    assert output["signed_accumulator_residual_preserved"] is True
    assert output["loaded_inner_rate_admitted"] is True
    assert output["inner_substep_execution_admitted"] is True
    assert output["provider_semantics_promoted"] is False
    assert output["render_loop_equated_to_outer_dispatch"] is False

    assert execution["format"] == "SHIFT.SelectedSessionRetailVehicleExecution/1"
    assert execution["ready"] is True
    assert execution["selected_session"]["rate_hz"] == 180
    assert execution["selected_session"]["normal_outer_substep_count"] == 6
    assert execution["native_regression"]["two_dispatch_persistent_steps"] == 12
    assert execution["handoff"]["retail_inner_substep_execution_admitted"] is True
    assert execution["handoff"]["retail_control_chain_complete"] is False
    assert execution["limits"]["provider_semantics_promoted"] is False
    assert execution["limits"]["render_frame_equivalence_claimed"] is False
    assert execution["limits"]["host_1_60_used_as_retail_timing"] is False

    consumers = packet["consumer"]
    assert "evidence/s5_selected_physics_tweaker_rate.json" in consumers
    assert "evidence/s5_selected_session_retail_vehicle_execution.json" in consumers
    assert any("admit_selected_session_physics_tweaker_rate" in consumer for consumer in consumers)
    assert any("SelectedSessionRetailVehicleExecution" in consumer for consumer in consumers)
    assert any("execute_ready_retail_inner_batch" in consumer for consumer in consumers)
    assert any("execute_retail_outer_dispatch" in consumer for consumer in consumers)

    limits = packet["limits"]
    assert any("does not infer 180 Hz" in limit for limit in limits)
    assert any("does not auto-schedule" in limit for limit in limits)
    assert any("does not promote Phase 701" in limit for limit in limits)

    ownership = packet["ownership"]
    assert ownership["retail_outer_cadence_blocker_owner"] == "Process 1 positive"
    assert ownership["loaded_inner_rate_blocker_owner"] == "resource/static join positive"
    assert ownership["inner_substep_execution_blocker_owner"] == "native runtime positive"
    assert ownership["next_blocker_owner"] == "static producer/ownership proof"
    assert ownership["process2_state"] == "exact-pc-rate-consumed-through-persistent-inner-batch"
