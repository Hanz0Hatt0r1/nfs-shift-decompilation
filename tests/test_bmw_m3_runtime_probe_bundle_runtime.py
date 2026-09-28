import json

import bmw_m3_runtime_probe_bundle_runtime as runtime


def test_bundle_report_blocks_without_real_pre_solve_capture(tmp_path, monkeypatch):
    monkeypatch.setattr(
        runtime,
        "resolve_probe_executable",
        lambda input_path, work_dir: tmp_path / "SHIFT.exe",
    )
    monkeypatch.setattr(
        runtime,
        "validate_probe_executable_file",
        lambda path: {
            "format": "SHIFT.SDFRuntimeProbePEValidation/1",
            "version": 1,
            "ready": True,
            "status": "validated",
            "errors": [],
            "sha256": "a" * 64,
        },
    )
    monkeypatch.setattr(
        runtime,
        "verify_bff_domain",
        lambda path: {"ready": True, "solver_domain": {"solver_scalar_count": 40}},
    )

    report = runtime.build_bundle_report(
        shift_input=tmp_path / "SHIFT.zip",
        bff_path=tmp_path / "BMW_M3_E36.bff",
        pre_path=None,
        work_dir=tmp_path / "bundle",
    )
    assert report["ready"] is False
    assert report["gates"]["retail_pe"] is True
    assert report["gates"]["bmw_m3_domain"] is True
    assert report["gates"]["frame_pre_post"] is False
    assert "missing:pre-solve-capture" in report["errors"]


def test_bundle_report_accepts_matching_structural_capture(
    tmp_path,
    monkeypatch,
):
    pre_path = tmp_path / "pre.json"
    pre_path.write_text(json.dumps({
        "format": "SHIFT.SDFRuntimeProbe/1",
        "version": 1,
        "frame": 17,
        "solver_scalar_count": 3,
        "matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        "rhs": [1.0, 2.0, 3.0],
    }), encoding="utf-8")

    monkeypatch.setattr(
        runtime,
        "resolve_probe_executable",
        lambda input_path, work_dir: tmp_path / "SHIFT.exe",
    )
    monkeypatch.setattr(
        runtime,
        "validate_probe_executable_file",
        lambda path: {
            "format": "SHIFT.SDFRuntimeProbePEValidation/1",
            "version": 1,
            "ready": True,
            "status": "validated",
            "errors": [],
            "sha256": "a" * 64,
        },
    )
    monkeypatch.setattr(
        runtime,
        "verify_bff_domain",
        lambda path: {"ready": True, "solver_domain": {"solver_scalar_count": 3}},
    )

    report = runtime.build_bundle_report(
        shift_input=tmp_path / "SHIFT.zip",
        bff_path=tmp_path / "BMW_M3_E36.bff",
        pre_path=pre_path,
        work_dir=tmp_path / "bundle",
    )
    assert report["ready"] is True
    assert report["gates"]["frame_pre_post"] is True
    assert report["capture"]["structure"]["ready"] is True
    assert report["capture"]["session"]["frame"] == 17


def test_bundle_report_blocks_bad_bmw_capture_shape(tmp_path, monkeypatch):
    pre_path = tmp_path / "pre.json"
    pre_path.write_text(json.dumps({
        "format": "SHIFT.SDFRuntimeProbe/1",
        "version": 1,
        "frame": 17,
        "solver_scalar_count": 2,
        "matrix": [[1.0, 0.0], [0.0, 1.0]],
        "rhs": [1.0, 2.0],
    }), encoding="utf-8")

    monkeypatch.setattr(
        runtime,
        "resolve_probe_executable",
        lambda input_path, work_dir: tmp_path / "SHIFT.exe",
    )
    monkeypatch.setattr(
        runtime,
        "validate_probe_executable_file",
        lambda path: {"ready": True, "status": "validated", "errors": []},
    )
    monkeypatch.setattr(
        runtime,
        "verify_bff_domain",
        lambda path: {"ready": True, "solver_domain": {"solver_scalar_count": 40}},
    )

    report = runtime.build_bundle_report(
        shift_input=tmp_path / "SHIFT.zip",
        bff_path=tmp_path / "BMW_M3_E36.bff",
        pre_path=pre_path,
        work_dir=tmp_path / "bundle",
    )
    assert report["ready"] is False
    assert "capture:solver-scalar-count:2!=40" in report["errors"]
