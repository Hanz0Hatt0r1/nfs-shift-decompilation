import json
import zipfile
from pathlib import Path

import sdf_runtime_probe_evidence_bundle as runtime


def _write_capture(root: Path, *, timeline_ready: bool = True) -> None:
    (root / "relation_state_mutation_events.jsonl").write_text(
        json.dumps(
            {
                "format": "SHIFT.ConstraintRelationStateMutationCaptureRuntime/1",
                "runtime_event_sequence": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "relation_state_mutation_timeline.json").write_text(
        json.dumps(
            {
                "format": (
                    "SHIFT.ConstraintRelationStateMutationTimelineCorrelation/1"
                ),
                "status": "ready" if timeline_ready else "blocked",
                "ready": timeline_ready,
                "errors": [] if timeline_ready else ["blocked-fixture"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "frame_entry_000001.json").write_text(
        json.dumps(
            {
                "frame_index": 1,
                "runtime_event_sequence": 2,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "pre_solve_000001.json").write_text(
        '{"runtime_event_sequence":3}\n',
        encoding="utf-8",
    )
    (root / "post_solve_000001.json").write_text(
        '{"runtime_event_sequence":4}\n',
        encoding="utf-8",
    )
    (root / "scalar_reset_events.jsonl").write_text(
        '{"runtime_event_sequence":5}\n',
        encoding="utf-8",
    )


def test_phase639_packages_only_capture_evidence_and_manifest(tmp_path: Path):
    _write_capture(tmp_path)

    # Host-local / copyrighted / launcher files must not enter the archive.
    (tmp_path / "SHIFT.exe").write_bytes(b"retail")
    (tmp_path / "attach.gdb").write_text("secret-local-path\n", encoding="utf-8")
    (tmp_path / "probe_manifest.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "provider_capture_preflight.json").write_text(
        "{}\n",
        encoding="utf-8",
    )

    report = runtime.build_sdf_runtime_probe_evidence_bundle(tmp_path)

    assert report["ready"] is True
    assert report["capture_ready"] is True
    assert report["file_count"] == 6
    assert len(report["archive"]["sha256"]) == 64

    archive = Path(report["archive"]["path"])
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        assert names == [
            "evidence_manifest.json",
            "frame_entry_000001.json",
            "post_solve_000001.json",
            "pre_solve_000001.json",
            "relation_state_mutation_events.jsonl",
            "relation_state_mutation_timeline.json",
            "scalar_reset_events.jsonl",
        ]
        assert "SHIFT.exe" not in names
        assert "attach.gdb" not in names
        assert "probe_manifest.json" not in names
        assert "provider_capture_preflight.json" not in names

        manifest = json.loads(
            bundle.read("evidence_manifest.json").decode("utf-8")
        )
        assert manifest["format"] == runtime.FORMAT
        assert manifest["ready"] is True
        assert manifest["capture_ready"] is True
        assert manifest["archive_policy"]["includes_executable"] is False


def test_phase639_archive_is_byte_deterministic(tmp_path: Path):
    _write_capture(tmp_path)
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    report_a = runtime.build_sdf_runtime_probe_evidence_bundle(
        tmp_path,
        output_path=first,
    )
    report_b = runtime.build_sdf_runtime_probe_evidence_bundle(
        tmp_path,
        output_path=second,
    )

    assert first.read_bytes() == second.read_bytes()
    assert report_a["archive"]["sha256"] == report_b["archive"]["sha256"]


def test_phase639_manifest_hashes_match_archive_payloads(tmp_path: Path):
    _write_capture(tmp_path)
    report = runtime.build_sdf_runtime_probe_evidence_bundle(tmp_path)

    with zipfile.ZipFile(report["archive"]["path"]) as bundle:
        manifest = json.loads(
            bundle.read(runtime.MANIFEST_NAME).decode("utf-8")
        )
        for row in manifest["files"]:
            payload = bundle.read(row["path"])
            import hashlib

            assert hashlib.sha256(payload).hexdigest() == row["sha256"]
            assert len(payload) == row["size"]


def test_phase639_preserves_blocked_timeline_without_faking_capture_readiness(
    tmp_path: Path,
):
    _write_capture(tmp_path, timeline_ready=False)

    report = runtime.build_sdf_runtime_probe_evidence_bundle(tmp_path)

    assert report["ready"] is True
    assert report["capture_ready"] is False
    assert report["capture_status"] == "blocked"
    assert report["capture_error_count"] == 1


def test_phase639_missing_required_capture_file_blocks_bundle_readiness(
    tmp_path: Path,
):
    (tmp_path / "relation_state_mutation_events.jsonl").write_text(
        "{}\n",
        encoding="utf-8",
    )

    report = runtime.build_sdf_runtime_probe_evidence_bundle(tmp_path)

    assert report["ready"] is False
    assert report["capture_ready"] is False
    assert (
        "missing-required-capture-file:relation_state_mutation_timeline.json"
        in report["errors"]
    )
    assert Path(report["archive"]["path"]).is_file()


def test_phase639_rejects_wrong_timeline_format(tmp_path: Path):
    _write_capture(tmp_path)
    (tmp_path / "relation_state_mutation_timeline.json").write_text(
        json.dumps(
            {
                "format": "wrong",
                "ready": True,
                "errors": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = runtime.build_sdf_runtime_probe_evidence_bundle(tmp_path)

    assert report["ready"] is False
    assert "timeline-format-mismatch" in report["errors"]


def _load_cli_module():
    import importlib.util

    path = Path("tools/package_sdf_solver_capture.py")
    spec = importlib.util.spec_from_file_location(
        "phase639_package_sdf_solver_capture",
        path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase639_cli_packages_ready_capture(tmp_path: Path):
    _write_capture(tmp_path)
    output = tmp_path / "portable.zip"
    cli = _load_cli_module()

    assert cli.main([str(tmp_path), "-o", str(output)]) == 0
    assert output.is_file()


def test_phase639_cli_returns_two_for_incomplete_capture(tmp_path: Path):
    cli = _load_cli_module()

    assert cli.main([str(tmp_path)]) == 2
    assert (tmp_path / runtime.DEFAULT_ARCHIVE_NAME).is_file()
