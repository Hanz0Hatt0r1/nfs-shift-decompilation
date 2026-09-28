import specialized_provider_scalar_reset_callsite_runtime as runtime


def test_callsite_table_has_six_direct_calls():
    assert len(runtime.CALLS) == 6
    assert len(runtime.BY_RETURN_ADDRESS) == 6


def test_callsite_group_and_ordinal_mapping():
    expected = {
        0x007B4029: ("JOINT/HINGE", 0, 3),
        0x007B4034: ("JOINT/HINGE", 1, 3),
        0x007B403F: ("JOINT/HINGE", 2, 3),
        0x007B407E: ("SECONDARY", 0, 2),
        0x007B4089: ("SECONDARY", 1, 2),
        0x007B40CB: ("BAR", 0, 1),
    }

    for address, (group, ordinal, width) in expected.items():
        result = runtime.get_callsite_by_return_address(address)
        assert result is not None
        assert result["group"] == group
        assert result["ordinal"] == ordinal
        assert result["group_width"] == width


def test_attribute_reset_event_uses_caller_return_address():
    result = runtime.attribute_reset_event(
        {
            "caller_return_address": 0x007B407E,
            "selector": 12,
        }
    )

    assert result["ready"] is True
    assert result["status"] == "attributed"
    assert result["group"] == "SECONDARY"
    assert result["ordinal"] == 0
    assert result["selector"] == 12


def test_attribute_reset_event_fails_closed_without_return_address():
    result = runtime.attribute_reset_event(
        {
            "selector": 5,
        }
    )

    assert result["ready"] is False
    assert result["status"] == "unattributed"
    assert result["reason"] == "caller-return-address-missing"


def test_attribute_reset_event_fails_closed_for_unknown_return_address():
    result = runtime.attribute_reset_event(
        {
            "caller_return_address": 0x12345678,
            "selector": 5,
        }
    )

    assert result["ready"] is False
    assert result["status"] == "unattributed"
    assert result["reason"] == "unknown-caller-return-address"


def test_attribute_reset_events_preserves_input_order():
    result = runtime.attribute_reset_events(
        [
            {
                "caller_return_address": 0x007B4029,
                "selector": 4,
            },
            {
                "caller_return_address": 0x007B40CB,
                "selector": 7,
            },
        ]
    )

    assert [item["group"] for item in result] == [
        "JOINT/HINGE",
        "BAR",
    ]


def test_summary_counts_attributed_and_unattributed():
    result = runtime.summarize_reset_callsite_attribution(
        [
            {"status": "attributed", "group": "JOINT/HINGE"},
            {"status": "attributed", "group": "JOINT/HINGE"},
            {"status": "attributed", "group": "BAR"},
            {"status": "unattributed"},
        ]
    )

    assert result["event_count"] == 4
    assert result["attributed_count"] == 3
    assert result["unattributed_count"] == 1
    assert result["group_counts"]["JOINT/HINGE"] == 2
    assert result["group_counts"]["BAR"] == 1


def test_validate_callsite_table():
    result = runtime.validate_reset_callsite_table()

    assert result["ready"] is True
    assert result["errors"] == []
