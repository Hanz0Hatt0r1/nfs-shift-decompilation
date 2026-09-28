import specialized_provider_selector_reset_footprint_runtime as runtime


def _event(call_index, frame, return_address, selector, provider_id):
    return {
        "frame_index": frame,
        "call_index": call_index,
        "physics_system": 0x1000,
        "provider_pointer": 0x2000 if provider_id == 0 else 0,
        "provider_vtable": 0x00B0FC5C if provider_id == 0 else None,
        "provider_id": provider_id,
        "scalar_count": 40 if provider_id == 0 else 34,
        "selector": selector,
        "caller_return_address": return_address,
    }

def test_expand_runtime_footprint_filters_to_provider_id():
    original = runtime.extract_selector_reset_footprint
    try:
        runtime.extract_selector_reset_footprint = lambda source, provider_id: {
            "provider_id": provider_id,
            "scalar_count": 40,
            "ready": True,
            "errors": [],
            "selectors": [
                {
                    "selector": selector,
                    "touched_addresses": [
                        hex(0x00C21738 + selector * 8),
                    ],
                    "touched_count": 1,
                }
                for selector in range(40)
            ],
        }

        events = [
            _event(1, 1, 0x007B4029, 1, 0),
            _event(2, 1, 0x007B4034, 2, 0),
            _event(3, 1, 0x007B403F, 3, 0),
            _event(4, 1, 0x007B40CB, 20, 1),
        ]

        result = runtime.expand_runtime_reset_footprint(
            "ignored",
            events,
            provider_id=0,
        )

        assert result["runtime_event_input_count"] == 4
        assert result["runtime_event_provider_filtered_count"] == 3
        assert result["frames"][0]["runtime_selector_count"] == 3
        assert result["frames"][0]["selectors"] == [1, 2, 3]
    finally:
        runtime.extract_selector_reset_footprint = original


def test_summarize_selector_reset_footprint():
    result = runtime.summarize_selector_reset_footprint(
        {
            "provider_id": 0,
            "scalar_count": 40,
            "static_selector_footprint": {
                "selectors": [
                    {"selector": 0, "touched_count": 2},
                    {"selector": 1, "touched_count": 3},
                ]
            },
            "frames": [
                {"runtime_selector_count": 5, "unknown_selector_count": 0},
                {"runtime_selector_count": 2, "unknown_selector_count": 1},
            ],
            "ready": True,
        }
    )

    assert result["selector_count"] == 2
    assert result["total_selector_touched_addresses"] == 5
    assert result["runtime_selector_count"] == 7
    assert result["unknown_runtime_selector_count"] == 1
