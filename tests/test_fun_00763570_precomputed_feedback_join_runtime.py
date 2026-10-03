import pytest

from fun_00763570_precomputed_feedback_join_runtime import (
    BATCH,
    FEEDBACK,
    FORMAT,
    PROVIDER,
    contract,
    execute_fun_00763570_precomputed_feedback_join_runtime,
)


def test_contract_keeps_transform_and_half_step_gates_explicit():
    payload = contract()
    assert payload["format"] == FORMAT == "SHIFT.Fun00763570PrecomputedFeedbackJoinRuntime/1"
    assert payload["source_function"] == "FUN_00763570"
    assert payload["source_child_function"] == "FUN_00755f80"
    assert payload["event_order"] == [PROVIDER, BATCH, FEEDBACK]
    assert payload["native_fun_00763570_batch_used"] is True
    assert payload["phase685_join_reused"] is True
    assert payload["fun_007af010_implemented"] is False
    assert payload["complete_fun_00763570_semantics"] is False
    assert payload["complete_fun_00765470_semantics"] is False


def test_provider_payload_is_forwarded_exactly_before_feedback_continuation():
    events = []
    sentinel = {"wheel_vectors": object()}

    def provider():
        events.append("provider-call")
        return sentinel

    def batch_executor(payload):
        assert payload is sentinel
        events.append("batch-call")
        return {"batch": "ok"}

    def feedback_executor():
        events.append("feedback-call")
        return {"feedback": "ok"}

    result = execute_fun_00763570_precomputed_feedback_join_runtime(
        provider,
        batch_executor,
        feedback_executor,
    )

    assert events == ["provider-call", "batch-call", "feedback-call"]
    assert result.provider_payload is sentinel
    assert result.batch_result == {"batch": "ok"}
    assert result.feedback_result == {"feedback": "ok"}
    assert result.events == (PROVIDER, BATCH, FEEDBACK)


def test_batch_failure_prevents_feedback_execution():
    feedback_calls = 0

    def bad_batch(_payload):
        raise ValueError("bad precomputed vectors")

    def feedback_executor():
        nonlocal feedback_calls
        feedback_calls += 1
        return None

    with pytest.raises(ValueError, match="bad precomputed vectors"):
        execute_fun_00763570_precomputed_feedback_join_runtime(
            lambda: {"payload": 1},
            bad_batch,
            feedback_executor,
        )
    assert feedback_calls == 0


@pytest.mark.parametrize("missing", ["provider", "batch", "feedback"])
def test_missing_required_boundary_fails_closed(missing):
    provider = None if missing == "provider" else (lambda: {})
    batch = None if missing == "batch" else (lambda payload: payload)
    feedback = None if missing == "feedback" else (lambda: {})
    with pytest.raises(ValueError):
        execute_fun_00763570_precomputed_feedback_join_runtime(
            provider,
            batch,
            feedback,
        )
