import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_scheduler_authority_is_explicit_and_fail_closed():
    policy = (ROOT / "native_runtime/src/runtime_loop_policy.hpp").read_text(
        encoding="utf-8"
    )

    assert "enum class RuntimeSchedulerAuthority" in policy
    assert "HostDevelopment" in policy
    assert "RetailEvidence" in policy
    assert "kNativeContinuousFixedDt = 1.0 / 60.0" in policy
    assert "kHostDevelopmentFixedDt = kNativeContinuousFixedDt" in policy
    assert "retail_cadence_admitted = false" in policy
    assert "uses_host_development_scheduler" in policy
    assert "uses_admitted_retail_scheduler" in policy
    assert (
        "host 1/60 pacing cannot satisfy retail scheduler/cadence authority"
        in policy
    )


def test_process2_scheduler_authority_handoff_stays_non_retail_until_proof():
    packet = json.loads(
        (ROOT / "evidence/process2_runtime_scheduler_authority.json").read_text(
            encoding="utf-8"
        )
    )

    assert packet["format"] == "SHIFT.Process2RuntimeSchedulerAuthority/1"
    assert packet["status"] == "ready-gate"
    assert packet["input"]["retail_scheduler_cadence_handoff_present"] is False
    assert packet["output"]["scheduler_authority_explicit"] is True
    assert packet["output"]["host_scheduler_authority"] == "HostDevelopment"
    assert packet["output"]["future_retail_scheduler_authority"] == "RetailEvidence"
    assert packet["output"]["host_1_60_is_retail_cadence"] is False
    assert packet["output"]["retail_host_fallback_rejected"] is True
    assert packet["output"]["retail_cadence_admitted"] is False
    assert packet["ownership"]["current_retail_cadence_blocker_owner"] == "Process 1"
