import specialized_provider_reset_evidence_manifest_runtime as runtime


def _event(call_index, frame, return_address, selector):
    return {
        "frame_index": frame,
        "call_index": call_index,
        "physics_system": 0x1000,
        "provider_pointer": 0,
        "scalar_count": 40,
        "selector": selector,
        "caller_return_address": return_address,
    }


def test_build_frame_manifest_groups_by_frame():
    events = [
        _event(1, 1, 0x007B4029, 4),
        _event(2, 1, 0x007B4034, 5),
        _event(3, 1, 0x007B403F, 6),
        _event(4, 2, 0x007B40CB, 10),
    ]

    result = runtime.build_frame_manifest(events)

    assert [frame["frame_index"] for frame in result] == [1, 2]
    assert result[0]["event_count"] == 3
    assert result[1]["event_count"] == 1
    assert result[0]["selectors"] == [4, 5, 6]
    assert result[1]["selectors"] == [10]


def test_build_frame_manifest_counts_provider_and_groups():
    events = [
        {
            **_event(1, 3, 0x007B4029, 4),
            "provider_pointer": 0x2000,
            "provider_vtable": 0x00B0FC5C,
            "provider_id": 0,
            "callsite": {
                "status": "attributed",
                "group": "JOINT/HINGE",
            },
        },
        {
            **_event(2, 3, 0x007B40CB, 9),
            "callsite": {
                "status": "attributed",
                "group": "BAR",
            },
        },
    ]

    result = runtime.build_frame_manifest(events)

    assert result[0]["providers"] == {
        "0": 1,
        "builtin": 1,
    }
    assert result[0]["group_counts"] == {
        "BAR": 1,
        "JOINT/HINGE": 1,
    }


def test_build_reset_evidence_manifest_is_ready_for_valid_events():
    events = [
        _event(1, 1, 0x007B4029, 4),
        _event(2, 1, 0x007B4034, 5),
        _event(3, 1, 0x007B403F, 6),
    ]

    result = runtime.build_reset_evidence_manifest(events)

    assert result["ready"] is True
    assert result["event_validation"]["ready"] is True
    assert result["sequence_validation"]["ready"] is True
    assert result["provider_solve_order"] == []


def test_build_reset_evidence_manifest_collects_solve_order_errors():
    events = [_event(1, 1, 0x007B4029, 4)]
    capture = {
        "provider_id": 0,
        "stage": "pre-solve-provider",
        "workspace": [0.0] * 1190,
        "output_vector": [0.0] * 40,
        "row_pointers": [],
        "frame_index": 1,
        "metadata": {
            "scalar_reset_event_count": 3,
            "scalar_reset_events_since_frame_entry": 1,
        },
    }

    result = runtime.build_reset_evidence_manifest(
        events,
        provider_captures=[capture],
    )

    assert result["ready"] is False
    assert any(
        error.startswith("solve-0:provider-solve-reset-counter-mismatch")
        for error in result["errors"]
    )


def test_build_reset_evidence_contract_includes_summary():
    events = [
        _event(1, 1, 0x007B4029, 4),
        _event(2, 1, 0x007B4034, 5),
        _event(3, 1, 0x007B403F, 6),
    ]

    result = runtime.build_reset_evidence_contract(events)

    assert result["summary"]["event_count"] == 3
    assert result["summary"]["frame_count"] == 1
    assert result["summary"]["group_event_counts"] == {
        "JOINT/HINGE": 3,
    }
    assert result["summary"]["ready"] is True
