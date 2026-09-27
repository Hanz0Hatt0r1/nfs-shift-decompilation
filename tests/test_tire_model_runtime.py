from tire_model_runtime import (
    COMPOUND_PROPERTIES,
    COMPOUND_SCOPE_TOKENS,
    RUNTIME_CURVE_POINTERS,
    SLIPCURVE_PROPERTIES,
    SLIP_CURVE_OBJECT,
    CubicSegment,
    analyze_source,
    build_curve_contract,
    evaluate_precompiled_curve,
)


def test_tbc_layout_and_scope_dispatch_are_frozen():
    c = build_curve_contract()
    assert c["functions"]["load_tbc"] == "FUN_007a10f0"
    assert c["functions"]["build_curve"] == "FUN_007a07c0"
    assert c["functions"]["evaluate_curve"] == "FUN_007a0c00"
    assert SLIP_CURVE_OBJECT["record_stride"] == 0x38
    assert SLIP_CURVE_OBJECT["compiled_segment_stride"] == 0x28
    assert SLIP_CURVE_OBJECT["storage_pointer_offset"] == 0x34
    assert SLIP_CURVE_OBJECT["count_offset"] == 0x30
    assert COMPOUND_SCOPE_TOKENS[-1] == "ALL:"


def test_named_tire_compound_properties():
    assert COMPOUND_PROPERTIES == {
        "TyreLatDragReduction": 0x08,
        "TyreLongDragReduction": 0x10,
        "Style": 0x24,
        "LaunchControlFactor": 0x28,
    }


def test_slip_curve_properties_cover_observed_registry():
    assert SLIPCURVE_PROPERTIES["CorneringStiffness"] == 0x38
    assert SLIPCURVE_PROPERTIES["BrakingStiffness"] == 0x40
    assert SLIPCURVE_PROPERTIES["SelfAligningStiffness"] == 0x48
    assert SLIPCURVE_PROPERTIES["DesignLoad"] == 0x58
    assert SLIPCURVE_PROPERTIES["LatPeakMin"] == 0xF8
    assert SLIPCURVE_PROPERTIES["LongPeakMax"] == 0x120
    assert SLIPCURVE_PROPERTIES["OptimumPressureBase"] == 0x1F0
    assert SLIPCURVE_PROPERTIES["GripTempPressMax"] == 0x210
    assert SLIPCURVE_PROPERTIES["FailureTemp"] == 0x218
    assert SLIPCURVE_PROPERTIES["LatCurveName"] == 0x138
    assert SLIPCURVE_PROPERTIES["TractiveCurveName"] == 0x140


def test_runtime_binds_three_curves_per_wheel():
    assert RUNTIME_CURVE_POINTERS == {
        "LatCurve": 0x6E0,
        "BrakingCurve": 0x6E4,
        "TractiveCurve": 0x6E8,
    }


def test_cubic_segment_evaluation_matches_horner_form():
    segment = CubicSegment(2.0, -1.0, 0.5, 0.25)
    x = 0.75
    expected = ((2.0 * x - 1.0) * x + 0.5) * x + 0.25
    assert segment.evaluate(x) == expected


def test_precompiled_curve_uses_segment_clamp():
    segments = [CubicSegment(0.0, 0.0, 1.0, 0.0), CubicSegment(0.0, 0.0, 0.0, 2.0)]
    assert evaluate_precompiled_curve(
        x=0.2,
        domain=1.0,
        maximum_value=1.0,
        extrapolation_slope=0.0,
        extrapolation_base=0.0,
        segments=segments,
    ) == 0.2
    assert evaluate_precompiled_curve(
        x=0.99,
        domain=1.0,
        maximum_value=1.0,
        extrapolation_slope=0.0,
        extrapolation_base=0.0,
        segments=segments,
    ) == 2.0


def test_source_evidence_on_recovered_source(tmp_path):
    src = tmp_path / "SHIFT.exe.c"
    src.write_bytes(
        b"""FUN_007a10f0
FUN_007a07c0
FUN_007a0c00(*(int *)(iVar9 + 0x6e0),0,0x3ff00000,0.0001)
"[SLIPCURVE]"
"[COMPOUND]"
"LatCurve"
"BrakingCurve"
"TractiveCurve"
int FUN_00715990(float param_1)
.\\Source\\Vehicle\\tire_manager.cpp
"""
    )
    r = analyze_source(src)
    assert r["ready"] is True
    assert r["source_sha256"]
    assert r["curve_contract"]["source_lines"]["FUN_007a0c00"] == 799419


def test_source_evidence_fails_closed():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = __import__("pathlib").Path(td) / "empty.c"
        p.write_text("void foo(void) {}", encoding="utf-8")
        assert analyze_source(p)["ready"] is False


def test_curve_contract_keeps_semantics_conservative():
    c = build_curve_contract()
    assert "physical-unit/semantic labels remain conservative" in c["status"]
