import joint_desc_schema_runtime as runtime


def test_joint_desc_offsets_and_registration_ids():
    c = runtime.build_joint_desc_schema()
    fields = {f["name"]: f for f in c["fields"]}
    assert fields["object1"]["offset"] == 0x14
    assert fields["object2"]["offset"] == 0x18
    assert fields["anchor1"]["offset"] == 0x1C
    assert fields["anchor2"]["offset"] == 0x28
    assert fields["axis1"]["offset"] == 0x34
    assert fields["axis2"]["offset"] == 0x40
    assert fields["normal1"]["offset"] == 0x4C
    assert fields["normal2"]["offset"] == 0x58
    assert fields["breakable"]["offset"] == 0x64
    assert fields["limits_enabled"]["offset"] == 0x68
    assert fields["limit_min"]["offset"] == 0x6C
    assert fields["limit_max"]["offset"] == 0x70
    assert fields["break_limit"]["offset"] == 0x74
    assert fields["axis1"]["type_id"] == 0x10
    assert fields["breakable"]["type_id"] == 2


def test_joint_limit_desc_schema():
    c = runtime.build_joint_limit_desc_schema()
    fields = {f["name"]: f for f in c["fields"]}
    assert fields["type"]["offset"] == 0x10
    assert fields["value"]["offset"] == 0x14
    assert fields["restitution"]["offset"] == 0x18
    assert fields["spring"]["offset"] == 0x1C
    assert fields["damping"]["offset"] == 0x20
    assert fields["spring"]["type_id"] == 10


def test_joint_desc_explicit_constructor_defaults():
    d = runtime.build_joint_desc_defaults()["defaults"]
    assert d["type"]["raw_u32"] == 1
    assert d["breakable"]["raw_u32"] == 0
    assert d["limits_enabled"]["raw_u32"] == 0
    assert d["axis1"]["raw_u32"] == 0x3F800000
    assert d["normal2"]["value"] == 1.0


def test_schema_validation():
    c = runtime.build_joint_desc_schema()
    result = runtime.validate_joint_desc_schema(c)
    assert result["ready"]
    assert result["errors"] == []
