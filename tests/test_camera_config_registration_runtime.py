from camera_config_registration_runtime import (
    camera_config_manager_registration,
    describe_camera_config_defaults_reference,
    describe_default_camera_data_load,
    describe_default_camera_data_save,
)


def test_registration_matches_three_limit_and_three_config_properties():
    result = camera_config_manager_registration()
    props = {p["name"]: p for p in result["properties"]}
    assert props["FreeLookYawLimits"] == {
        "name": "FreeLookYawLimits", "type_id": 0x0F, "offset": 0x2B8, "flags": 2
    }
    assert props["Camera configs"]["offset"] == 0x10
    assert props["DefaultStaticCamData"]["offset"] == 0x78
    assert props["DefaultTrackingCamData"]["offset"] == 0x168


def test_registration_keeps_save_load_callbacks_exact():
    result = camera_config_manager_registration()
    assert result["callbacks"]["Camera configs"] == {
        "save": "FUN_00810530", "load": "FUN_00810180"
    }
    assert result["callbacks"]["DefaultStaticCamData"]["load"] == "FUN_0080fa40"
    assert result["callbacks"]["DefaultTrackingCamData"]["save"] == "FUN_0080fb40"


def test_default_data_save_uses_50_byte_funcpropdata():
    static = describe_default_camera_data_save(
        data_offset=0x78,
        vtable_name="PTR_FUN_00b15d08",
    )
    tracking = describe_default_camera_data_save(
        data_offset=0x168,
        vtable_name="PTR_FUN_00b165e8",
    )
    assert static["actions"][0]["bytes"] == 0x50
    assert tracking["data_offset"] == 0x168


def test_default_data_load_stops_when_root_or_class_is_missing():
    missing = describe_default_camera_data_load(
        data_offset=0x78,
        root_present=False,
        class_resolved=True,
        property_apply_success=True,
        finalize_success=True,
    )
    assert missing["status"] == "root-missing"

    unresolved = describe_default_camera_data_load(
        data_offset=0x168,
        root_present=True,
        class_resolved=False,
        property_apply_success=True,
        finalize_success=True,
    )
    assert unresolved["status"] == "class-unresolved"


def test_default_data_load_reports_property_and_finalize_failures():
    failed_apply = describe_default_camera_data_load(
        data_offset=0x78,
        root_present=True,
        class_resolved=True,
        property_apply_success=False,
        finalize_success=True,
    )
    assert failed_apply["status"] == "property-apply-failed"

    failed_finalize = describe_default_camera_data_load(
        data_offset=0x168,
        root_present=True,
        class_resolved=True,
        property_apply_success=True,
        finalize_success=False,
    )
    assert failed_finalize["status"] == "finalize-failed"


def test_default_reference_helper_returns_exact_offsets():
    result = describe_camera_config_defaults_reference()
    assert [x["offset"] for x in result["references"]] == [0x78, 0x168]
