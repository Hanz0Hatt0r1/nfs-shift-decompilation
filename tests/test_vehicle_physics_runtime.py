import pytest

from vehicle_physics_runtime import (
    SECTION_TARGETS,
    analyze_source,
    build_vehicle_physics_contract,
    validate_contract_shape,
)


def _by_name(rows):
    return {row["name"]: row for row in rows}


def test_hdvehicle_section_dispatch_is_explicit():
    c = build_vehicle_physics_contract()
    assert c["vehicle_loader"]["function"] == "FUN_007c3b00"
    assert c["vehicle_loader"]["sections"]["GENERAL"]["parser"] == "FUN_007be420"
    assert c["vehicle_loader"]["sections"]["DRIVELINE"]["parser"] == "FUN_007bcdf0"
    assert c["vehicle_loader"]["sections"]["SUSPENSION"]["parser"] == "FUN_007bdb80"
    assert c["vehicle_loader"]["sections"]["FRONTLEFT"]["index"] == 0
    assert c["vehicle_loader"]["sections"]["REARRIGHT"]["index"] == 3
    assert c["vehicle_loader"]["sections"]["ENGINE"]["special"] == "SpeedLimiter"
    assert set(SECTION_TARGETS) == {
        "GENERAL", "FRONTWING", "LEFTFENDER", "RIGHTFENDER", "REARWING",
        "BODYAERO", "DIFFUSER", "SUSPENSION", "CONTROLS", "ENGINE", "DRIVELINE",
        "FRONTLEFT", "FRONTRIGHT", "REARLEFT", "REARRIGHT", "BASIC",
    }


def test_general_mass_inertia_and_cg_offsets():
    rows = _by_name(build_vehicle_physics_contract()["general"])
    assert rows["Mass"]["offset"] == 0x1C
    assert rows["Inertia"]["offset"] == 0x30
    assert rows["Inertia"]["width"] == "vec3"
    assert rows["DriftInertia"]["offset"] == 0x78
    assert rows["CGHeight"]["offset"] == 0x180


def test_engine_rpm_torque_and_file_boundary():
    c = build_vehicle_physics_contract()["engine"]
    rows = _by_name(c["properties"])
    assert rows["EngineInertia"]["offset"] == 0x16F8
    assert rows["RevLimitRange"]["width"] == "vec3"
    assert rows["EngineMapRange"]["offset"] == 0x17C0
    assert rows["OnboardStarter"]["offset"] == 0x28F1
    assert c["file_loader"] == "FUN_007c3280"
    assert c["rpm_torque"]["storage_base_offset"] == 0x1818
    assert c["rpm_torque"]["entry_stride"] == 0x20
    assert c["rpm_torque"]["diagnostic_when_existing_points_ge"] == 127


def test_wheel_and_suspension_parameter_boundaries():
    c = build_vehicle_physics_contract()
    wheel = _by_name(c["wheel"])
    suspension = _by_name(c["suspension"])
    assert wheel["BumpTravel"]["offset"] == 0
    assert wheel["BrakeTorque"]["offset"] == 0xC0
    assert wheel["SpringRange"]["width"] == "vec3"
    assert wheel["BrakePadSetting"]["offset"] == 0x2E0
    assert suspension["ApplySlowToFastDampers"]["offset"] == 0x18
    assert suspension["AlignWheels"]["offset"] == 0x1A
    assert suspension["FrontAntiSwayRange"]["width"] == "vec3"
    assert suspension["RearToeInSetting"]["offset"] == 0x3C0


def test_driveline_registration_contains_named_controls_and_eight_gears():
    rows = _by_name(build_vehicle_physics_contract()["driveline"])
    assert rows["WheelDrive"]["offset"] == 0x04
    assert rows["ClutchEngageRate"]["offset"] == 0x08
    assert rows["AllowManualOverride"]["offset"] == 0x6C
    assert rows["SemiAutomatic"]["offset"] == 0x6D
    assert rows["FinalDriveSetting"]["offset"] == 0x190
    assert [rows[f"Gear{i}Setting"]["offset"] for i in range(1, 9)] == [
        0x1B8, 0x1CC, 0x1E0, 0x1F4, 0x208, 0x21C, 0x230, 0x244
    ]
    assert rows["DiffPowerRange"]["offset"] == 0x148
    assert rows["DiffPreloadSetting"]["offset"] == 0x294


