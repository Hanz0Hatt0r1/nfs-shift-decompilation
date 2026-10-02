import os
from pathlib import Path
import subprocess
import sys

from tools.audit_imb_corpus import FORMAT, audit_decoded_imb_rows


def test_all_ready_corpus_aggregates_versions_properties_and_totals():
    report = audit_decoded_imb_rows([
        {
            "archive": "A.bff",
            "path": "a.imb",
            "ready": True,
            "blocking_reasons": [],
            "version_text": "0.4.0.0",
            "vertex_count": 10,
            "primitive_count": 2,
            "decoded_properties": ["200", "130", "460"],
            "deferred_stream_count": 1,
        },
        {
            "archive": "B.bff",
            "path": "b.imb",
            "ready": True,
            "blocking_reasons": [],
            "version_text": "0.4.0.0",
            "vertex_count": 20,
            "primitive_count": 3,
            "decoded_properties": ["200", "130"],
            "deferred_stream_count": 0,
        },
    ])

    assert report["format"] == FORMAT
    assert report["status"] == "ready"
    assert report["ready"] is True
    assert report["resource_count"] == 2
    assert report["ready_count"] == 2
    assert report["blocked_count"] == 0
    assert report["total_vertex_count"] == 30
    assert report["total_primitive_count"] == 5
    assert report["total_triangle_count"] == 0
    assert report["bone_resource_count"] == 0
    assert report["total_deferred_stream_count"] == 1
    assert report["version_counts"] == {"0.4.0.0": 2}
    assert report["decoded_property_use_counts"] == {
        "130": 2,
        "200": 2,
        "460": 1,
    }


def test_partial_corpus_preserves_blocker_and_exception_distribution():
    report = audit_decoded_imb_rows([
        {
            "archive": "A.bff",
            "path": "ready.imb",
            "ready": True,
            "blocking_reasons": [],
            "version_text": "0.4.0.0",
            "vertex_count": 3,
            "primitive_count": 1,
            "decoded_properties": ["200"],
            "deferred_stream_count": 0,
        },
        {
            "archive": "A.bff",
            "path": "blocked.imb",
            "ready": False,
            "blocking_reasons": ["position-stream-200-missing"],
            "version_text": "0.4.0.0",
            "vertex_count": 3,
            "primitive_count": 1,
            "decoded_properties": ["130"],
            "deferred_stream_count": 2,
        },
        {
            "archive": "B.bff",
            "path": "bad.imb",
            "ready": False,
            "blocking_reasons": ["decode-exception"],
            "error_kind": "ValueError",
            "vertex_count": 0,
            "primitive_count": 0,
            "decoded_properties": [],
            "deferred_stream_count": 0,
        },
    ])

    assert report["status"] == "partial"
    assert report["ready"] is False
    assert report["resource_count"] == 3
    assert report["ready_count"] == 1
    assert report["blocked_count"] == 2
    assert report["blocking_reason_counts"] == {
        "decode-exception": 1,
        "position-stream-200-missing": 1,
    }
    assert report["error_kind_counts"] == {"ValueError": 1}
    assert report["total_deferred_stream_count"] == 2


def test_empty_corpus_is_explicitly_empty_not_ready():
    report = audit_decoded_imb_rows([])
    assert report["status"] == "empty"
    assert report["ready"] is False
    assert report["resource_count"] == 0
    assert report["rows"] == []


def test_audit_imb_corpus_cli_imports_without_pythonpath():
    repo_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "tools" / "audit_imb_corpus.py"),
            "--help",
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Audit neutral IMB geometry readiness" in result.stdout
