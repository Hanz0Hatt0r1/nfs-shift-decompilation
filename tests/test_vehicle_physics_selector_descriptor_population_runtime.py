import vehicle_physics_selector_descriptor_population_runtime as runtime


def test_phase512_storage_capacity_and_wrapper_are_source_backed():
    report = runtime.build_vehicle_physics_selector_descriptor_population()

    assert report["format"] == "SHIFT.VehiclePhysicsSelectorDescriptorPopulation/1"
    assert report["ready"] is True
    assert report["storage"]["capacity_field"] == "context+0x28"
    assert report["storage"]["capacity_value"] == 16
    assert report["storage"]["descriptor_base"] == "context+0xb8"
    assert report["storage"]["descriptor_stride"] == "0x90"
    assert report["population"]["wrapper"]["function"] == "thunk_FUN_00409290"
    assert report["population"]["wrapper"]["condition"] == "context+0x1c < context+0x28"


def test_phase512_packed_token_layout_matches_source_operations():
    report = runtime.build_vehicle_physics_selector_descriptor_population()
    fields = report["population"]["packed_token"]["descriptor_fields"]

    assert fields["+0x00"] == "token bits 0..3"
    assert fields["+0x04"] == "token bits 4..7"
    assert fields["+0x08"] == "token bits 8..10"
    assert fields["+0x0c"] == "token bits 11..14"
    assert fields["+0x78"] == "token bits 15..18"
    assert fields["+0x7d"] == "source byte at +0x14 bit 0"


def test_phase512_string_and_block_copy_offsets_are_explicit():
    report = runtime.build_vehicle_physics_selector_descriptor_population()

    assert report["population"]["strings"] == [
        {"source": "+0x05", "destination": "+0x10"},
        {"source": "+0x25", "destination": "+0x14"},
        {"source": "+0x45", "destination": "+0x18"},
        {"source": "+0x76", "destination": "+0x24"},
        {"source": "+0x96", "destination": "+0x28"},
    ]
    copied = report["population"]["copied_block"]
    assert copied["source"] == "+0xa8"
    assert copied["destination"] == "+0x38"
    assert copied["dword_count"] == 14
    assert copied["byte_count"] == 56


def test_phase512_selector_state_and_conditional_field_are_separate():
    report = runtime.build_vehicle_physics_selector_descriptor_population()

    derived = report["population"]["derived_fields"]
    assert derived["+0x74"] == 0
    assert derived["+0x88"] == 0
    assert "descriptor+0x08 == 0" in derived["+0x70"]
    assert report["selection_relation"]["eligible_test"] == "descriptor+0x74 == 0"


def test_phase512_keeps_semantics_observational():
    report = runtime.build_vehicle_physics_selector_descriptor_population()
    limitations = " ".join(report["limitations"])

    assert "gameplay or physics meanings are not inferred" in limitations
    assert "Runtime provider identity" in limitations
