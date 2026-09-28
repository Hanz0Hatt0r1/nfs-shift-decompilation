import specialized_provider_reset_effect_correlation_runtime as runtime


def _reset_event(
    count: int,
    frame: int,
    selector: int,
    provider_id: int = 0,
):
    return {
        "call_index": count,
        "frame_index": frame,
        "physics_system": 0x1000,
        "provider_pointer": 0x2000,
        "provider_vtable": (
            0x00B0FC5C if provider_id == 0 else 0x00B0FC8C
        ),
        "provider_id": provider_id,
        "scalar_count": 40 if provider_id == 0 else 34,
        "selector": selector,
        "caller_return_address": 0x007B4029,
    }


def _effect(
    count: int,
    frame: int,
    selector: int,
    provider_id: int = 0,
):
    vtable = 0x00B0FC5C if provider_id == 0 else 0x00B0FC8C
    return {
        "provider_id": provider_id,
        "provider_pointer": 0x2000,
        "provider_vtable": vtable,
        "selector": selector,
        "frame_index": frame,
        "reset_event_count": count,
        "addresses": {
            "diagonal": "0x1000",
            "output": "0x2000",
        },
        "values": {
            "diagonal_before": 0.0,
            "diagonal_after": 1.0,
            "output_before": 0.0,
            "output_after": 0.0,
        },
    }


def test_correlate_reset_effect_event_accepts_exact_match():
    result = runtime.correlate_reset_effect_event(
        _reset_event(7, 3, 12),
        _effect(7, 3, 12),
    )

    assert result["ready"] is True
    assert result["status"] == "correlated"
    assert result["reset_event"]["call_index"] == 7
    assert result["effect_event"]["reset_event_count"] == 7


def test_correlate_reset_effect_event_rejects_count_mismatch():
    result = runtime.correlate_reset_effect_event(
        _reset_event(7, 3, 12),
        _effect(8, 3, 12),
    )

    assert result["ready"] is False
    assert "reset-event-count-mismatch:7:8" in result["errors"]


def test_correlate_reset_effect_event_rejects_provider_mismatch():
    result = runtime.correlate_reset_effect_event(
        _reset_event(7, 3, 12, provider_id=0),
        _effect(7, 3, 12, provider_id=1),
    )

    assert result["ready"] is False
    assert "provider-id-mismatch" in result["errors"]


def test_correlate_reset_effect_event_rejects_frame_mismatch():
    result = runtime.correlate_reset_effect_event(
        _reset_event(7, 3, 12),
        _effect(7, 4, 12),
    )

    assert result["ready"] is False
    assert "frame-index-mismatch" in result["errors"]


def test_correlate_reset_effect_event_rejects_selector_mismatch():
    result = runtime.correlate_reset_effect_event(
        _reset_event(7, 3, 12),
        _effect(7, 3, 13),
    )

    assert result["ready"] is False
    assert "selector-mismatch" in result["errors"]


def test_correlate_reset_effect_stream_pairs_by_monotonic_count():
    result = runtime.correlate_reset_effect_stream(
        [
            _reset_event(1, 1, 4),
            _reset_event(2, 1, 5),
        ],
        [
            _effect(1, 1, 4),
            _effect(2, 1, 5),
        ],
    )

    assert result["ready"] is True
    assert result["correlated_count"] == 2
    assert result["errors"] == []


def test_correlate_reset_effect_stream_reports_missing_effect():
    result = runtime.correlate_reset_effect_stream(
        [
            _reset_event(1, 1, 4),
            _reset_event(2, 1, 5),
        ],
        [
            _effect(1, 1, 4),
        ],
    )

    assert result["ready"] is False
    assert "missing-reset-effect:2" in result["errors"]


def test_correlate_reset_effect_stream_reports_missing_reset():
    result = runtime.correlate_reset_effect_stream(
        [
            _reset_event(1, 1, 4),
        ],
        [
            _effect(1, 1, 4),
            _effect(2, 1, 5),
        ],
    )

    assert result["ready"] is False
    assert "missing-reset-event:2" in result["errors"]


def test_summary_reports_unmatched_count():
    result = runtime.summarize_reset_effect_correlation(
        {
            "reset_event_count": 5,
            "effect_event_count": 4,
            "correlated_count": 3,
            "ready": False,
            "correlations": [],
        }
    )

    assert result["unmatched_count"] == 3


def test_contract_has_expected_status():
    result = runtime.build_reset_effect_correlation_contract(
        [],
        [],
    )

    assert result["ready"] is True
    assert result["summary"]["correlated_count"] == 0
