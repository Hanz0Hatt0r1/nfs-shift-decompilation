from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _module():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "bootstrap_native_vertical_slice_from_capture_result.py"
    spec = importlib.util.spec_from_file_location(
        "bootstrap_native_vertical_slice_from_capture_result_tested",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _result(snapshot_path: str) -> dict:
    return {
        "format": "SHIFT.Phase642ExternalSamplerCaptureResult/1",
        "version": 1,
        "status": "ready",
        "ready": True,
        "capture_input_class_ready": True,
        "blocking_reasons": [],
        "source": {
            "capture_plan_format": "SHIFT.Phase641ExternalSamplerCapturePlan/1",
            "capture_plan_requirement_count": 1,
            # Deliberately stale/non-authoritative. Phase 652 must use the
            # result bundle's parent instead.
            "capture_root": "/old/machine/capture-output",
        },
        "summary": {
            "expectation_count": 1,
            "ready_expectation_count": 1,
            "requirement_count": 1,
        },
        "expectations": [{
            "stage": 7,
            "sampler_type": "sampler2D",
            "expected_d3d9_resource_type": "texture2d",
            "required_snapshot_path_count": 1,
            "binding_indices": [17],
            "ready": True,
            "candidate_event_count": 1,
            "ready_event_count": 1,
            "observations": [{
                "event_index": 42,
                "frame": 120,
                "texture_ptr": "0x1234",
                "stage": 7,
                "resource_type_name": "texture2d",
                "snapshot_status": "captured",
                "snapshot_paths": [snapshot_path],
                "resolved_snapshot_paths": ["/old/machine/capture-output/textures/s7.ppm"],
                "snapshot_path_resolution_modes": [
                    "capture-launcher-textures-relative"
                ],
                "cube_faces": [],
                "ready": True,
                "blocking_reasons": [],
            }],
        }],
        "requirements": [{
            "binding_index": 17,
            "requested_texture_stage": 7,
            "sampler": "shadowMap",
            "sampler_type": "sampler2D",
            "expected_d3d9_resource_type": "texture2d",
            "required_snapshot_path_count": 1,
            "capture_input_class_ready": True,
            "binding_identity_revalidated": False,
        }],
        "boundary": {
            "phase641_capture_plan_authoritative": True,
            "stage_and_resource_type_only_preflight": True,
            "snapshot_status_captured_required": True,
            "exact_snapshot_path_count_required": True,
            "snapshot_files_must_exist": True,
            "snapshot_basename_search_allowed": False,
            "cube_face_set_required": ["px", "nx", "py", "ny", "pz", "nz"],
            "binding_identity_claimed": False,
            "draw_identity_claimed": False,
            "scene_identity_claimed": False,
            "resource_identity_claimed": False,
            "scene_set_ready_claimed": False,
            "full_renderer_reattribution_required": True,
        },
    }


def _write_bundle(tmp_path: Path, *, raw_overrides: dict | None = None):
    root = tmp_path / "capture"
    textures = root / "textures"
    textures.mkdir(parents=True)
    (textures / "s7.ppm").write_bytes(b"P6\n1 1\n255\n\x01\x02\x03")
    raw_snapshot_path = r"Z:\\old\\capture\\textures\\s7.ppm"
    raw = {
        "event_index": 42,
        "frame": 120,
        "event": "set_texture",
        "texture_ptr": "0x1234",
        "stage": 7,
        "resource_type_name": "texture2d",
        "snapshot_status": "captured",
        "snapshot_paths": [raw_snapshot_path],
    }
    if raw_overrides:
        raw.update(raw_overrides)
    (root / "shift_d3d9_capture.jsonl").write_text(
        json.dumps(raw) + "\n",
        encoding="utf-8",
    )
    result_path = root / "external_sampler_capture_result.json"
    result_path.write_text(
        json.dumps(_result(raw_snapshot_path)),
        encoding="utf-8",
    )
    return root, result_path


def test_phase652_resolves_only_canonical_sibling_capture_bundle(tmp_path):
    mod = _module()
    root, result_path = _write_bundle(tmp_path)

    feedback = mod.resolve_capture_feedback_input(result_path)

    assert feedback["format"] == "SHIFT.Phase652ExternalSamplerCaptureFeedback/1"
    assert feedback["ready"] is True
    assert feedback["verified_expectation_count"] == 1
    assert feedback["capture_root"] == str(root.resolve())
    assert feedback["capture_jsonl"] == str(
        (root / "shift_d3d9_capture.jsonl").resolve()
    )
    assert feedback["boundary"]["stored_capture_root_is_selection_authority"] is False
    assert feedback["boundary"]["binding_identity_claimed"] is False
    assert feedback["boundary"]["full_renderer_reattribution_required"] is True


def test_phase652_rejects_tampered_raw_capture_after_ready_result(tmp_path):
    mod = _module()
    _root, result_path = _write_bundle(
        tmp_path,
        raw_overrides={"texture_ptr": "0x9999"},
    )

    with pytest.raises(ValueError, match="ready-observation-no-longer-matches-raw"):
        mod.resolve_capture_feedback_input(result_path)


def test_phase652_rejects_missing_canonical_sibling_capture(tmp_path):
    mod = _module()
    root = tmp_path / "capture"
    root.mkdir()
    result_path = root / "external_sampler_capture_result.json"
    result_path.write_text(
        json.dumps(_result(r"Z:\\old\\capture\\textures\\s7.ppm")),
        encoding="utf-8",
    )
    # A similarly named capture elsewhere must never be searched/admitted.
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "shift_d3d9_capture.jsonl").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="canonical-sibling-capture-missing"):
        mod.resolve_capture_feedback_input(result_path)


