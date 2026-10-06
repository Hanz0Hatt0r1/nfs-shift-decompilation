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

    # Constructor-default 180 Hz may exist in evidence, but it must never be
    # encoded as an admitted runtime inner rate. Avoid a raw substring check:
    # the exact recovered 1/30 constant itself contains the digits "180".
    for forbidden in (
        "kRetailInnerRateHz = 180",
        "kRetailLoadedInnerRateHz = 180",
        "loaded_inner_rate_hz = 180",
        "admit_loaded_inner_rate(180",
        "admit_loaded_inner_rate(180.0",
    ):
        assert forbidden not in policy
        assert forbidden not in selected_rate_handoff
        assert forbidden not in session_source
    assert "constructor default is intentionally not encoded here" in policy

    assert (
        "host 1/60 pacing cannot satisfy retail scheduler/cadence authority"
        in policy
    )


def test_process2_scheduler_authority_consumes_outer_proof_but_blocks_inner_rate():
    packet = json.loads(
        (ROOT / "evidence/process2_runtime_scheduler_authority.json").read_text(
            encoding="utf-8"
        )
    )

    assert packet["format"] == "SHIFT.Process2RuntimeSchedulerAuthority/1"
    assert packet["status"] == "outer-retail-seam-ready-inner-rate-blocked"
    assert packet["input"]["retail_scheduler_cadence_handoff_present"] is True
    assert packet["input"]["retail_scheduler_cadence_handoff"] == "SHIFT.RetailOuterUpdateCadence/1"
    assert packet["input"]["selected_rate_materializer_contract"] == (
        "SHIFT.SelectedSessionPhysicsTweakerRate/1"
    )
    assert packet["input"]["selected_rate_typed_native_handoff_ready"] is True
    assert packet["input"]["outer_nominal_frequency_hz"] == 30.0
    assert packet["input"]["outer_gate_period_ms"] == 33
    assert packet["input"]["steady_scheduler_invocations_per_dispatch"] == 1
    assert packet["input"]["recovered_inner_substep_count_expression"] == (
        "TRUNC(rate * accumulator + 0.5)"
    )
    assert packet["input"]["recovered_post_batch_accumulator_expression"] == (
        "accumulator - substep_count / rate"
    )
    assert packet["input"]["loaded_rate_shape"] == "positive integral uint16"
    assert packet["input"]["loaded_inner_rate_present"] is False

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
    assert output["retail_inner_substep_count_commit_seam_ready"] is True
    assert output["retail_inner_substep_provider_batch_bridge_ready"] is True
    assert output["provider_batch_uses_recovered_inner_substep_seconds"] is True
    assert output["provider_batch_internal_state_rollback_ready"] is True
    assert output["retail_outer_dispatch_provider_transaction_ready"] is True
    assert output["retail_outer_dispatch_pre_admission_rollback_ready"] is True
    assert output["signed_accumulator_residual_preserved"] is True
    assert output["loaded_inner_rate_admitted"] is False
    assert output["inner_substep_execution_admitted"] is False
    assert output["render_loop_equated_to_outer_dispatch"] is False

    consumers = packet["consumer"]
    assert any("--native-handoff-out" in consumer for consumer in consumers)
    assert any(
        "admit_selected_session_physics_tweaker_rate" in consumer
        for consumer in consumers
    )
    assert any(
        "execute_ready_retail_inner_batch" in consumer
        for consumer in consumers
    )
    assert any(
        "execute_retail_outer_dispatch" in consumer
        for consumer in consumers
    )

    limits = packet["limits"]
    assert any("does not auto-schedule" in limit for limit in limits)
    assert any("does not promote Phase 701" in limit for limit in limits)

    ownership = packet["ownership"]
    assert ownership["retail_outer_cadence_blocker_owner"] == "Process 1 positive"
    assert ownership["loaded_inner_rate_blocker_owner"] == "resource/static join"
    assert ownership["process2_state"] == (
        "typed-selected-rate-handoff-and-atomic-retail-dispatch-bridge-ready-awaiting-exact-pc-rate"
    )
