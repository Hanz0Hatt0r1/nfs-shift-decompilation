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
        "[BODY]\nname=wheel mass=(1) inertia=(1,1,1) pos=(0,0,0) ori=(0,0,0)\n"
        "[BODY]\nname=spindle mass=(1) inertia=(1,1,1) pos=(0,0,0) ori=(0,0,0)\n"
        "[JOINT&HINGE]\nposbody=wheel negbody=spindle pos=wheel axis=(1,0,0)\n",
    )
    report = build_profile(cdf=cdf, edf=edf, gdf=gdf, sdf=sdf)
    assert report["ready"] is True
    assert report["summary"]["cdf_sections"] == 1
    assert report["summary"]["edf_rpm_torque_points"] == 2
    assert report["summary"]["gdf_gear_ratio_count"] == 1
    assert report["summary"]["gdf_final_drive_ratio_count"] == 1
    assert report["summary"]["sdf_bodies"] == 3
    assert report["summary"]["sdf_joint_hinge_count"] == 1
    assert report["summary"]["sdf_constraint_runtime_record_count"] == 2
    assert report["summary"]["sdf_constraint_solver_graph_ready"] is True
    assert report["summary"]["sdf_solver_scalar_count"] == 5
    assert report["summary"]["sdf_sparse_solver_contract_ready"] is True
    assert report["summary"]["sdf_builtin_sparse_solver_ready"] is True
    assert report["summary"]["sdf_builtin_sparse_solver_function"] == "FUN_007b0f20"
    assert report["summary"]["sdf_sparse_solver_validation_ready"] is True
    assert "sdf_builtin_diagonal_reset_node_count" in report["summary"]
    assert report["summary"]["sdf_body_state_projection_contract_ready"] is True
    assert report["summary"]["sdf_body_impulse_primitives_ready"] is True
    assert report["summary"]["sdf_body_tensor_ready"] is True
    assert report["summary"]["sdf_body_frame_ready"] is True
    assert report["summary"]["sdf_joint_projection_ready"] is True
    assert report["summary"]["sdf_hinge_projection_ready"] is True
    assert report["summary"]["sdf_bar_matrix_coupling_ready"] is True
    assert report["summary"]["sdf_joint_matrix_coupling_ready"] is True
    assert report["summary"]["sdf_joint_d15_source_audit_ready"] is True
    assert report["summary"]["sdf_hinge_bar_matrix_coupling_ready"] is True
    assert report["summary"]["sdf_post_solve_application_ready"] is True
    assert report["summary"]["sdf_matrix_assembly_ready"] is True
    assert report["summary"]["sdf_matrix_storage_ready"] is True
    assert report["summary"]["sdf_real_solver_domain_ready"] is True
    assert report["summary"]["sdf_matrix_seed_write_ready"] is True
    assert report["summary"]["sdf_full_frame_contract_ready"] is True
    assert report["summary"]["sdf_solver_frame_verification_ready"] is True
    assert report["summary"]["sdf_full_frame_runtime_ready"] is False
    assert report["summary"]["sdf_solver_capture_contract_ready"] is True
    assert report["summary"]["sdf_solver_capture_binary_contract_ready"] is True
    assert report["summary"]["bmw_m3_solver_capture_verifier_ready"] is True
    assert report["summary"]["sdf_runtime_probe_ready"] is True
    assert report["summary"]["sdf_runtime_probe_session_ready"] is True
    assert report["summary"]["sdf_runtime_probe_session_schema_v2_ready"] is True
    assert report["summary"]["sdf_runtime_probe_pe_ready"] is True
    assert report["summary"]["sdf_runtime_probe_launcher_ready"] is True
    assert report["summary"]["sdf_runtime_probe_backend_contract_ready"] is True
    assert report["summary"]["sdf_matrix_seed_write_count"] == 25
    assert report["summary"]["sdf_real_solver_scalar_count"] == 5
    assert report["summary"]["sdf_constraint_shared_body_pair_count"] == 1
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
    assert report["entries"][2]["schema"]["width"] == "vec2"


def test_asset_graph_retains_unknown_engine_properties():
    from engine_edf_runtime import parse_engine_edf

    report = parse_engine_edf("[future]\nUnknownKey=123\n")
    assert report["unknown_entry_count"] == 1
    assert report["unknown_keys"] == ["UnknownKey"]


def test_engine_edf_profile_exposes_rpm_torque_derived_values():
    from engine_edf_runtime import parse_engine_edf

    report = parse_engine_edf("""
RPMTorque=(1000,-30,100)
RPMTorque=(2000,-10,200)
""")
    peak = report["rpm_torque"]["peak_power_scan"]
    assert peak["point_index"] == 1
    assert peak["rpm"] == 2000.0
    assert report["rpm_torque"]["interpolation_examples"][0]["throttle"] == 100.0
    assert report["rpm_torque"]["interpolation_examples"][1]["throttle"] == 200.0
