from camera_view_base_state_runtime import (
    camera_view_base_property_registration,
    copy_camera_view_base_state,
    copy_embedded_camera_state,
    describe_refcounted_base_constructor,
    reset_camera_view_base_state,
)


def test_base_reset_uses_exact_vtable_and_reset_helper():
    result = reset_camera_view_base_state()
    assert result["actions"][0]["value"] == "PTR_FUN_00b161f0"
    assert result["actions"][1]["action"] == "FUN_006383f0"


def test_base_constructor_keeps_projection_raw_bits():
    result = describe_refcounted_base_constructor()
    assert result["writes"]["+0x34"] == 0x3F490FDB
    assert result["writes"]["+0x38"] == 0x3FAAAAAB
    assert result["writes"]["+0x3c"] == 0x3DCCCCCD
    assert result["writes"]["+0x40"] == 0x443B8000


def test_base_copy_has_exactly_thirteen_dwords():
    source = {offset: offset for offset in range(0, 0x34, 4)}
    result = copy_camera_view_base_state(source)
    assert result["copy_count"] == 13
    assert result["offsets"][0] == "+0x00"
    assert result["offsets"][-1] == "+0x30"


def test_embedded_copy_points_to_source_plus_10():
    result = copy_embedded_camera_state(source_base="camera")
    assert result["destination"] == "this + 0x10"
    assert result["source"] == "camera+0x10"


def test_registration_keeps_exact_offsets_and_type_ids():
    result = camera_view_base_property_registration()
    props = {row["name"]: row for row in result["properties"]}
    assert props["Position"]["offset"] == 0x10
    assert props["Orientation"]["offset"] == 0x1c
    assert props["Velocity"]["offset"] == 0x28
    assert props["FOV"]["offset"] == 0x34
    assert props["FOV"]["type_id"] == 10
    assert props["FarZ"]["offset"] == 0x40
