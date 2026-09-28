import specialized_provider_active_scalar_group_runtime as runtime


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


def test_reconstruct_joint_record_from_three_calls():
    result = runtime.reconstruct_frame_groups(
        [
            _event(1, 1, 0x007B4029, 10),
            _event(2, 1, 0x007B4034, 11),
            _event(3, 1, 0x007B403F, 12),
        ],
        frame_index=1,
    )

    assert result["ready"] is True
    assert result["active_record_count"] == 1
    assert result["groups"]["JOINT/HINGE"][0] == {
        "group": "JOINT/HINGE",
        "width": 3,
        "base_selector": 10,
        "selectors": [10, 11, 12],
    }


def test_reconstruct_two_joint_records():
    result = runtime.reconstruct_frame_groups(
        [
            _event(1, 1, 0x007B4029, 10),
            _event(2, 1, 0x007B4034, 11),
            _event(3, 1, 0x007B403F, 12),
            _event(4, 1, 0x007B4029, 20),
            _event(5, 1, 0x007B4034, 21),
            _event(6, 1, 0x007B403F, 22),
        ],
        frame_index=1,
    )

    assert result["ready"] is True
    assert [record["base_selector"] for record in result["groups"]["JOINT/HINGE"]] == [
        10,
        20,
    ]


def test_reconstruct_secondary_and_bar_groups():
    result = runtime.reconstruct_frame_groups(
        [
            _event(1, 1, 0x007B407E, 30),
            _event(2, 1, 0x007B4089, 31),
            _event(3, 1, 0x007B40CB, 40),
        ],
        frame_index=1,
    )

    assert result["ready"] is True
    assert result["groups"]["SECONDARY"][0]["selectors"] == [30, 31]
    assert result["groups"]["BAR"][0]["selectors"] == [40]


def test_missing_selector_call_rejects_record():
    result = runtime.reconstruct_frame_groups(
        [
            _event(1, 1, 0x007B4029, 10),
            _event(2, 1, 0x007B403F, 12),
        ],
        frame_index=1,
    )

    assert result["ready"] is False
    assert any(
        error.startswith("JOINT/HINGE-record-width-mismatch")
        or error.startswith("JOINT/HINGE-selector-contiguity")
        or error.startswith("JOINT/HINGE-ordinal-mismatch")
        for error in result["errors"]
    )


def test_reconstruct_active_scalar_groups_counts_frames():
    result = runtime.reconstruct_active_scalar_groups(
        [
            _event(1, 1, 0x007B4029, 10),
            _event(2, 1, 0x007B4034, 11),
            _event(3, 1, 0x007B403F, 12),
            _event(4, 2, 0x007B40CB, 20),
        ]
    )

    assert result["ready"] is True
    assert result["frame_count"] == 2
    assert result["frames"][0]["event_count"] == 3
    assert result["frames"][1]["event_count"] == 1


def test_summary_counts_scalar_events_and_records_by_group():
    result = runtime.summarize_active_scalar_groups(
        {
            "event_count": 9,
            "frame_count": 2,
            "frames": [
                {
                    "groups": {
                        "JOINT/HINGE": [
                            {"selectors": [1, 2, 3]},
                        ],
                        "BAR": [
                            {"selectors": [7]},
                            {"selectors": [9]},
                        ],
                    }
                },
                {
                    "groups": {
                        "SECONDARY": [
                            {"selectors": [10, 11]},
                        ],
                    }
                },
            ],
            "ready": True,
        }
    )

    assert result["scalar_events_by_group"] == {
        "JOINT/HINGE": 3,
        "SECONDARY": 2,
        "BAR": 2,
    }
    assert result["active_records_by_group"] == {
        "JOINT/HINGE": 1,
        "SECONDARY": 1,
        "BAR": 2,
    }


def test_contract_exposes_summary():
    result = runtime.build_active_scalar_group_contract(
        [
            _event(1, 1, 0x007B40CB, 5),
        ]
    )

    assert result["summary"]["event_count"] == 1
    assert result["summary"]["active_records_by_group"]["BAR"] == 1
