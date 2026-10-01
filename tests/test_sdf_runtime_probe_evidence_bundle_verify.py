import json
import zipfile
from pathlib import Path

import sdf_runtime_probe_evidence_bundle as builder
import sdf_runtime_probe_evidence_bundle_verify as runtime


def _write_capture(root: Path, *, timeline_ready: bool = True) -> Path:
    (root / "relation_state_mutation_events.jsonl").write_text(
        '{"format":"SHIFT.ConstraintRelationStateMutationCaptureRuntime/1"}\n',
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
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "frame_entry_000001.json").write_text(
        '{"frame_index":1,"runtime_event_sequence":1}\n',
        encoding="utf-8",
    )
    return Path(
        builder.build_sdf_runtime_probe_evidence_bundle(root)["archive"]["path"]
    )


def _rewrite_archive(
    source: Path,
    target: Path,
    mutate,
) -> None:
    with zipfile.ZipFile(source, "r") as src:
        rows = [(info, src.read(info.filename)) for info in src.infolist()]
    with zipfile.ZipFile(target, "w") as dst:
        for info, data in rows:
            dst.writestr(info, mutate(info.filename, data))


def _fixed_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def test_phase640_verifies_builder_output(tmp_path: Path):
    archive = _write_capture(tmp_path)

    report = runtime.verify_sdf_runtime_probe_evidence_bundle(archive)

    assert report["ready"] is True
    assert report["package_ready"] is True
    assert report["capture_ready"] is True
    assert report["evidence_ready"] is True
    assert report["file_count"] == 3
    assert len(report["archive"]["sha256"]) == 64
    assert report["errors"] == []


def test_phase640_integrity_can_be_ready_while_capture_stays_blocked(
    tmp_path: Path,
):
    archive = _write_capture(tmp_path, timeline_ready=False)

    report = runtime.verify_sdf_runtime_probe_evidence_bundle(archive)

    assert report["ready"] is True
    assert report["package_ready"] is True
    assert report["capture_ready"] is False
    assert report["evidence_ready"] is False


def test_phase640_detects_payload_tampering(tmp_path: Path):
    archive = _write_capture(tmp_path)
    tampered = tmp_path / "tampered.zip"

    _rewrite_archive(
        archive,
        tampered,
        lambda name, data: (
            data + b"tampered"
            if name == "relation_state_mutation_events.jsonl"
            else data
        ),
    )

    report = runtime.verify_sdf_runtime_probe_evidence_bundle(tampered)

    assert report["ready"] is False
    assert (
        "file-size-mismatch:relation_state_mutation_events.jsonl"
        in report["errors"]
    )
    assert (
        "file-sha256-mismatch:relation_state_mutation_events.jsonl"
        in report["errors"]
    )


def test_phase640_detects_manifest_timeline_readiness_forgery(
    tmp_path: Path,
):
    archive = _write_capture(tmp_path, timeline_ready=False)
    forged = tmp_path / "forged.zip"

    def mutate(name, data):
        if name != builder.MANIFEST_NAME:
            return data
        manifest = json.loads(data.decode("utf-8"))
        manifest["capture_ready"] = True
        return (
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")

    _rewrite_archive(archive, forged, mutate)

    report = runtime.verify_sdf_runtime_probe_evidence_bundle(forged)

    assert report["ready"] is False
    assert "manifest-timeline-readiness-mismatch" in report["errors"]


def test_phase640_rejects_extra_executable_entry(tmp_path: Path):
    archive = _write_capture(tmp_path)
    extra = tmp_path / "extra.zip"

    with zipfile.ZipFile(archive, "r") as src:
        rows = [(info, src.read(info.filename)) for info in src.infolist()]
    with zipfile.ZipFile(extra, "w") as dst:
        for info, data in rows:
            dst.writestr(info, data)
        dst.writestr(_fixed_info("SHIFT.exe"), b"not-allowed")

    report = runtime.verify_sdf_runtime_probe_evidence_bundle(extra)

    assert report["ready"] is False
    assert "archive-extra-entry:SHIFT.exe" in report["errors"]
    assert "archive-entry-order-mismatch" in report["errors"]


def test_phase640_rejects_path_traversal_entry(tmp_path: Path):
    archive = _write_capture(tmp_path)
    unsafe = tmp_path / "unsafe.zip"

    with zipfile.ZipFile(archive, "r") as src:
        rows = [(info, src.read(info.filename)) for info in src.infolist()]
    with zipfile.ZipFile(unsafe, "w") as dst:
        for info, data in rows:
            dst.writestr(info, data)
        dst.writestr(_fixed_info("../SHIFT.exe"), b"unsafe")

    report = runtime.verify_sdf_runtime_probe_evidence_bundle(unsafe)

    assert report["ready"] is False
    assert "unsafe-zip-entry:../SHIFT.exe" in report["errors"]
    assert "archive-extra-entry:../SHIFT.exe" in report["errors"]


def test_phase640_rejects_non_deterministic_zip_metadata(tmp_path: Path):
    archive = _write_capture(tmp_path)
    changed = tmp_path / "metadata.zip"

    with zipfile.ZipFile(archive, "r") as src:
        rows = [(info, src.read(info.filename)) for info in src.infolist()]
    with zipfile.ZipFile(changed, "w") as dst:
        for index, (info, data) in enumerate(rows):
            if index == 1:
                info.date_time = (2026, 1, 1, 0, 0, 0)
            dst.writestr(info, data)

    report = runtime.verify_sdf_runtime_probe_evidence_bundle(changed)

    assert report["ready"] is False
    assert any(
        error.startswith("entry-timestamp-mismatch:")
        for error in report["errors"]
    )


def test_phase640_missing_archive_fails_closed(tmp_path: Path):
    report = runtime.verify_sdf_runtime_probe_evidence_bundle(
        tmp_path / "missing.zip"
    )

    assert report["ready"] is False
    assert report["evidence_ready"] is False
    assert report["errors"][0].startswith("archive-missing:")


def _load_cli_module():
    import importlib.util

    path = Path("tools/verify_sdf_solver_capture_bundle.py")
    spec = importlib.util.spec_from_file_location(
        "phase640_verify_sdf_solver_capture_bundle",
        path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase640_cli_accepts_valid_bundle(tmp_path: Path):
    archive = _write_capture(tmp_path)
    cli = _load_cli_module()

    assert cli.main([str(archive)]) == 0


def test_phase640_cli_returns_two_for_invalid_bundle(tmp_path: Path):
    path = tmp_path / "bad.zip"
    path.write_bytes(b"not-a-zip")
    cli = _load_cli_module()

    assert cli.main([str(path)]) == 2
