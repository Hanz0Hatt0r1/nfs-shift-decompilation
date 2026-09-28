import json

import pytest

import tools.verify_bmw_m3_solver_capture as cli


def _capture40():
    n = 40
    return {
        "scalar_count": n,
        "rhs": [float(index) for index in range(n)],
        "matrix": [
            [1.0 if row == column else 0.0 for column in range(n)]
            for row in range(n)
        ],
        "row_indices": [n * row for row in range(n)],
        "runtime_identity_nodes": [3, 9],
    }


def _fake_domain(_path):
    return {
        "ready": True,
        "source": {"archive": "BMW_M3_E36.bff"},
        "sdf": {"record_count": 24, "topology": {"body_count": 11}},
        "solver_domain": {"solver_scalar_count": 40},
    }


def test_build_report_verifies_bmw_shape_without_expected_values(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "verify_bff_domain", _fake_domain)
    capture_path = tmp_path / "capture.json"
    capture_path.write_text(
        json.dumps(_capture40()),
        encoding="utf-8",
    )

    report = cli.build_report(
        bff_path=tmp_path / "BMW_M3_E36.bff",
        capture_path=capture_path,
    )
    assert report["ready"] is True
    assert report["status"] == "verified-structure"
    assert report["domain"]["solver_domain"]["solver_scalar_count"] == 40
    assert report["capture"]["structure"]["observed"]["matrix_bytes"] == 12800


def test_build_report_blocks_bad_capture_shape(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "verify_bff_domain", _fake_domain)
    capture = _capture40()
    capture["scalar_count"] = 39
    capture["rhs"] = capture["rhs"][:39]
    capture["matrix"] = [row[:39] for row in capture["matrix"][:39]]
    capture["row_indices"] = [39 * row for row in range(39)]
    capture_path = tmp_path / "capture.json"
    capture_path.write_text(json.dumps(capture), encoding="utf-8")

    report = cli.build_report(
        bff_path=tmp_path / "BMW_M3_E36.bff",
        capture_path=capture_path,
    )
    assert report["ready"] is False
    assert report["status"] == "diverged-or-blocked"
    assert any(
        error.startswith("solver-scalar-count:")
        for error in report["capture"]["structure"]["errors"]
    )


def test_build_report_performs_exact_pair_comparison(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "verify_bff_domain", _fake_domain)
    expected_path = tmp_path / "expected.json"
    capture_path = tmp_path / "capture.json"
    expected = _capture40()
    observed = _capture40()
    observed["rhs"][11] = 11.5
    expected_path.write_text(json.dumps(expected), encoding="utf-8")
    capture_path.write_text(json.dumps(observed), encoding="utf-8")

    report = cli.build_report(
        bff_path=tmp_path / "BMW_M3_E36.bff",
        capture_path=capture_path,
        expected_capture_path=expected_path,
    )
    assert report["ready"] is False
    assert report["status"] == "diverged-or-blocked"
    assert report["comparison"]["status"] == "diverged"
    assert report["comparison"]["rhs"]["mismatches"][0]["index"] == 11


def test_cli_main_writes_report_and_returns_zero_for_structural_success(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "verify_bff_domain", _fake_domain)
    bff = tmp_path / "BMW_M3_E36.bff"
    capture = tmp_path / "capture.json"
    output = tmp_path / "report" / "solver.json"
    bff.write_bytes(b"placeholder")
    capture.write_text(json.dumps(_capture40()), encoding="utf-8")

    rc = cli.main([
        str(bff),
        str(capture),
        "--output",
        str(output),
    ])
    assert rc == 0
    assert output.exists()
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["status"] == "verified-structure"


def test_cli_parser_keeps_expected_capture_optional():
    args = cli.build_parser().parse_args([
        "BMW_M3_E36.bff",
        "capture.json",
    ])
    assert args.expected_capture is None
    assert args.abs_tol == 0.0
    assert args.rel_tol == 0.0
    assert args.output is None
