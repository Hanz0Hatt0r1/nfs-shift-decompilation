from pathlib import Path

from vehicle_physics_asset_graph_runtime import build_profile


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_vehicle_physics_graph_joins_all_four_resource_boundaries(tmp_path):
    cdf = _write(tmp_path, "car.cdf", "[GENERAL]\nMass=1000\n")
    edf = _write(tmp_path, "car.edf", "RPMTorque=(1000,10,20)\nRPMTorque=(2000,11,21)\n")
    gdf = _write(
        tmp_path,
        "gear.gdf",
        "[GEAR_RATIOS]\nratio=(10,35)\n[FINAL_DRIVE]\nbevel=(1,1)\nratio=(6,39)\n",
    )
    sdf = _write(
        tmp_path,
        "susp.sdf",
        "[BODY]\nname=body mass=(1) inertia=(1,1,1) pos=(0,0,0) ori=(0,0,0)\n"
        "[JOINT&HINGE]\nposbody=wheel negbody=spindle pos=wheel axis=(1,0,0)\n",
    )
    report = build_profile(cdf=cdf, edf=edf, gdf=gdf, sdf=sdf)
    assert report["ready"] is True
    assert report["summary"]["cdf_sections"] == 1
    assert report["summary"]["edf_rpm_torque_points"] == 2
    assert report["summary"]["gdf_gear_ratio_count"] == 1
    assert report["summary"]["gdf_final_drive_ratio_count"] == 1
    assert report["summary"]["sdf_bodies"] == 1
    assert report["summary"]["sdf_joint_hinge_count"] == 1
    assert report["load_graph"]["chassis"]["runtime_loader"] == "FUN_0074d640 -> FUN_007be420"
    assert report["load_graph"]["engine"]["runtime_loader"] == "FUN_007c3280"
    assert report["load_graph"]["gearbox"]["runtime_loader"] == "FUN_007c2110"
    assert report["load_graph"]["suspension"]["runtime_loader"] == "FUN_007bf790 -> FUN_007b6900"


def test_vehicle_physics_graph_fails_closed_on_malformed_resource(tmp_path):
    cdf = _write(tmp_path, "car.cdf", "[GENERAL]\nMass=1000\n")
    edf = _write(tmp_path, "car.edf", "RPMTorque=(1000,10,20)\nRPMTorque=(900,11,21)\n")
    gdf = _write(tmp_path, "gear.gdf", "[GEAR_RATIOS]\nratio=(10,35)\n")
    sdf = _write(tmp_path, "susp.sdf", "[BODY]\nname=body\n")
    report = build_profile(cdf=cdf, edf=edf, gdf=gdf, sdf=sdf)
    assert report["ready"] is False
    assert any(reason.startswith("edf:line:2:") for reason in report["blockers"])


def test_asset_graph_can_report_full_engine_edf_summary(tmp_path):
    from engine_edf_runtime import parse_engine_edf

    report = parse_engine_edf("""
RPMTorque=(1000,-30,200)
RPMTorque=(2000,-20,250)
FuelConsumption=3.9e-5
EngineInertia=0.300
IdleRPMLogic=(1000,1050)
RevLimitAvailable=1
EngineSound=(0.33,0.8,-1.0)
""")
    assert report["ready"] is True
    assert report["entry_count"] == 7
    assert report["recognized_entry_count"] == 7
    assert report["unknown_entry_count"] == 0
    assert report["rpm_torque"]["point_count"] == 2
    assert report["entries"][0]["schema"]["offset"] == 0x16D8
    assert report["entries"][3]["schema"]["width"] == "vec2"


def test_asset_graph_retains_unknown_engine_properties():
    from engine_edf_runtime import parse_engine_edf

    report = parse_engine_edf("[future]\nUnknownKey=123\n")
    assert report["unknown_entry_count"] == 1
    assert report["unknown_keys"] == ["UnknownKey"]
