from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _module():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "phase642_external_sampler_capture_result.py"
    spec = importlib.util.spec_from_file_location(
        "phase642_external_sampler_capture_result_tested",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _requirement(
    *,
    binding_index: int,
    stage: int,
    sampler_type: str,
):
    if sampler_type == "sampler2D":
        resource_type = "texture2d"
        path_count = 1
        sampler = "shadowMap"
    else:
        resource_type = "cube_texture"
        path_count = 6
        sampler = "environmentMap"
    return {
        "binding_index": binding_index,
        "draw_order": binding_index,
        "register": stage,
        "sampler": sampler,
        "sampler_type": sampler_type,
        "reason": "snapshot-content-not-captured",
        "expected_d3d9_resource_type": resource_type,
        "required_snapshot_path_count": path_count,
        "requested_texture_stage": stage,
        "capture_frames": [100 + binding_index],
        "capture_draw_indices": [binding_index],
    }


def _handoff(requirements):
    rows = list(requirements)
    return {
        "format": "SHIFT.RendererNativeSceneHandoff/1",
        "scene_set_ready": False,
        "boundary": {
            "capture_observation_required": bool(rows),
            "capture_observation_requirement_count": len(rows),
        },
        "existing_capture_completion": {
            "runtime_evidence_required": rows,
        },
    }


def _line(**value) -> str:
    return json.dumps(value, separators=(",", ":")) + "\n"


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"P6\n1 1\n255\n\x00\x00\x00")


def test_preflight_accepts_exact_requested_2d_and_cube_snapshot_classes(tmp_path):
    mod = _module()
    handoff = _handoff([
        _requirement(binding_index=17, stage=7, sampler_type="sampler2D"),
        _requirement(binding_index=18, stage=3, sampler_type="samplerCube"),
    ])

    _touch(tmp_path / "textures" / "s7.ppm")
    cube_paths = []
    for face in mod.CUBE_FACES:
        _touch(tmp_path / "textures" / f"cube_face_{face}.ppm")
        cube_paths.append(f"Z:\\capture\\textures\\cube_face_{face}.ppm")

    lines = [
        _line(
            event_index=10,
            frame=200,
            event="set_texture",
            texture_ptr="0x1000",
            stage=7,
            resource_type_name="texture2d",
            snapshot_status="captured",
            snapshot_paths=["textures/s7.ppm"],
        ),
        _line(
            event_index=11,
            frame=200,
            event="set_texture",
            texture_ptr="0x2000",
            stage=3,
            resource_type_name="cube_texture",
            snapshot_status="captured",
            snapshot_paths=cube_paths,
        ),
    ]

    report = mod.build_capture_result(handoff, lines, capture_root=tmp_path)

    assert report["format"] == "SHIFT.Phase642ExternalSamplerCaptureResult/1"
    assert report["ready"] is True
    assert report["capture_input_class_ready"] is True
    assert report["blocking_reasons"] == []
    assert report["summary"]["expectation_count"] == 2
    assert report["summary"]["ready_expectation_count"] == 2
    assert all(row["capture_input_class_ready"] for row in report["requirements"])
    assert all(
        row["binding_identity_revalidated"] is False
        for row in report["requirements"]
    )
    assert report["boundary"]["binding_identity_claimed"] is False
    assert report["boundary"]["draw_identity_claimed"] is False
    assert report["boundary"]["scene_set_ready_claimed"] is False
    assert report["boundary"]["full_renderer_reattribution_required"] is True


def test_preflight_blocks_incomplete_cube_snapshot_faces(tmp_path):
    mod = _module()
    handoff = _handoff([
        _requirement(binding_index=18, stage=3, sampler_type="samplerCube"),
    ])

    paths = []
    for face in mod.CUBE_FACES[:-1]:
        _touch(tmp_path / "textures" / f"cube_face_{face}.ppm")
        paths.append(f"textures/cube_face_{face}.ppm")

    report = mod.build_capture_result(
        handoff,
        [_line(
            event_index=20,
            frame=201,
            event="set_texture",
            texture_ptr="0x2000",
            stage=3,
            resource_type_name="cube_texture",
            snapshot_status="captured",
            snapshot_paths=paths,
        )],
        capture_root=tmp_path,
    )

    assert report["ready"] is False
    assert any(
        reason.startswith(
            "phase642-capture-result:requested-input-not-observed:s3:cube_texture"
        )
        for reason in report["blocking_reasons"]
    )
    observation = report["expectations"][0]["observations"][0]
    assert observation["ready"] is False
    assert any(
        reason.startswith("snapshot-path-count:5!=6")
        for reason in observation["blocking_reasons"]
    )
    assert "cube-faces-missing:nz" in observation["blocking_reasons"]