def test_driveline_solver_contract():
    solver = build_vehicle_physics_contract()["driveline_solver"]
    assert solver["integrator_function"] == "FUN_00764266"
    assert solver["solver_function"] == "FUN_007af310"
    assert solver["dimension"] == 6
    assert solver["failure_log"] == "Could not solve driveline"
    assert solver["source_line_hex"] == "0x1d46"
    assert solver["source_line_decimal"] == 7494
    assert [x["result_slot"] for x in solver["post_solver_wheel_sign_threshold_checks"]] == [
        "wheel_0", "wheel_1", "wheel_2", "wheel_3", "driveline_input"
    ]


def test_postload_order_is_preserved():
    assert build_vehicle_physics_contract()["postload"] == [
        "FUN_007c3920", "FUN_007bf0e0 x4", "FUN_007bf590", "FUN_007bfbe0",
        "FUN_007bdb60", "FUN_007bf790", "FUN_007bf6e0", "FUN_007c2110",
        "FUN_007bf430 x2", "FUN_007bf310 x2",
    ]


def test_contract_tables_have_no_duplicate_offsets_within_each_object():
    report = validate_contract_shape()
    assert report["ready"] is True
    assert report["property_counts"] == {
        "general": 19,
        "engine": 30,
        "suspension": 49,
        "wheel": 45,
        "driveline": 40,
    }


def test_source_evidence_is_extracted_without_local_absolute_paths(tmp_path):
    nl = chr(10)
    slash = chr(92) * 2
    source = nl.join([
        "void __thiscall FUN_007c3b00(void *this) {",
        "void __thiscall FUN_007be420(void *this) {",
        "void __thiscall FUN_007bc770(void *this) {",
        "void __thiscall FUN_007bdb80(void *this) {",
        "void __thiscall FUN_007bcdf0(void *this) {",
        "undefined4 __thiscall FUN_007c3280(void *this) {",
        "void __thiscall FUN_007c3920(void *this) {",
        "void __fastcall FUN_00764266(int param_1) {",
        "  iVar10 = FUN_007af310(unaff_EBP + -0x1b8,6);",
        '  FUN_0062de20("Could not solve driveline");',
        '  FUN_0062de50(0xb095d8,".' + slash + 'Source' + slash + 'Vehicle' + slash + 'hdvehicle.cpp",0x1d46,0xb09600,0);',
        "  FUN_00632920(this, x.edf);",
        "  FUN_007c3920(this,this_00,&param_3,param_5);",
        '  FUN_0062de20("Too many RPM-torque points");',
        '  FUN_0062de20("Could not open Engine file: %s");',
        '  FUN_0062de50(0xaac44c,".' + slash + 'Source' + slash + 'Vehicle' + slash + 'vehload.cpp",0x6b8,0xb0f5f4,0);',
    ])
    p = tmp_path / "recovered.c"
    p.write_text(source, encoding="utf-8")
    report = analyze_source(p)
    assert report["ready"] is True
    assert report["function_lines"]["FUN_00764266"] == 8
    assert report["function_lines"]["FUN_007af310"] == 9


def test_source_evidence_fails_closed_for_incomplete_input(tmp_path):
    p = tmp_path / "empty.c"
    p.write_text("void foo(void) { return; }", encoding="utf-8")
    report = analyze_source(p)
    assert report["ready"] is False
    assert not all(report["checks"].values())



def test_rpm_torque_source_order_is_rpm_brake_throttle():
    from vehicle_physics_runtime import parse_rpm_torque_points

    report = parse_rpm_torque_points("""
RPMTorque=(0,-58.40,-58.00)
RPMTorque=(250,-33.00,-9.00)
RPMTorque=(500,-13.70,60.00)
""")
    assert report["ready"] is True
    assert report["point_count"] == 3
    assert report["points"][0]["source_tuple"] == [0.0, -58.4, -58.0]
    assert report["points"][0]["storage_order"] == [-58.4, -58.0, 0.0]
    assert report["storage"]["base_offset"] == 0x1818
    assert report["storage"]["record_stride"] == 0x20


