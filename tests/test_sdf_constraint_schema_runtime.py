import physics_constraint_construction_runtime as construction
import sdf_constraint_schema_runtime as runtime


def test_sdf_descriptor_exact_named_fields():
    schema = runtime.build_sdf_constraint_descriptor_schema()
    fields = {field["name"]: field for field in schema["fields"]}
    assert fields["label"] == {"name": "label", "label": "Label", "offset": 0x14, "type_id": 0}
    assert fields["pos_body"]["offset"] == 0x18
    assert fields["neg_body"]["offset"] == 0x1C
    assert fields["copy_body"]["offset"] == 0x20
    assert fields["pos_body"]["type_id"] == 0
    assert schema["registration_function"] == "FUN_007b42f0"


def test_sdf_descriptor_opaque_fields_preserve_source_globals():
    schema = runtime.build_sdf_constraint_descriptor_schema()
    fields = {field["offset"]: field for field in schema["fields"]}
    assert fields[0x28]["type_id"] == 0x13
    assert fields[0x28]["source_global"] == "DAT_00afc8b8"
    assert fields[0x40]["source_global"] == "DAT_00b0ce6c"
    assert fields[0x58]["source_global"] == "DAT_00b0ce64"


def test_sdf_descriptor_parser_aliases_do_not_guess_opaque_fields():
    schema = runtime.build_sdf_constraint_descriptor_schema()
    assert schema["parser_field_aliases"]["posbody"]["descriptor_offset"] == 0x18
    assert "pos" not in schema["parser_field_aliases"]


def test_sdf_descriptor_schema_validation():
    schema = runtime.build_sdf_constraint_descriptor_schema()
    result = runtime.validate_sdf_constraint_descriptor_schema(schema)
    assert result["ready"]
    assert result["errors"] == []


def test_bar_endpoint_counters_are_both_a0():
    spec = construction.CONSTRAINT_RUNTIME["BAR"]
    assert spec["body_reference_counters"] == {
        "positive": "+0xa0",
        "negative": "+0xa0",
    }
