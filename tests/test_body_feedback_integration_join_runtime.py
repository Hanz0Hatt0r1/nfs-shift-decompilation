import pytest

from body_feedback_integration_join_runtime import (
    BODY_ARRAY_INTEGRATION,
    POST_SOLVE_FEEDBACK,
    build_body_feedback_integration_join_contract,
    execute_body_feedback_integration_join,
)


def test_contract_freezes_only_proven_anchor_order():
    contract = build_body_feedback_integration_join_contract()
    assert contract["ordered_anchors"] == (
        "FUN_007b4110",
        "FUN_007b2270",
    )
    assert contract["feedback_before_integration_proven"] is True
    assert contract["byte_exact_feedback_to_integration_handoff"] is True
    assert contract["basis_rotation_arithmetic_external"] is True
    assert contract["complete_half_step_implemented"] is False
    assert contract["render_frame_scheduler_proven"] is False


def test_feedback_output_is_exact_integration_input():
    seen = []

    def feedback(payload: bytes) -> bytes:
        seen.append((POST_SOLVE_FEEDBACK, payload))
        return payload + b"F"

    def integration(payload: bytes) -> bytes:
        seen.append((BODY_ARRAY_INTEGRATION, payload))
        return payload + b"I"

    trace = execute_body_feedback_integration_join(b"BODY", feedback, integration)
    assert trace.events == (POST_SOLVE_FEEDBACK, BODY_ARRAY_INTEGRATION)
    assert trace.feedback_output == b"BODYF"
    assert seen == [
        (POST_SOLVE_FEEDBACK, b"BODY"),
        (BODY_ARRAY_INTEGRATION, b"BODYF"),
    ]
    assert trace.output == b"BODYFI"


def test_rejects_invalid_stage_contracts():
    with pytest.raises(ValueError, match="must be callable"):
        execute_body_feedback_integration_join(b"BODY", None, lambda value: value)

    with pytest.raises(ValueError, match="input must be bytes"):
        execute_body_feedback_integration_join(bytearray(b"BODY"), lambda value: value, lambda value: value)

    with pytest.raises(ValueError, match="feedback stage must return bytes"):
        execute_body_feedback_integration_join(b"BODY", lambda value: bytearray(value), lambda value: value)

    with pytest.raises(ValueError, match="integration stage must return bytes"):
        execute_body_feedback_integration_join(b"BODY", lambda value: value, lambda value: bytearray(value))