def test_rpm_torque_rejects_brake_above_throttle_and_non_monotonic_rpm():
    from vehicle_physics_runtime import parse_rpm_torque_points

    report = parse_rpm_torque_points("""
RPMTorque=(1000,50,40)
RPMTorque=(900,20,30)
""")
    assert report["ready"] is False
    assert any("brake-greater-than-throttle" in warning for warning in report["warnings"])
    assert any("curve-out-of-order" in warning for warning in report["warnings"])


def test_rpm_torque_limit_is_127_existing_points():
    from vehicle_physics_runtime import parse_rpm_torque_points

    text = "\n".join(
        f"RPMTorque=({index},{index},{index + 1})" for index in range(130)
    )
    report = parse_rpm_torque_points(text)
    assert report["point_count"] == 127
    assert "rpm-torque:too-many-points:127" in report["warnings"]


def test_rpm_torque_interpolation_matches_linear_bracket():
    from vehicle_physics_runtime import RPMTorquePoint, sample_rpm_torque_curve

    points = (
        RPMTorquePoint(1000.0, -30.0, 100.0),
        RPMTorquePoint(2000.0, -10.0, 200.0),
    )
    assert sample_rpm_torque_curve(points, 1500.0) == (-20.0, 150.0)


def test_rpm_torque_interpolation_extrapolates_using_end_segments():
    from vehicle_physics_runtime import RPMTorquePoint, sample_rpm_torque_curve

    points = (
        RPMTorquePoint(1000.0, -30.0, 100.0),
        RPMTorquePoint(2000.0, -10.0, 200.0),
        RPMTorquePoint(3000.0, -20.0, 150.0),
    )
    assert sample_rpm_torque_curve(points, 500.0) == (-40.0, 50.0)
    assert sample_rpm_torque_curve(points, 3500.0) == (-25.0, 125.0)


def test_rpm_torque_interpolation_midpoint_clamps_when_brake_exceeds_throttle():
    from vehicle_physics_runtime import RPMTorquePoint, sample_rpm_torque_curve

    points = (
        RPMTorquePoint(1000.0, 200.0, 100.0),
        RPMTorquePoint(2000.0, 300.0, 100.0),
    )
    assert sample_rpm_torque_curve(points, 1500.0) == (175.0, 175.0)


def test_rpm_torque_interpolation_handles_zero_and_one_point_curves():
    from vehicle_physics_runtime import RPMTorquePoint, sample_rpm_torque_curve

    assert sample_rpm_torque_curve((), 2000.0) == (0.0, 0.0)
    point = RPMTorquePoint(1000.0, -30.0, 120.0)
    assert sample_rpm_torque_curve((point,), 2000.0) == (-30.0, 120.0)


def test_rpm_torque_peak_power_scan_matches_source_conversion():
    from vehicle_physics_runtime import RPMTorquePoint, compute_rpm_torque_peak_power

    points = (
        RPMTorquePoint(5000.0, -100.0, 300.0),
        RPMTorquePoint(7000.0, -200.0, 320.0),
        RPMTorquePoint(7500.0, -226.0, 270.0),
    )
    result = compute_rpm_torque_peak_power(points)
    assert result["point_index"] == 1
    assert result["rpm"] == 7000.0
    assert result["throttle_torque"] == 320.0
    assert result["peak"] == pytest.approx(
        7000.0 * 320.0 * 0.73756105 / 5252.0
    )


def test_rpm_torque_peak_power_keeps_source_initial_value_for_empty_curve():
    from vehicle_physics_runtime import compute_rpm_torque_peak_power

    result = compute_rpm_torque_peak_power(())
    assert result == {
        "peak": 1.0,
        "point_index": None,
        "rpm": None,
        "throttle_torque": None,
    }
