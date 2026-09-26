from config_manager_runtime import (
    ConfigEntry,
    clone_default_objects,
    describe_config_manager_registration,
    describe_config_manager_reset,
    deserialize_config_entries,
    find_config_index,
    indexed_config,
    load_config_manager,
    release_config_arrays,
    serialize_config_entries,
)


def test_indexed_config_returns_zero_outside_count():
    result = indexed_config(["a"], 1)
    assert result["status"] == "out-of-range"
    assert result["value"] == 0


def test_indexed_config_returns_existing_entry():
    result = indexed_config(["a", "b"], 1)
    assert result["status"] == "found"
    assert result["value"] == "b"


def test_find_config_index_uses_property_values():
    entries = [
        ConfigEntry("A", "one"),
        ConfigEntry("B", "two"),
    ]
    result = find_config_index(
        entries,
        query="two",
        object_property_values=["one", "two"],
    )
    assert result["index"] == 1


def test_find_config_index_returns_minus_one_when_missing():
    entries = [ConfigEntry("A", "one")]
    result = find_config_index(
        entries,
        query="missing",
        object_property_values=["one"],
    )
    assert result["index"] == -1


def test_release_config_arrays_walks_both_arrays():
    result = release_config_arrays(["a", "b"], ["s", "t"])
    assert result["actions"][0]["count"] == 2
    assert result["actions"][2]["count"] == 2


def test_top_level_load_constructs_both_default_camera_data_objects():
    result = load_config_manager(
        xml_object="xml",
        manager_registration_succeeded=True,
        config_entries_result=[ConfigEntry("A", "a")],
        default_static_object="static",
        default_tracking_object="tracking",
    )
    assert result["status"] == "loaded"
    names = [a["helper"] for a in result["actions"] if "helper" in a]
    assert "FUN_00813180" in names
    assert "FUN_0081f8c0" in names


def test_entry_deserializer_reads_class_and_secondary_attributes():
    result = deserialize_config_entries(
        xml_entries=[{"class": "A", "secondary": "id"}],
        existing_entries=[],
        existing_properties=[],
    )
    assert result["status"] == "loaded"
    assert result["actions"][0]["class"] == "A"


def test_entry_deserializer_can_fail_before_append():
    result = deserialize_config_entries(
        xml_entries=[{"class": "A", "secondary": "id"}],
        existing_entries=[],
        existing_properties=[],
        factory_succeeded=False,
    )
    assert result["status"] == "factory-failed"


def test_serializer_keeps_entry_order_and_names():
    result = serialize_config_entries([
        ConfigEntry("A", "one"),
        ConfigEntry("B", "two"),
    ])
    assert result["actions"][2]["class_name"] == "A"
    assert result["actions"][3]["index"] == 0


def test_serializer_failure_is_explicit():
    result = serialize_config_entries(
        [ConfigEntry("A", "one")],
        class_conversion_succeeded=False,
    )
    assert result["status"] == "failed"


def test_clone_default_objects_preserves_each_source_record():
    result = clone_default_objects([
        {"class": "A"},
        {"class": "B"},
    ])
    assert result["clones"][1]["class"] == "B"


def test_config_manager_reset_has_exact_order():
    result = describe_config_manager_reset()
    assert [a["action"] for a in result["actions"]] == [
        "write vtable",
        "FUN_00810490",
        "FUN_0081ea60",
        "FUN_00813500",
        "FUN_004f0050",
        "FUN_004f0050",
        "FUN_006383f0",
    ]


def test_config_manager_registration_matches_all_six_properties():
    result = describe_config_manager_registration()
    assert len(result["properties"]) == 6
    props = {p["name"]: p for p in result["properties"]}
    assert props["FreeLookYawLimits"]["offset"] == 0x2B8
    assert props["FreeLookPitchLimits"]["offset"] == 0x2C0
    assert props["RotateChaseCamPitchLimits"]["offset"] == 0x2C8
    assert result["container_callbacks"]["Camera configs"]["load"] == "FUN_00810180"
