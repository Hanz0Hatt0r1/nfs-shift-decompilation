from camera_global_factory_runtime import (
    instantiate_factory_entry,
    resolve_factory_entry,
    resolve_factory_name,
)


def test_factory_map_preserves_known_allocation_sizes():
    assert resolve_factory_entry("DAT_00c25f0c")["allocation_bytes"] == 0xBC0
    assert resolve_factory_entry("DAT_00c25fa8")["allocation_bytes"] == 0x460
    assert resolve_factory_entry("DAT_00c25fb8")["allocation_bytes"] == 0x150


def test_factory_map_preserves_constructor_links():
    assert resolve_factory_entry("DAT_00c25f0c")["constructor"] == "FUN_0081cba0"
    assert resolve_factory_entry("DAT_00c25e70")["constructor"] == "FUN_00813300"


def test_unknown_type_returns_null_boundary():
    result = resolve_factory_entry("unknown")
    assert result["status"] == "unsupported"
    assert result["object"] is None


def test_allocation_failure_is_reported_before_constructor():
    result = instantiate_factory_entry(
        "DAT_00c25fb8",
        allocation_succeeded=False,
        constructor_succeeded=True,
    )
    assert result["status"] == "allocation-failed"
    assert result["actions"][0]["bytes"] == 0x150


def test_source_dependent_factory_requires_source():
    result = instantiate_factory_entry(
        "DAT_00c25fb8",
        allocation_succeeded=True,
        constructor_succeeded=True,
        source_available=False,
    )
    assert result["status"] == "source-unavailable"


def test_factory_name_resolution_preserves_resolver_order():
    result = resolve_factory_name(
        global_name="TrackingCamera",
        resolved_type_symbol="DAT_00c25fb8",
    )
    assert [a["action"] for a in result["actions"]] == [
        "FUN_0080cc60",
        "thunk_FUN_00d8cf00",
        "FUN_00823990",
    ]
