import math

from ai_database_runtime import (
    CLASS_NAME,
    DEFAULT_INITIALIZER,
    META_RECORD_COUNT_OFFSET,
    META_RECORD_PTR_OFFSET,
    META_RECORD_STRIDE,
    META_REBUILD_FLAG_OFFSET,
    MINIMUM_OBSERVED_SPAN,
    REFLECTED_FIELDS,
    RTTI_DESCRIPTOR,
    SINGLETON_ADDRESS,
    SOURCE_RECORD_COUNT_OFFSET,
    SOURCE_RECORD_PTR_OFFSET,
    SOURCE_RECORD_STRIDE,
    VTABLE,
    constructor_default_writes,
    describe_ai_database_runtime,
    describe_meta_section_storage,
    reflected_constructor_defaults,
    reflected_field_index,
)


def test_ai_database_identity_is_frozen_to_retail_evidence():
    report = describe_ai_database_runtime()
    assert CLASS_NAME == "AIDatabase"
    assert RTTI_DESCRIPTOR == 0x00C10F58
    assert VTABLE == 0x00B04C88
    assert SINGLETON_ADDRESS == 0x00C10F68
    assert report["identity"]["constructor"] == "FUN_0071da20"
    assert report["identity"]["destructor"] == "FUN_0071dab0"
    assert report["identity"]["default_initializer"] == DEFAULT_INITIALIZER
    assert report["singleton"]["storage"] == "static"
    assert MINIMUM_OBSERVED_SPAN == 0x13A5
    assert report["minimum_observed_span"] == 0x13A5


def test_all_thirty_direct_reflection_fields_are_preserved():
    assert len(REFLECTED_FIELDS) == 30
    fields = reflected_field_index()
    assert len(fields) == 30
    assert fields["Garage Depth"]["offset"] == 0x10
    assert fields["Groove Width"]["offset"] == 0x2C
    assert fields["Waypoints"]["offset"] == 0x70
    assert fields["GRID"]["offset"] == 0x9C
    assert fields["PITS"]["offset"] == 0xA0
    assert fields["Track State"]["offset"] == 0x1304
    assert fields["Cheat Delta Best"]["offset"] == 0x1338


def test_reflected_array_fields_keep_source_callback_pairs():
    fields = reflected_field_index()
    assert fields["GRID"]["callbacks"] == ["FUN_00715fc0", "FUN_00716100"]
    assert fields["TELEPORT"]["callbacks"] == ["FUN_00716850", "FUN_007162a0"]
    assert fields["PITS"]["callbacks"] == ["FUN_00716440", "FUN_00716610"]
    assert fields["Waypoints"].get("callbacks") is None


def test_constructor_defaults_match_fun_00715690():
    defaults = reflected_constructor_defaults()
    assert defaults["Pit Lanes"] == 1
    assert defaults["Starting Grid"] == 104
    assert defaults["Pit Spots"] == 52
    assert defaults["Garage Spots"] == 3
    assert defaults["Fuel Use"] == 0
    assert math.isclose(defaults["Groove Width"], 6.0)
    assert math.isclose(defaults["Wet Groove Width"], 4.3125)
    assert math.isclose(defaults["Qual Ratio"], 1.005, rel_tol=1e-6)
    assert math.isclose(defaults["Race Ratio"], 0.99, rel_tol=1e-6)
    assert defaults["Waypoints"] == 0
    assert defaults["Dry Line Time"] > 3.0e38
    assert defaults["Wet Line Time"] > 3.0e38


def test_constructor_write_contract_preserves_write_widths_and_flag():
    writes = {row["offset"]: row for row in constructor_default_writes()}
    assert writes[0x48] == {"offset": 0x48, "width": 1, "raw_value": 0}
    assert writes[0x2C]["raw_value"] == 0x40C00000
    assert writes[0x2C]["float_value"] == 6.0
    assert writes[SOURCE_RECORD_PTR_OFFSET] == {
        "offset": SOURCE_RECORD_PTR_OFFSET,
        "width": 4,
        "raw_value": 0,
    }
    assert writes[META_RECORD_PTR_OFFSET] == {
        "offset": META_RECORD_PTR_OFFSET,
        "width": 4,
        "raw_value": 0,
    }
    assert writes[META_REBUILD_FLAG_OFFSET] == {
        "offset": META_REBUILD_FLAG_OFFSET,
        "width": 1,
        "raw_value": 1,
    }


def test_meta_section_storage_uses_recovered_pointer_count_pairs_and_strides():
    storage = describe_meta_section_storage()
    source = storage["source_records"]
    meta = storage["meta_records"]

    assert SOURCE_RECORD_PTR_OFFSET == 0x1394
    assert SOURCE_RECORD_COUNT_OFFSET == 0x1398
    assert SOURCE_RECORD_STRIDE == 0x18
    assert source["pointer_offset"] == SOURCE_RECORD_PTR_OFFSET
    assert source["count_offset"] == SOURCE_RECORD_COUNT_OFFSET
    assert source["stride"] == SOURCE_RECORD_STRIDE
    assert source["meta_index_offset"] == 0x14

    assert META_RECORD_PTR_OFFSET == 0x139C
    assert META_RECORD_COUNT_OFFSET == 0x13A0
    assert META_RECORD_STRIDE == 0x14
    assert meta["pointer_offset"] == META_RECORD_PTR_OFFSET
    assert meta["count_offset"] == META_RECORD_COUNT_OFFSET
    assert meta["stride"] == META_RECORD_STRIDE
    assert meta["source_index_offset"] == 0x4
    assert meta["secondary_index_offset"] == 0x8
    assert meta["range_start_offset"] == 0xC
    assert meta["range_end_offset"] == 0x10
    assert storage["rebuild_flag_offset"] == 0x13A4
    assert storage["rebuild_flag_default"] == 1
    assert storage["clear_function"] == "FUN_0071dbf0"
    assert storage["rebuild_function"] == "FUN_0071dc90"


def test_runtime_report_keeps_unknown_semantics_out_of_contract():
    report = describe_ai_database_runtime()
    assert report["direct_reflected_field_count"] == 30
    assert "not inferred" in report["evidence_boundary"]
    assert "does not assign names" in report["meta_section_storage"]["boundary"]
