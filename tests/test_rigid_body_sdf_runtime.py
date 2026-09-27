import rigid_body_sdf_runtime as sdf


def test_body_and_constraint_fields_match_runtime_loader():
    report = sdf.parse_sdf("""
[BODY]
name=body mass=(0.0) inertia=(1.0,2.0,3.0)
pos=(0.0,0.0,0.0) ori=(0.0,0.0,0.0)
[JOINT&HINGE]
posbody=fl_wheel negbody=fl_spindle
pos=fl_wheel axis=(-1.0,0.0,0.0)
""")
    assert report["ready"] is True
    assert report["topology"]["body_count"] == 1
    assert report["topology"]["joint_count"] == 1
    assert report["topology"]["hinge_count"] == 1
    assert report["topology"]["joint_hinge_count"] == 1
    body = sdf.records_by_type(report, "BODY")[0]
    assert body["entries"][0]["name"] == "name"
    assert body["entries"][1]["value"] == 0.0
    joint = sdf.records_by_type(report, "JOINT&HINGE")[0]
    pos = next(x for x in joint["entries"] if x["name"] == "pos")
    assert pos["value"] == "fl_wheel"
    assert pos["loader_shape"] == "tuple3-or-string"


def test_sdf_accepts_numeric_pos_and_preserves_unknown_keys():
    report = sdf.parse_sdf("""
[BAR]
name=fl_fore_lower posbody=body negbody=fl_spindle
pos=(0.1,0.2,0.3) neg=(0.4,0.5,0.6) axis=(1,0,0)
extra=keep
""")
    bar = sdf.records_by_type(report, "BAR")[0]
    assert next(x for x in bar["entries"] if x["name"] == "pos")["value"] == [0.1, 0.2, 0.3]
    extra = next(x for x in bar["entries"] if x["name"] == "extra")
    assert extra["recognized_by_loader"] is False
    assert extra["value"] == "keep"


def test_sdf_strict_mode_rejects_malformed_line():
    import pytest
    with pytest.raises(ValueError, match="unparsed"):
        sdf.parse_sdf("[BODY]\nbad line\n", strict=True)


def test_sdf_body_reference_graph_resolves_posbody_and_negbody():
    import rigid_body_sdf_runtime as sdf

    report = sdf.parse_sdf("""
[BODY]
name=body
[BODY]
name=wheel
[JOINT&HINGE]
posbody=wheel negbody=body pos=wheel axis=(1,0,0)
[BAR]
name=link posbody=body negbody=wheel pos=(0,0,0) neg=(1,0,0)
""")
    graph = sdf.resolve_sdf_body_references(report)
    assert graph["ready"] is True
    assert graph["edge_count"] == 2
    assert graph["body_names"] == ["BODY", "WHEEL"]
    assert graph["adjacency"]["body"] == [0, 1]
    assert graph["adjacency"]["wheel"] == [0, 1]


def test_sdf_body_reference_graph_blocks_missing_body():
    import rigid_body_sdf_runtime as sdf

    report = sdf.parse_sdf("""
[BODY]
name=body
[BAR]
name=broken posbody=missing negbody=body pos=(0,0,0) neg=(1,0,0)
""")
    graph = sdf.resolve_sdf_body_references(report)
    assert graph["ready"] is False
    assert "record:1:BAR:posbody:MISSING" in graph["unresolved"]


def test_sdf_runtime_topology_compiler_preserves_constructor_flags_and_strides():
    import rigid_body_sdf_runtime as sdf

    report = sdf.parse_sdf("""
[BODY]
name=body
[BODY]
name=wheel
[JOINT]
name=j posbody=body negbody=wheel axis=(1,0,0) neg=(0,0,0) pos=(0,1,0)
[HINGE]
name=h posbody=body negbody=wheel axis=(0,1,0) neg=(0,0,0) pos=anchor
[BAR]
name=b posbody=body negbody=wheel axis=(0,0,1) neg=(0,0,0) pos=(0,0,1)
[JOINT&HINGE]
name=jh posbody=wheel negbody=body axis=(1,1,0) neg=(0,0,0) pos=(0,0,1)
""")
    compiled = sdf.compile_sdf_runtime_topology(report)
    assert compiled["ready"] is True
    assert compiled["body_count"] == 2
    assert compiled["constraint_count"] == 4
    assert compiled["constraints"][0]["flag_word"] == 1
    assert compiled["constraints"][1]["flag_word"] == 2
    assert compiled["constraints"][2]["flag_word"] == 4
    assert compiled["constraints"][3]["flag_word"] == 3
    assert compiled["constraints"][2]["runtime_stride"] == 0xB8
    assert compiled["constraints"][0]["runtime_stride"] == 0xA0
    assert compiled["constraints"][1]["vectors"]["pos_body_anchor_name"] == "anchor"


def test_sdf_runtime_topology_blocks_unresolved_constraint_body():
    import rigid_body_sdf_runtime as sdf

    report = sdf.parse_sdf("""
[BODY]
name=body
[BAR]
name=broken posbody=missing negbody=body pos=(0,0,0) neg=(1,0,0) axis=(1,0,0)
""")
    compiled = sdf.compile_sdf_runtime_topology(report)
    assert compiled["ready"] is False
    assert any("posbody:missing" in value for value in compiled["unresolved"])


