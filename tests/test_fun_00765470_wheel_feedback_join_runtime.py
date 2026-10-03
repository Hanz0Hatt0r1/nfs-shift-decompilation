import pytest

from fun_00765470_wheel_feedback_join_runtime import (
    BODY_ARRAY_INTEGRATION,
    FORMAT,
    POST_SOLVE_FEEDBACK,
    WHEEL_SHARED_TRIPLET,
    contract,
    execute_wheel_feedback_join,
)


def test_contract_preserves_only_proven_half_step_anchors():
    payload = contract()
    assert payload["format"] == FORMAT
    assert payload["required_order"] == [
        WHEEL_SHARED_TRIPLET,
        POST_SOLVE_FEEDBACK,
        BODY_ARRAY_INTEGRATION,
    ]
    assert payload["phase679_join_reused"] is True
    assert payload["intervening_local_work_modeled"] is False
    assert payload["complete_fun_00765470_semantics"] is False
    assert payload["wheel_shared_triplet_callback_external"] is True
    assert payload["feedback_integration_bytes_reconstructed"] is False


def test_wheel_anchor_runs_before_byte_exact_phase679_handoff():
    observed = []
    original = bytes(range(32))
    replacement = bytes(reversed(range(32)))

    def wheel_anchor():
        observed.append(WHEEL_SHARED_TRIPLET)

    def feedback_integration(payload):
        observed.append("feedback-entry")
        assert payload is original
        return replacement

    result = execute_wheel_feedback_join(original, wheel_anchor, feedback_integration)
    assert observed == [WHEEL_SHARED_TRIPLET, "feedback-entry"]
    assert result.body_bytes is replacement
    assert result.events == (
        WHEEL_SHARED_TRIPLET,
        POST_SOLVE_FEEDBACK,
        BODY_ARRAY_INTEGRATION,
    )
    assert result.wheel_shared_triplet_anchor_count == 1


def test_missing_callbacks_and_nonbyte_feedback_fail_closed():
    with pytest.raises(ValueError, match="FUN_00763570"):
        execute_wheel_feedback_join(b"", None, lambda payload: payload)
    with pytest.raises(ValueError, match="Phase 679"):
        execute_wheel_feedback_join(b"", lambda: None, None)
    with pytest.raises(ValueError, match="must return bytes"):
        execute_wheel_feedback_join(b"", lambda: None, lambda payload: bytearray(payload))
