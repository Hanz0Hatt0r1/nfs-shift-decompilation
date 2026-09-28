import specialized_provider_scalar_reset_sequence_runtime as runtime


def _event(return_address, selector, frame=1):
    return {
        "frame_index": frame,
        "call_index": selector,
        "physics_system": 0x1000,
        "provider_pointer": 0,
        "scalar_count": 40,
        "selector": selector,
        "caller_return_address": return_address,
    }


def test_joint_group_ordinals_must_follow_zero_one_two():
    result = runtime.validate_group_event_sequence(
        [
            _event(0x007B4029, 10),
            _event(0x007B4034, 11),
            _event(0x007B403F, 12),
        ]
    )

    assert result["ready"] is True
    assert result["frames"][0]["groups"][0]["ordinals"] == [0, 1, 2]


def test_repeated_joint_records_reset_ordinal_sequence():
    result = runtime.validate_group_event_sequence(
        [
            _event(0x007B4029, 10),
            _event(0x007B4034, 11),
            _event(0x007B403F, 12),
            _event(0x007B4029, 20),
            _event(0x007B4034, 21),
            _event(0x007B403F, 22),
        ]
    )

    assert result["ready"] is True
    assert result["frames"][0]["groups"][0]["event_count"] == 6


def test_missing_middle_callsite_is_rejected():
    result = runtime.validate_group_event_sequence(
        [
            _event(0x007B4029, 10),
            _event(0x007B403F, 12),
        ]
    )

    assert result["ready"] is False
    assert any(
        error.startswith("group-JOINT/HINGE-ordinal-sequence")
        for error in result["frames"][0]["errors"]
    )


def test_group_order_must_not_regress():
    result = runtime.validate_group_event_sequence(
        [
            _event(0x007B407E, 10),
            _event(0x007B4029, 20),
        ]
    )

    assert result["ready"] is False
    assert "group-order-regression" in result["frames"][0]["errors"]


def test_secondary_group_uses_zero_one():
    result = runtime.validate_group_event_sequence(
        [
            _event(0x007B407E, 7),
            _event(0x007B4089, 8),
        ]
    )

    assert result["ready"] is True
    secondary = result["frames"][0]["groups"][0]
    assert secondary["group"] == "SECONDARY"
    assert secondary["ordinals"] == [0, 1]


def test_bar_group_uses_single_zero_ordinal():
    result = runtime.validate_group_event_sequence(
        [
            _event(0x007B40CB, 33),
            _event(0x007B40CB, 34),
        ]
    )

    assert result["ready"] is True
    assert result["frames"][0]["groups"][0]["ordinals"] == [0, 0]


def test_multiple_groups_keep_source_order():
    result = runtime.validate_group_event_sequence(
        [
            _event(0x007B4029, 1),
            _event(0x007B4034, 2),
            _event(0x007B403F, 3),
            _event(0x007B407E, 4),
            _event(0x007B4089, 5),
            _event(0x007B40CB, 6),
        ]
    )

    assert result["ready"] is True
    assert [
        group["group"]
        for group in result["frames"][0]["groups"]
    ] == ["JOINT/HINGE", "SECONDARY", "BAR"]


def test_summary_reports_frame_errors():
    result = runtime.summarize_group_event_sequence(
        {
            "event_count": 8,
            "attributed_count": 6,
            "frames": [
                {"event_count": 4, "errors": ["x"], "groups": []},
                {"event_count": 4, "errors": [], "groups": []},
            ],
            "ready": False,
        }
    )

    assert result["event_count"] == 8
    assert result["attributed_count"] == 6
    assert result["frame_count"] == 2
    assert result["frame_errors"] == 1
    assert result["ready"] is False


def test_callsite_attribute_can_be_supplied_inline():
    result = runtime.validate_group_event_sequence(
        [
            {
                **_event(0x007B40CB, 9),
                "callsite": {
                    "status": "attributed",
                    "group": "BAR",
                    "group_width": 1,
                    "ordinal": 0,
                    "return_address": "0x007b40cb",
                },
            }
        ]
    )

    assert result["ready"] is True
