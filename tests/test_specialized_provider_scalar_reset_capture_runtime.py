import specialized_provider_scalar_reset_capture_runtime as runtime


def test_normalize_provider_event_uses_exact_vtable_identity():
    result = runtime.normalize_scalar_reset_event(
        {
            "frame_index": 3,
            "call_index": 7,
            "physics_system": 0x1000,
            "provider_pointer": 0x2000,
            "provider_vtable": 0x00B0FC5C,
            "provider_id": 0,
            "scalar_count": 40,
            "selector": 17,
            "caller_return_address": 0x007B1234,
        }
    )

    assert result["backend"] == "provider"
    assert result["provider_id"] == 0
    assert result["provider_pointer"] == 0x2000
    assert result["provider_vtable"] == 0x00B0FC5C
    assert result["selector"] == 17
    assert result["caller_return_address"] == 0x007B1234


def test_normalize_builtin_event():
    result = runtime.normalize_scalar_reset_event(
        {
            "call_index": 1,
            "physics_system": 0x1000,
            "provider_pointer": 0,
            "scalar_count": 34,
            "selector": 5,
        }
    )

    assert result["backend"] == "builtin"
    assert result["provider_id"] is None
    assert result["provider_vtable"] is None
    assert result["provider_reset_vtable_offset"] is None


def test_unknown_nonzero_provider_is_not_accepted_as_known_provider():
    result = runtime.normalize_scalar_reset_event(
        {
            "call_index": 1,
            "physics_system": 0x1000,
            "provider_pointer": 0x2000,
            "provider_vtable": 0xDEADBEEF,
            "scalar_count": 40,
            "selector": 1,
        }
    )

    validation = runtime.validate_scalar_reset_event(
        {
            "call_index": 1,
            "physics_system": 0x1000,
            "provider_pointer": 0x2000,
            "provider_vtable": 0xDEADBEEF,
            "provider_id": None,
            "scalar_count": 40,
            "selector": 1,
        }
    )

    assert result["backend"] == "unknown"
    assert validation["ready"] is False
    assert "unknown-provider-vtable" in validation["errors"]


def test_selector_domain_is_enforced():
    result = runtime.validate_scalar_reset_event(
        {
            "call_index": 1,
            "physics_system": 0x1000,
            "provider_pointer": 0,
            "scalar_count": 40,
            "selector": 40,
        }
    )

    assert result["ready"] is False
    assert "selector-out-of-domain:selector=40:count=40" in result["errors"]


def test_batch_summary_counts_unknown_backend():
    result = runtime.summarize_scalar_reset_events(
        [
            {
                "call_index": 0,
                "physics_system": 0x1000,
                "provider_pointer": 0,
                "scalar_count": 40,
                "selector": 0,
            },
            {
                "call_index": 1,
                "physics_system": 0x1000,
                "provider_pointer": 0x2000,
                "provider_vtable": 0x00B0FC5C,
                "provider_id": 0,
                "scalar_count": 40,
                "selector": 1,
            },
            {
                "call_index": 2,
                "physics_system": 0x1000,
                "provider_pointer": 0x3000,
                "provider_vtable": 0xDEADBEEF,
                "scalar_count": 40,
                "selector": 2,
            },
        ]
    )

    assert result["event_count"] == 3
    assert result["provider_event_count"] == 1
    assert result["builtin_event_count"] == 1
    assert result["unknown_event_count"] == 1


def test_batch_validation_rejects_duplicate_call_indices():
    result = runtime.validate_scalar_reset_events(
        [
            {
                "call_index": 0,
                "physics_system": 0x1000,
                "provider_pointer": 0,
                "scalar_count": 40,
                "selector": 0,
            },
            {
                "call_index": 0,
                "physics_system": 0x1000,
                "provider_pointer": 0,
                "scalar_count": 40,
                "selector": 1,
            },
        ]
    )

    assert result["ready"] is False
    assert "duplicate-call-index" in result["errors"]


def test_capture_contract_is_version_two():
    contract = runtime.build_scalar_reset_capture_contract()

    assert contract["format"].endswith("/2")
    assert "provider_pointer" in contract["event"]["required"]
    assert "caller_return_address" in contract["event"]["optional"]
