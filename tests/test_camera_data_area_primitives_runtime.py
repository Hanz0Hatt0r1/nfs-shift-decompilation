from camera_data_area_primitives_runtime import (
    describe_area_base_constructor,
    describe_box_constructor,
    describe_box_distance_helper,
    describe_camera_data_copy,
    describe_camera_data_external_update,
    describe_sphere_constructor,
    sphere_distance_contract,
    sphere_property_registration,
)


def test_camera_data_copy_calls_base_then_extended_copy():
    result = describe_camera_data_copy(destination="dst", source="src")
    assert result["actions"][0]["action"] == "FUN_0081af70"
    assert result["actions"][1]["action"] == "FUN_0081d180"
    assert result["actions"][1]["destination"] == "dst+0x80"


def test_camera_data_external_update_targets_plus_10():
    result = describe_camera_data_external_update(
        destination="camera",
        update_source="opaque",
    )
    assert result["actions"][0]["destination"] == "camera+0x10"


def test_area_base_constructor_keeps_exact_vtable_sequence():
    result = describe_area_base_constructor()
    assert result["actions"][-1]["value"] == "PTR_FUN_00b164b0"


def test_sphere_constructor_zeroes_center_radius_storage():
    result = describe_sphere_constructor()
    assert result["writes"] == {
        "+0x10": 0,
        "+0x14": 0,
        "+0x18": 0,
        "+0x1c": 0,
    }


def test_sphere_properties_use_exact_offsets():
    result = sphere_property_registration()
    props = {x["name"]: x for x in result["properties"]}
    assert props["Centre"]["offset"] == 0x10
    assert props["Centre"]["type_id"] == 0x10
    assert props["Radius"]["offset"] == 0x1c
    assert props["Radius"]["type_id"] == 1


def test_sphere_distance_subtracts_radius_from_opaque_sqrt_result():
    result = sphere_distance_contract(sqrt_result=10, radius=3)
    assert result["result"] == 7


def test_box_registration_uses_xform_and_dimensions_offsets():
    result = describe_box_constructor()
    props = {x["name"]: x for x in result["properties"]}
    assert props["XForm"]["offset"] == 0x10
    assert props["XForm"]["type_id"] == 0x1D
    assert props["Dimensions"]["offset"] == 0x50


def test_box_distance_keeps_helper_semantics_opaque():
    result = describe_box_distance_helper(
        transform_words=[1, 2, 3],
        query="query",
    )
    assert result["actions"][1]["action"] == "FUN_00702520"
