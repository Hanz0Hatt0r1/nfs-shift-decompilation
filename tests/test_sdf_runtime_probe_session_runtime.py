import json

import pytest

import sdf_runtime_probe_session_runtime as runtime
import tools.verify_sdf_probe_session as cli


def _pre(frame=12):
    n = 3
    return {
        "scalar_count": n,
        "rhs": [1.0, 2.0, 3.0],
        "matrix": [
            [1.0, 2.0, 0.0],
            [2.0, 3.0, 4.0],
            [0.0, 4.0, 5.0],
        ],
        "row_indices": [0, 3, 6],
        "frame": frame,
    }


def _post(frame=12):
    return {
        "scalar_count": 3,
        "rhs": [7.0, 8.0, 9.0],
        "frame_index": frame,
        "source_function": "FUN_007b4110",
    }


def test_normalize_probe_session_accepts_matching_pre_post_frame():
    result = runtime.normalize_probe_session(_pre(), _post())
    assert result["ready"] is True
    assert result["frame"] == 12
    assert result["post_solve"]["rhs"] == [7.0, 8.0, 9.0]


def test_normalize_probe_session_blocks_frame_mismatch():
    result = runtime.normalize_probe_session(_pre(12), _post(13))
    assert result["ready"] is False
    assert "frame-index-mismatch" in result["errors"]


def test_normalize_probe_session_blocks_post_scalar_count_mismatch():
    post = _post()
    post["scalar_count"] = 2
    result = runtime.normalize_probe_session(_pre(), post)
    assert result["ready"] is False
    assert "post-solve-scalar-count" in result["errors"]


def test_compare_probe_session_reports_pre_matrix_and_post_vector_diffs():
    observed = {"pre_solve": _pre(), "post_solve": _post()}
    expected = {"pre_solve": _pre(), "post_solve": _post()}
    observed["pre_solve"]["matrix"][1][2] = 4.5
    observed["post_solve"]["rhs"][1] = 8.25
    result = runtime.compare_probe_session(observed, expected)
    assert result["ready"] is False
    assert result["pre_solve"]["matrix"]["mismatches"][0]["row"] == 1
    assert result["post_solve"]["mismatches"][0]["index"] == 1


def test_compare_probe_session_accepts_identical_pre_post_pair():
    observed = {"pre_solve": _pre(), "post_solve": _post()}
    expected = {"pre_solve": _pre(), "post_solve": _post()}
    result = runtime.compare_probe_session(observed, expected)
    assert result["ready"] is True
    assert result["status"] == "matched"


def test_compare_probe_session_blocks_missing_post_capture_when_expected_has_one():
    observed = {"pre_solve": _pre()}
    expected = {"pre_solve": _pre(), "post_solve": _post()}
    result = runtime.compare_probe_session(observed, expected)
    assert result["ready"] is False
    assert result["post_solve"]["errors"][0]["kind"] == "missing-observed-post-solve"


def test_session_cli_builds_parser_with_optional_post_and_expected_capture():
    args = cli.build_parser().parse_args([
        "--pre", "pre.json",
        "--post", "post.json",
        "--expected-pre", "expected-pre.json",
        "--expected-post", "expected-post.json",
    ])
    assert args.pre.name == "pre.json"
    assert args.post.name == "post.json"
    assert args.expected_pre.name == "expected-pre.json"


def test_session_cli_can_write_normalized_report(monkeypatch, tmp_path, capsys):
    pre = tmp_path / "pre.json"
    post = tmp_path / "post.json"
    out = tmp_path / "session.json"
    pre.write_text(json.dumps(_pre()), encoding="utf-8")
    post.write_text(json.dumps(_post()), encoding="utf-8")

    rc = cli.main([
        "--pre", str(pre),
        "--post", str(post),
        "-o", str(out),
    ])
    assert rc == 0
    assert out.exists()
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["ready"] is True
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["status"] == "normalized"


def test_session_cli_can_report_numeric_divergence(monkeypatch, tmp_path, capsys):
    pre = tmp_path / "pre.json"
    post = tmp_path / "post.json"
    expected_pre = tmp_path / "expected-pre.json"
    pre.write_text(json.dumps(_pre()), encoding="utf-8")
    post.write_text(json.dumps(_post()), encoding="utf-8")
    expected_pre.write_text(json.dumps(_pre()), encoding="utf-8")

    rc = cli.main([
        "--pre", str(pre),
        "--post", str(post),
        "--expected-pre", str(expected_pre),
        "--abs-tol", "0",
        "--rel-tol", "0",
    ])
    assert rc == 0
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["status"] == "matched"



def test_session_accepts_matching_frame_entry_builtin_capture():
    pre = _pre(frame=12)
    post = _post(frame=12)
    frame = {
        "format": "SHIFT.SDFRuntimeProbeFrameEntry/1",
        "version": 1,
        "ready": True,
        "status": "captured",
        "frame_index": 12,
        "backend": "builtin",
        "provider": 0,
        "scalar_count": 3,
    }
    result = runtime.normalize_probe_session(pre, post, frame)
    assert result["ready"] is True
    assert result["format"] == "SHIFT.SDFRuntimeProbeSession/2"
    assert result["frame_entry"]["backend"] == "builtin"


def test_session_blocks_provider_backend_when_builtin_pre_capture_is_present():
    pre = _pre(frame=7)
    frame = {
        "format": "SHIFT.SDFRuntimeProbeFrameEntry/1",
        "version": 1,
        "ready": True,
        "status": "captured",
        "frame_index": 7,
        "backend": "provider",
        "provider": 0x1234,
        "scalar_count": 3,
    }
    result = runtime.normalize_probe_session(pre, None, frame)
    assert result["ready"] is False
    assert "provider-backend-bypasses-builtin-capture" in result["errors"]


def test_session_blocks_frame_entry_index_mismatch():
    pre = _pre_capture(frame=7)
    frame = {
        "format": "SHIFT.SDFRuntimeProbeFrameEntry/1",
        "version": 1,
        "ready": True,
        "status": "captured",
        "frame_index": 8,
        "backend": "builtin",
        "provider": 0,
        "scalar_count": 40,
    }
    result = runtime.normalize_probe_session(pre, None, frame)
    assert result["ready"] is False
    assert "frame-entry-pre-solve-index-mismatch" in result["errors"]
