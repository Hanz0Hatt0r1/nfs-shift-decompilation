import hashlib
import json
import zipfile
from pathlib import Path

import relation_state_mutation_timeline_correlation_runtime as timeline_runtime
import sdf_runtime_probe_evidence_bundle as builder
import sdf_runtime_probe_evidence_bundle_replay as runtime
import sdf_runtime_probe_evidence_bundle_verify as verifier


def _write_raw_capture(root: Path, *, blocked: bool = False) -> Path:
    mutation = {
        "format": "SHIFT.ConstraintRelationStateMutationCaptureRuntime/1",
        "ready": True,
        "callsite_ready": not blocked,
        "runtime_event_sequence": 2,
        "frame_index": 1,
        "frame_entry_runtime_event_sequence": 1,
        "component_slot": 0,
        "component_slot_name": "FL",
        "source_branch": "wheel-rear-axle-pair",
        "caller_return_address": 0x0079A5C1,
        "caller_classification": {
            "format": "SHIFT.ConstraintRelationStateMutationCallsite/1",
            "ready": not blocked,
            "known_callsite": not blocked,
            "kind": (
                "unclassified"
                if blocked
                else "runtime-threshold-slot"
            ),
            "source_function": None if blocked else "FUN_0079a050",
        },
    }
    (root / "relation_state_mutation_events.jsonl").write_text(
        json.dumps(mutation) + "\n",
        encoding="utf-8",
    )
    (root / "frame_entry_000001.json").write_text(
        json.dumps(
            {
                "runtime_event_sequence": 1,
                "frame_index": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "scalar_reset_events.jsonl").write_text(
        json.dumps(
            {
                "runtime_event_sequence": 3,
                "frame_index": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    timeline = (
        timeline_runtime.analyze_relation_state_mutation_capture_directory(
            root
        )
    )
    assert "capture_directory" not in timeline
    (root / "relation_state_mutation_timeline.json").write_text(
        json.dumps(
            timeline,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return Path(
        builder.build_sdf_runtime_probe_evidence_bundle(root)["archive"]["path"]
    )


def _rewrite_timeline_and_manifest(
    source: Path,
    target: Path,
) -> None:
    with zipfile.ZipFile(source, "r") as src:
        infos = src.infolist()
        payloads = {
            info.filename: src.read(info.filename)
            for info in infos
        }

    timeline = json.loads(
        payloads["relation_state_mutation_timeline.json"].decode("utf-8")
    )
    timeline["summary"]["runtime_threshold_mutation_count"] += 7
    timeline_bytes = (
        json.dumps(
            timeline,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    payloads["relation_state_mutation_timeline.json"] = timeline_bytes

    manifest = json.loads(
        payloads[builder.MANIFEST_NAME].decode("utf-8")
    )
    for row in manifest["files"]:
        if row["path"] == "relation_state_mutation_timeline.json":
            row["size"] = len(timeline_bytes)
            row["sha256"] = hashlib.sha256(timeline_bytes).hexdigest()
    payloads[builder.MANIFEST_NAME] = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    with zipfile.ZipFile(target, "w") as dst:
        for info in infos:
            dst.writestr(info, payloads[info.filename])


def test_phase641_replays_valid_bundle_exactly(tmp_path: Path):
    archive = _write_raw_capture(tmp_path)

    report = runtime.replay_sdf_runtime_probe_evidence_bundle(archive)

    assert report["ready"] is True
    assert report["verification_ready"] is True
    assert report["timeline_match"] is True
    assert report["capture_ready"] is True
    assert report["evidence_ready"] is True
    assert (
        report["embedded_timeline_sha256"]
        == report["recomputed_timeline_sha256"]
    )


def test_phase641_blocked_capture_can_replay_without_becoming_evidence_ready(
    tmp_path: Path,
):
    archive = _write_raw_capture(tmp_path, blocked=True)

    report = runtime.replay_sdf_runtime_probe_evidence_bundle(archive)

    assert report["ready"] is True
    assert report["timeline_match"] is True
    assert report["capture_ready"] is False
    assert report["evidence_ready"] is False


def test_phase641_detects_semantic_timeline_tamper_even_after_manifest_rehash(
    tmp_path: Path,
):
    archive = _write_raw_capture(tmp_path)
    forged = tmp_path / "forged.zip"
    _rewrite_timeline_and_manifest(archive, forged)

    integrity = verifier.verify_sdf_runtime_probe_evidence_bundle(forged)
    assert integrity["ready"] is True
    assert integrity["evidence_ready"] is True

    replay = runtime.replay_sdf_runtime_probe_evidence_bundle(forged)
    assert replay["ready"] is False
    assert replay["timeline_match"] is False
    assert "embedded-timeline-replay-mismatch" in replay["errors"]
    assert (
        replay["embedded_timeline_sha256"]
        != replay["recomputed_timeline_sha256"]
    )


def test_phase641_rejects_bundle_that_fails_phase640_verification(
    tmp_path: Path,
):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not-a-zip")

    report = runtime.replay_sdf_runtime_probe_evidence_bundle(bad)

    assert report["ready"] is False
    assert report["verification_ready"] is False
    assert report["timeline_match"] is False
    assert report["errors"]


def _load_cli_module():
    import importlib.util

    path = Path("tools/replay_sdf_solver_capture_bundle.py")
    spec = importlib.util.spec_from_file_location(
        "phase641_replay_sdf_solver_capture_bundle",
        path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase641_cli_accepts_reproducible_bundle(tmp_path: Path):
    archive = _write_raw_capture(tmp_path)
    cli = _load_cli_module()

    assert cli.main([str(archive)]) == 0


def test_phase641_cli_returns_two_for_replay_mismatch(tmp_path: Path):
    archive = _write_raw_capture(tmp_path)
    forged = tmp_path / "forged.zip"
    _rewrite_timeline_and_manifest(archive, forged)
    cli = _load_cli_module()

    assert cli.main([str(forged)]) == 2
