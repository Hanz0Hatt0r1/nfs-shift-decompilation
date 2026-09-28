import pytest

import specialized_provider_scalar_reset_effect_runtime as runtime


def test_expected_addresses_provider0_selector_zero():
    result = runtime._expected_addresses(0, 0)

    assert result["diagonal"] == 0x00C21738
    assert result["output"] == 0x00C23C68


def test_expected_addresses_provider1_selector_zero():
    result = runtime._expected_addresses(1, 0)

    assert result["diagonal"] == 0x00C1FE38
    assert result["output"] == 0x00C21588


def test_build_reset_effect_event_sets_exact_expected_values():
    result = runtime.build_reset_effect_event(
        provider_id=0,
        selector=2,
        frame_index=3,
        reset_event_count=7,
        provider_pointer=0x1234,
        provider_vtable=0x00B0FC5C,
        diagonal_before=0.25,
        diagonal_after=1.0,
        output_before=9.0,
        output_after=0.0,
    )

    assert result["addresses"]["diagonal"] == "0x00c21848"
    assert result["addresses"]["output"] == "0x00c23c78"
    assert result["expected"] == {
        "diagonal_after": 1.0,
        "output_after": 0.0,
    }


def test_validate_reset_effect_accepts_exact_post_state():
    event = runtime.build_reset_effect_event(
        provider_id=1,
        selector=5,
        frame_index=2,
        reset_event_count=10,
        provider_pointer=0x2000,
        provider_vtable=0x00B0FC8C,
        diagonal_before=-3.0,
        diagonal_after=1.0,
        output_before=4.0,
        output_after=0.0,
    )

    result = runtime.validate_reset_effect_event(event)

    assert result["ready"] is True
    assert result["errors"] == []


def test_validate_reset_effect_rejects_wrong_diagonal_after():
    event = runtime.build_reset_effect_event(
        provider_id=0,
        selector=1,
        frame_index=1,
        reset_event_count=1,
        provider_pointer=0x2000,
        provider_vtable=0x00B0FC5C,
        diagonal_before=0.0,
        diagonal_after=2.0,
        output_before=0.0,
        output_after=0.0,
    )

    result = runtime.validate_reset_effect_event(event)

    assert result["ready"] is False
    assert "diagonal-after-not-one" in result["errors"]


def test_validate_reset_effect_rejects_wrong_provider_vtable():
    event = runtime.build_reset_effect_event(
        provider_id=0,
        selector=1,
        frame_index=1,
        reset_event_count=1,
        provider_pointer=0x2000,
        provider_vtable=0xDEADBEEF,
        diagonal_before=0.0,
        diagonal_after=1.0,
        output_before=0.0,
        output_after=0.0,
    )

    result = runtime.validate_reset_effect_event(event)

    assert result["ready"] is False
    assert "provider-vtable-mismatch" in result["errors"]


def test_validate_reset_effect_batch_rejects_duplicate_counters():
    events = [
        runtime.build_reset_effect_event(
            provider_id=0,
            selector=0,
            frame_index=1,
            reset_event_count=1,
            provider_pointer=0x2000,
            provider_vtable=0x00B0FC5C,
            diagonal_before=0.0,
            diagonal_after=1.0,
            output_before=0.0,
            output_after=0.0,
        ),
        runtime.build_reset_effect_event(
            provider_id=0,
            selector=1,
            frame_index=1,
            reset_event_count=1,
            provider_pointer=0x2000,
            provider_vtable=0x00B0FC5C,
            diagonal_before=0.0,
            diagonal_after=1.0,
            output_before=0.0,
            output_after=0.0,
        ),
    ]

    result = runtime.validate_reset_effect_batch(events)

    assert result["ready"] is False
    assert "duplicate-reset-event-count" in result["errors"]


def test_summary_counts_valid_and_invalid_events():
    valid = runtime.build_reset_effect_event(
        provider_id=1,
        selector=0,
        frame_index=2,
        reset_event_count=3,
        provider_pointer=0x2000,
        provider_vtable=0x00B0FC8C,
        diagonal_before=0.0,
        diagonal_after=1.0,
        output_before=0.0,
        output_after=0.0,
    )
    invalid = dict(valid)
    invalid["values"] = dict(valid["values"])
    invalid["values"]["output_after"] = 1.0

    result = runtime.summarize_reset_effect_events(
        [valid, invalid],
    )

    assert result["event_count"] == 2
    assert result["valid_count"] == 1
    assert result["invalid_count"] == 1
