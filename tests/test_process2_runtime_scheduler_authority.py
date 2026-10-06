import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_scheduler_authority_separates_host_and_retail_consumers():
    policy = (ROOT / "native_runtime/src/runtime_loop_policy.hpp").read_text(
        encoding="utf-8"
    )

    assert "enum class RuntimeSchedulerAuthority" in policy
    assert "HostDevelopment" in policy
    assert "RetailEvidence" in policy
    assert "kNativeContinuousFixedDt = 1.0 / 60.0" in policy
    assert "kHostDevelopmentFixedDt = kNativeContinuousFixedDt" in policy
    assert "kRetailOuterNominalFrequencyHz = 30.0" in policy
    assert "kRetailOuterGatePeriodMilliseconds = 33" in policy
    assert "kRetailOuterNormalIncrementSeconds = 1.0 / 30.0" in policy
    assert "struct RetailOuterUpdateScheduler" in policy
    assert "make_retail_outer_update_scheduler" in policy
    assert "retail_cadence_admitted = false" in policy
    assert "retail_cadence_admitted = true" in policy
    assert "uses_host_development_scheduler" in policy
    assert "uses_admitted_retail_scheduler" in policy
    assert (
        "host 1/60 pacing cannot satisfy retail scheduler/cadence authority"
        in policy
    )
    assert "does not call NativeRuntimeState::fixed_step()" in policy


def test_process2_scheduler_authority_consumes_positive_s5_handoff():
    packet = json.loads(
        (ROOT / "evidence/process2_runtime_scheduler_authority.json").read_text(
            encoding="utf-8"
        )
    )

    assert packet["format"] == "SHIFT.Process2RuntimeSchedulerAuthority/1"
    assert packet["status"] == "retail-authority-consumed"
    assert packet["input"]["retail_scheduler_cadence_handoff_present"] is True
    assert packet["input"]["retail_cadence_contract"] == "SHIFT.RetailOuterUpdateCadence/1"
    assert packet["input"]["retail_cadence_completion_contract"] == "SHIFT.RetailOuterUpdateCadenceCompletion/1"
    output = packet["output"]
    assert output["scheduler_authority_explicit"] is True
    assert output["host_scheduler_authority"] == "HostDevelopment"
    assert output["retail_scheduler_authority"] == "RetailEvidence"
    assert output["host_1_60_is_retail_cadence"] is False
    assert output["retail_host_fallback_rejected"] is True
    assert output["retail_cadence_admitted"] is True
    assert output["retail_outer_scheduler_component_ready"] is True
    assert output["retail_gate_period_ms"] == 33
    assert abs(output["retail_outer_increment_seconds"] - (1.0 / 30.0)) < 1e-15
    assert output["production_outer_update_callback_attached"] is False
    assert packet["ownership"]["retail_cadence_blocker_state"] == "positive-consumed"
    assert packet["ownership"]["next_blocker"].startswith("S6 ")


def test_retail_authority_consumption_keeps_s6_boundary_closed():
    packet = json.loads(
        (ROOT / "evidence/process2_runtime_scheduler_authority.json").read_text(
            encoding="utf-8"
        )
    )
    limits = packet["limits"]
    assert "does not reinterpret NativeRuntimeState::fixed_step() as a retail outer update" in limits
    assert "does not attach any of the nine external vehicle provider boundaries" in limits
    assert "does not freeze the loaded PhysicsTweaker session rate" in limits
    assert "does not make host 1/60 pacing retail-admissible" in limits
    assert "does not treat the BManager worker 10 ms poll sleep as physics cadence" in limits
    assert "does not claim one rendered frame equals one retail outer update" in limits
