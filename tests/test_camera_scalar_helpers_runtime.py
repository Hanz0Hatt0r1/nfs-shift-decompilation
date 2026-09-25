from camera_scalar_helpers_runtime import (
    corrective_response,
    deadzone_response,
)


def test_deadzone_response_returns_zero_inside_threshold():
    result = deadzone_response(
        value=2.0,
        bias=0.0,
        threshold=3.0,
        gain=10.0,
        bias_scale=1.0,
    )
    assert result["result"] == 0.0


def test_deadzone_response_uses_opposite_sign_beyond_threshold():
    result = deadzone_response(
        value=5.0,
        bias=0.0,
        threshold=3.0,
        gain=2.0,
        bias_scale=1.0,
    )
    assert result["result"] == -4.0


def test_deadzone_response_includes_scaled_bias_term():
    result = deadzone_response(
        value=-5.0,
        bias=2.0,
        threshold=3.0,
        gain=2.0,
        bias_scale=0.5,
    )
    assert result["result"] == 3.0


def test_corrective_response_rejects_candidate_with_same_sign():
    result = corrective_response(
        value=5.0,
        bias=-100.0,
        threshold=3.0,
        gain=1.0,
        bias_scale=1.0,
    )
    assert result["candidate"] > 0
    assert result["accepted"] is False
    assert result["result"] == 0.0


def test_corrective_response_accepts_sign_reversing_candidate():
    result = corrective_response(
        value=5.0,
        bias=1.0,
        threshold=3.0,
        gain=1.0,
        bias_scale=1.0,
    )
    assert result["candidate"] == -3.0
    assert result["accepted"] is True
    assert result["result"] == -3.0


def test_corrective_response_is_zero_inside_dead_zone():
    result = corrective_response(
        value=-0.5,
        bias=2.0,
        threshold=1.0,
        gain=100.0,
        bias_scale=1.0,
    )
    assert result["result"] == 0.0


def test_corrective_response_accepts_exact_zero_candidate_as_sign_change():
    result = corrective_response(
        value=5.0,
        bias=4.0,
        threshold=3.0,
        gain=1.0,
        bias_scale=0.5,
    )
    assert result["candidate"] == -4.0
    assert result["accepted"] is True

def test_corrective_response_accepts_zero_candidate_when_bias_cancels():
    result = corrective_response(
        value=5.0,
        bias=-4.0,
        threshold=3.0,
        gain=1.0,
        bias_scale=0.5,
    )
    assert result["candidate"] == 0.0
    assert result["accepted"] is True
