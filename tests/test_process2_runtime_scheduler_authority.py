import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_scheduler_authority_has_strict_outer_retail_seam():
    policy = (ROOT / "native_runtime/src/runtime_loop_policy.hpp").read_text(
        encoding="utf-8"
    )

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
    assert "make_retail_outer_scheduler_contract" in policy
    assert "loaded PhysicsTweaker tick rate is required before inner substeps" in policy
    assert "180" not in policy
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
    assert packet["input"]["outer_nominal_frequency_hz"] == 30.0
    assert packet["input"]["outer_gate_period_ms"] == 33
    assert packet["input"]["steady_scheduler_invocations_per_dispatch"] == 1
    assert packet["input"]["loaded_inner_rate_present"] is False

    output = packet["output"]
    assert output["scheduler_authority_explicit"] is True
    assert output["host_scheduler_authority"] == "HostDevelopment"
    assert output["retail_outer_scheduler_authority"] == "RetailEvidence"
    assert output["host_1_60_is_retail_cadence"] is False
    assert output["retail_host_fallback_rejected"] is True
    assert output["retail_outer_authority_seam_ready"] is True
    assert output["retail_outer_cadence_admitted"] is True
    assert output["loaded_inner_rate_admitted"] is False
    assert output["inner_substep_execution_admitted"] is False
    assert output["render_loop_equated_to_outer_dispatch"] is False

    ownership = packet["ownership"]
    assert ownership["retail_outer_cadence_blocker_owner"] == "Process 1 positive"
    assert ownership["loaded_inner_rate_blocker_owner"] == "resource/static join"
    assert ownership["process2_state"] == (
        "strict-retail-outer-authority-seam-ready-awaiting-loaded-inner-rate"
    )