def test_phase652_rejects_blocked_or_semantically_promoted_result(tmp_path):
    mod = _module()
    _root, result_path = _write_bundle(tmp_path)
    value = json.loads(result_path.read_text(encoding="utf-8"))
    value["boundary"]["binding_identity_claimed"] = True
    result_path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValueError, match="boundary-mismatch:binding_identity_claimed"):
        mod.resolve_capture_feedback_input(result_path)


def test_phase652_delegates_to_existing_bootstrap_with_verified_capture(tmp_path, monkeypatch):
    mod = _module()
    root, result_path = _write_bundle(tmp_path)
    called = {}

    def fake_bootstrap(argv):
        called["argv"] = list(argv)
        return 7

    monkeypatch.setattr(mod, "bootstrap_main", fake_bootstrap)
    code = mod.main([
        str(result_path),
        "--",
        "Vehicles.zip",
        "Silverstone_Era3_.zip",
        "-o",
        "out/vertical",
        "--track",
        "Silverstone_Era3_GrandPrix",
        "--vehicle",
        "BMW_M3_E36",
        "--workspace-root",
        ".",
        "--renderer-pe-evidence",
        "out/shift_pe_evidence.json",
    ])

    assert code == 7
    argv = called["argv"]
    assert argv[-4:] == [
        "--renderer-capture-jsonl",
        str((root / "shift_d3d9_capture.jsonl").resolve()),
        "--renderer-capture-root",
        str(root.resolve()),
    ]
    assert "--renderer-pe-evidence" in argv


def test_phase652_refuses_manual_capture_path_override(tmp_path, monkeypatch):
    mod = _module()
    _root, result_path = _write_bundle(tmp_path)
    monkeypatch.setattr(mod, "bootstrap_main", lambda argv: 0)

    with pytest.raises(SystemExit) as exc:
        mod.main([
            str(result_path),
            "--",
            "Vehicles.zip",
            "-o",
            "out/vertical",
            "--track",
            "Silverstone_Era3_GrandPrix",
            "--vehicle",
            "BMW_M3_E36",
            "--workspace-root",
            ".",
            "--renderer-pe-evidence",
            "out/shift_pe_evidence.json",
            "--renderer-capture-root=/other/capture",
        ])
    assert exc.value.code == 2
