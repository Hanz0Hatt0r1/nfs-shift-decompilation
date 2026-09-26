from camera_attachment_selection_runtime import (
    build_spline_endpoint_output,
    describe_attachment_name_table,
    describe_selected_camera_config_query,
    resolve_attachment_name_index,
    resolve_selected_camera_property,
)


def test_attachment_table_has_exact_fifteen_canonical_names():
    result = describe_attachment_name_table()
    assert len(result["canonical_names"]) == 15
    assert result["canonical_names"][0] == "BumperPos"
    assert result["canonical_names"][14] == "SocketForArJackPos"


def test_attachment_aliases_map_to_observed_indices():
    assert resolve_attachment_name_index("fuelIntakePos")["index"] == 12
    assert resolve_attachment_name_index("driverPos")["index"] == 2


def test_unknown_attachment_name_maps_to_fifteen():
    result = resolve_attachment_name_index("unknown")
    assert result["index"] == 0x0F
    assert result["status"] == "no-match"


def test_canonical_attachment_names_keep_their_table_indices():
    assert resolve_attachment_name_index("CockpitPos")["index"] == 2
    assert resolve_attachment_name_index("RearRightWheelPos")["index"] == 11


def test_selected_camera_query_keeps_manager_298_boundary():
    result = describe_selected_camera_config_query(
        object_or_none="camera",
        selected_index=4,
    )
    assert result["manager"] == "+0x298"
    assert result["actions"][0]["action"] == "FUN_00810430"
    assert result["actions"][1]["action"] == "FUN_00810410"


def test_selected_camera_property_uses_vtable_or_lazy_fallback():
    resolved = resolve_selected_camera_property(
        selected_object="camera",
        selected_index=3,
        vtable_result="property",
    )
    assert resolved["value"] == "property"
    assert resolved["actions"][1]["action"] == "selected_object.vtable +0x10"

    fallback = resolve_selected_camera_property(
        selected_object=None,
        selected_index=3,
        vtable_result=None,
    )
    assert fallback["value"] == "DAT_00c259e4"


def test_spline_endpoint_output_uses_param2_only_when_record_scalar_is_zero():
    zero = build_spline_endpoint_output(
        record_position=[1, 2, 3],
        spline_object_value=7,
        record_scalar_20=0.0,
        param2_fallback=9,
    )
    assert zero["words"] == [1.0, 2.0, 3.0, 0.0, 0.0, 7, 0.0, 0.0, 9]

    nonzero = build_spline_endpoint_output(
        record_position=[1, 2, 3],
        spline_object_value=7,
        record_scalar_20=5,
        param2_fallback=9,
    )
    assert nonzero["words"][-1] == 5


def test_endpoint_middle_slot_is_raw_spline_object_value():
    result = build_spline_endpoint_output(
        record_position=[1, 2, 3],
        spline_object_value=0x1234,
        record_scalar_20=0,
        param2_fallback=0,
    )
    assert result["words"][5] == 0x1234