def test_preflight_rejects_wrong_resource_type_for_requested_stage(tmp_path):
    mod = _module()
    handoff = _handoff([
        _requirement(binding_index=17, stage=7, sampler_type="sampler2D"),
    ])
    _touch(tmp_path / "textures" / "wrong.ppm")

    report = mod.build_capture_result(
        handoff,
        [_line(
            event_index=30,
            frame=202,
            event="set_texture",
            texture_ptr="0x3000",
            stage=7,
            resource_type_name="cube_texture",
            snapshot_status="captured",
            snapshot_paths=["textures/wrong.ppm"],
        )],
        capture_root=tmp_path,
    )

    assert report["ready"] is False
    assert report["expectations"][0]["candidate_event_count"] == 0
    assert any("s7:texture2d:sampler2D" in reason for reason in report["blocking_reasons"])


def test_preflight_requires_snapshot_files_to_exist(tmp_path):
    mod = _module()
    handoff = _handoff([
        _requirement(binding_index=17, stage=7, sampler_type="sampler2D"),
    ])

    report = mod.build_capture_result(
        handoff,
        [_line(
            event_index=40,
            frame=203,
            event="set_texture",
            texture_ptr="0x4000",
            stage=7,
            resource_type_name="texture2d",
            snapshot_status="captured",
            snapshot_paths=["textures/missing.ppm"],
        )],
        capture_root=tmp_path,
    )

    assert report["ready"] is False
    observation = report["expectations"][0]["observations"][0]
    assert "snapshot-path-unresolved:relative-path-not-found" in observation[
        "blocking_reasons"
    ]
    assert report["boundary"]["snapshot_basename_search_allowed"] is False


def test_preflight_blocks_malformed_capture_even_when_snapshot_class_exists(tmp_path):
    mod = _module()
    handoff = _handoff([
        _requirement(binding_index=17, stage=7, sampler_type="sampler2D"),
    ])
    _touch(tmp_path / "textures" / "s7.ppm")

    lines = [
        "{not-json}\n",
        _line(
            event_index=50,
            frame=204,
            event="set_texture",
            texture_ptr="0x5000",
            stage=7,
            resource_type_name="texture2d",
            snapshot_status="captured",
            snapshot_paths=["textures/s7.ppm"],
        ),
    ]
    report = mod.build_capture_result(handoff, lines, capture_root=tmp_path)

    assert report["ready"] is False
    assert report["summary"]["invalid_json_count"] == 1
    assert "phase642-capture-result:invalid-json-lines:1" in report[
        "blocking_reasons"
    ]
    assert report["expectations"][0]["ready_event_count"] == 1


def test_preflight_deduplicates_stage_class_without_claiming_binding_identity(tmp_path):
    mod = _module()
    handoff = _handoff([
        _requirement(binding_index=17, stage=7, sampler_type="sampler2D"),
        _requirement(binding_index=19, stage=7, sampler_type="sampler2D"),
    ])
    _touch(tmp_path / "textures" / "s7.ppm")

    report = mod.build_capture_result(
        handoff,
        [_line(
            event_index=60,
            frame=205,
            event="set_texture",
            texture_ptr="0x6000",
            stage=7,
            resource_type_name="texture2d",
            snapshot_status="captured",
            snapshot_paths=["textures/s7.ppm"],
        )],
        capture_root=tmp_path,
    )

    assert report["ready"] is True
    assert report["summary"]["expectation_count"] == 1
    assert report["summary"]["requirement_count"] == 2
    assert report["expectations"][0]["binding_indices"] == [17, 19]
    assert all(row["capture_input_class_ready"] for row in report["requirements"])
    assert all(
        row["binding_identity_revalidated"] is False
        for row in report["requirements"]
    )
