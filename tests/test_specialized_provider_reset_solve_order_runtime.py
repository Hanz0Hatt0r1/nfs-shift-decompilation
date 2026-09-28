import specialized_provider_reset_solve_order_runtime as runtime


def _event(call_index, frame_index, selector):
    return {
        "call_index": call_index,
        "frame_index": frame_index,
        "physics_system": 0x1000,
        "provider_pointer": 0,
        "scalar_count": 40,
        "selector": selector,
        "caller_return_address": 0x007B4029,
    }


def _capture(frame_index, total_count, frame_count):
    return {
        "provider_id": 0,
        "stage": "pre-solve-provider",
        "workspace": [0.0] * 1190,
        "output_vector": [0.0] * 40,
        "row_pointers": [],
        "frame_index": frame_index,
        "metadata": {
            "scalar_reset_event_count": total_count,
            "scalar_reset_events_since_frame_entry": frame_count,
        },
    }


def test_provider_solve_order_matches_reset_counter():
    events = [
        _event(1, 1, 4),
        _event(2, 1, 5),
        _event(3, 2, 9),
    ]
    capture = _capture(2, 3, 1)

    result = runtime.compare_provider_solve_order(capture, events)

    assert result["ready"] is True
    assert result["reset_event_count_at_solve"] == 3
    assert result["reset_events_same_frame"] == 1
    assert result["max_prior_reset_call_index"] == 3


def test_provider_solve_order_detects_global_counter_mismatch():
    events = [
        _event(1, 1, 4),
        _event(2, 2, 5),
    ]
    capture = _capture(2, 7, 1)

    result = runtime.compare_provider_solve_order(capture, events)

    assert result["ready"] is False
    assert any(
        error.startswith("provider-solve-reset-counter-mismatch")
        for error in result["errors"]
    )


def test_provider_solve_order_detects_frame_counter_mismatch():
    events = [
        _event(1, 1, 4),
        _event(2, 1, 5),
    ]
    capture = _capture(1, 2, 3)

    result = runtime.compare_provider_solve_order(capture, events)

    assert result["ready"] is False
    assert any(
        error.startswith("provider-solve-frame-reset-count-mismatch")
        for error in result["errors"]
    )


def test_provider_solve_order_blocks_missing_metadata():
    capture = {
        "provider_id": 0,
        "stage": "pre-solve-provider",
        "workspace": [0.0] * 1190,
        "output_vector": [0.0] * 40,
        "row_pointers": [],
        "frame_index": 1,
        "metadata": {},
    }

    result = runtime.compare_provider_solve_order(capture, [])

    assert result["ready"] is False
    assert "scalar-reset-event-count-missing" in result["errors"]
    assert "scalar-reset-frame-count-missing" in result["errors"]


def test_pre_post_order_requires_stable_counter():
    events = [
        _event(1, 1, 4),
    ]
    pre = _capture(1, 1, 1)
    post = _capture(1, 2, 1)

    result = runtime.compare_provider_pre_post_order(
        pre,
        post,
        events,
    )

    assert result["ready"] is False
    assert "reset-counter-changed-after-solve" in result["errors"]


def test_summarize_provider_solve_order():
    result = runtime.summarize_provider_solve_order(
        {
            "provider_id": 1,
            "frame_index": 4,
            "reset_event_count_at_solve": 18,
            "reset_events_same_frame": 6,
            "reset_events_same_provider_frame": 6,
            "provider_stage": "pre-solve-provider",
            "ready": True,
        }
    )

    assert result == {
        "provider_id": 1,
        "frame_index": 4,
        "reset_event_count_at_solve": 18,
        "reset_events_same_frame": 6,
        "reset_events_same_provider_frame": 6,
        "provider_stage": "pre-solve-provider",
        "ready": True,
    }