def test_sdf_pre_physx_build_exposes_source_allocation_counts():
    import rigid_body_sdf_runtime as sdf

    report = sdf.parse_sdf("""
[BODY]
name=body
[BODY]
name=wheel
[JOINT]
name=j posbody=body negbody=wheel axis=(1,0,0) neg=(0,0,0) pos=(0,1,0)
[HINGE]
name=h posbody=body negbody=wheel axis=(0,1,0) neg=(0,0,0) pos=(0,1,0)
[BAR]
name=b posbody=body negbody=wheel axis=(0,0,1) neg=(0,0,0) pos=(0,0,1)
""")
    result = sdf.describe_sdf_pre_physx_build(report)
    assert result["ready"] is True
    assert result["allocations"]["body_index_matrix_elements"] == 4
    assert result["allocations"]["body_index_matrix_bytes"] == 32
    assert result["allocations"]["body_index_vector_bytes"] == 8
    assert result["allocations"]["per_joint_resolved_samples"] == 2
    assert result["allocations"]["per_hinge_resolved_samples"] == 2
    assert result["allocations"]["per_bar_resolved_samples"] == 2
    assert [stage["function"] for stage in result["stages"][:3]] == [
        "FUN_007ba4e0", "FUN_007b1b60", "FUN_007b2010"
    ]


def test_sdf_duplicate_body_names_are_blocked():
    import rigid_body_sdf_runtime as sdf

    report = sdf.parse_sdf("""
[BODY]
name=body
[BODY]
name=body
""")
    graph = sdf.resolve_sdf_body_references(report)
    assert graph["ready"] is False
    assert graph["duplicate_body_names"] == ["BODY"]
    assert "duplicate-body-name:body" in graph["unresolved"]


def test_sdf_body_lowering_preserves_proven_runtime_offsets():
    import rigid_body_sdf_runtime as sdf

    report = sdf.parse_sdf("""
[BODY]
name=body mass=1460 inertia=(1800,1920,450) pos=(0,0,0) ori=(0,0,0) vel=(0,0,0) rot=(0,0,0)
""")
    lowered = sdf.describe_sdf_body_runtime_lowering(report)
    assert lowered["ready"] is True
    row = lowered["rows"][0]
    assert row["normalized_name"] == "BODY"
    assert row["runtime_stride"] == 0x170
    assert row["lowering"]["name"]["runtime"] == "+0x100"
    assert row["lowering"]["mass"]["inverse"] == "+0x90"
    assert row["lowering"]["group_a"]["helper"] == "FUN_007bbb10"
    assert row["lowering"]["group_b"]["helper"] == "FUN_007bbb60"



def test_sdf_constraint_runtime_lowering_exposes_source_and_runtime_storage():
    report = sdf.parse_sdf("""
[BODY]
name=body
[BODY]
name=wheel
[JOINT&HINGE]
name=steer posbody=wheel negbody=body
axis=(1,0,0) neg=(0,0,0) pos=(0,1,0)
""")
    lowered = sdf.describe_sdf_constraint_runtime_lowering(report)
    assert lowered["ready"] is True
    assert lowered["source_record_count"] == 1
    assert lowered["record_count"] == 2
    row = lowered["rows"][0]
    assert row["runtime_section"] == "JOINT"
    assert row["materialization"] == "JOINT"
    assert row["flag_word"] == 1
    assert row["body_pointer_slots"] == {"posbody": "+0x78", "negbody": "+0x80"}
    assert row["record_index_field"] == "+0x70"
    assert row["body_counter_offset"] == "+0x98"
    assert row["copy_helper"] == "FUN_007b2ae0"
    assert row["sampling"]["helper"] == "FUN_007ba8b0"
    assert row["sampling"]["sample_stride"] == 0x40
    assert row["postload"]["helper"] == "FUN_007b2da0"
    assert row["section_storage"]["source_descriptor_offsets"] == ["+0x28", "+0x30", "+0x38"]
    assert row["section_storage"]["source_value_fields"] == ["pos"]
    assert row["source_descriptor"]["string_fields"] == {
        "constraint_name": "+0x14",
        "posbody": "+0x18",
        "negbody": "+0x1c",
        "copy_body_name": "+0x20",
    }
    hinge = lowered["rows"][1]
    assert hinge["runtime_section"] == "HINGE"
    assert hinge["flag_word"] == 2
    assert hinge["body_counter_offset"] == "+0x9c"
    assert hinge["section_storage"]["source_descriptor_offsets"] == ["+0x58", "+0x60", "+0x68"]
    assert hinge["section_storage"]["source_value_fields"] == ["axis"]


def test_sdf_constraint_runtime_lowering_blocks_missing_endpoint_names():
    report = sdf.parse_sdf("""
[BODY]
name=body
[BAR]
name=broken posbody=body
pos=(0,0,0) neg=(1,0,0)
""")
    lowered = sdf.describe_sdf_constraint_runtime_lowering(report)
    assert lowered["ready"] is False
    assert "record:1:BAR:missing-negbody" in lowered["unresolved"]
