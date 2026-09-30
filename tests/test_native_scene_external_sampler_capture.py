from pathlib import Path

from native_scene_external_sampler_capture import (
    FORMAT,
    build_scene_external_sampler_capture_adapter,
)
from native_scene_external_sampler_snapshots import (
    validate_external_sampler_snapshot_contract,
)


def _sha(char):
    return char * 64


def _ppm(path: Path, rgb=(9, 8, 7)):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"P6\n1 1\n255\n" + bytes(rgb)
    )


def _scene_draw(*, binding_index=17, draw_order=0, tx=1.0):
    world = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        tx, 0.0, 0.0, 1.0,
    ]
    return {
        "draw_order": draw_order,
        "command_index": draw_order,
        "submesh_index": 0,
        "binding_index": binding_index,
        "primitive_index": 3,
        "resource": {
            "source_kind": "IMB",
            "archive": "Silverstone_Era3_GrandPrix.bff",
            "path": "tracks/silverstone/object.imb",
            "sha256": _sha("a"),
        },
        "world_matrix": world,
        "hashes": {
            "draw_identity_sha256": (
                _sha("d") if draw_order == 0 else _sha("e")
            ),
        },
    }


def _scene_bundle(*draws):
    return {
        "format": "SHIFT.NativeSceneBundle/1",
        "ready": True,
        "draws": list(draws),
    }


def _external_submesh():
    return {
        "external_samplers": [{
            "sampler": "shadowMap",
            "sampler_type": "sampler2D",
            "d3d9_sampler_register": 7,
        }],
    }


def _bridge(draw_count=1):
    return {
        "format": "SHIFT.SGBRenderBindingBridge/1",
        "ready": True,
        "render_binding": {
            "format": "SHIFT.RenderBinding/1",
            "render_commands": [
                {"submeshes": [_external_submesh()]}
                for _ in range(draw_count)
            ],
        },
    }


def _pipeline(snapshot_path, *, observations=1):
    rows = []
    for draw_index in range(observations):
        rows.append({
            "binding_index": 17,
            "frame": 12,
            "draw_index": draw_index,
            "status": "observed",
            "blocking_reasons": [],
            "active_texture_bindings": [{
                "stage": 7,
                "texture_ptr": f"0x70{draw_index}",
                "resource_creation_status": "observed",
                "resource_creation": {
                    "resource_type": "texture2d",
                    "texture_ptr": f"0x70{draw_index}",
                    "width": 1,
                    "height": 1,
                },
                "snapshot_status": "captured",
                "snapshot_paths": [str(snapshot_path)],
            }],
        })
    return {
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "pipeline_ready": True,
        "resource_results": [{
            "resource_index": 0,
            "attributed_texture_observations": rows,
        }],
    }


def test_capture_adapter_builds_phase589_contract_from_exact_ppm(tmp_path):
    ppm = tmp_path / "textures" / "shadow.ppm"
    _ppm(ppm)

    report = build_scene_external_sampler_capture_adapter(
        _scene_bundle(_scene_draw()),
        _bridge(),
        _pipeline("textures/shadow.ppm"),
        capture_root=tmp_path,
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True, report["blocking_reasons"]
    assert report["required_external_sampler2d_count"] == 1
    assert report["snapshot_count"] == 1
    assert report["rows"][0]["candidate_observation_count"] == 1

    contract = report["snapshot_contract"]
    validated = validate_external_sampler_snapshot_contract(contract)
    assert validated["ready"] is True
    snapshot = validated["snapshots"][0]
    assert snapshot["draw_identity_sha256"] == _sha("d")
    assert snapshot["resource"]["sha256"] == _sha("a")
    assert snapshot["primitive_index"] == 3
    assert snapshot["d3d9_sampler_register"] == 7
    assert snapshot["texture"]["source_format"] == "D3D9_CAPTURE_PPM"
    assert snapshot["texture"]["pixels"] == [9, 8, 7, 255]
    assert (
        snapshot["provenance"]["source_kind"]
        == "D3D9_CAPTURE_PPM"
    )
    assert snapshot["provenance"]["capture_frame"] == 12
    assert snapshot["provenance"]["capture_draw_index"] == 0


def test_capture_adapter_blocks_multiple_runtime_observations(tmp_path):
    ppm = tmp_path / "textures" / "shadow.ppm"
    _ppm(ppm)

    report = build_scene_external_sampler_capture_adapter(
        _scene_bundle(_scene_draw()),
        _bridge(),
        _pipeline("textures/shadow.ppm", observations=2),
        capture_root=tmp_path,
    )

    assert report["ready"] is False
    assert report["snapshot_contract"] is None
    assert any(
        "capture-observation-count:2" in reason
        for reason in report["blocking_reasons"]
    )


def test_capture_adapter_blocks_reused_binding_across_scene_instances(
    tmp_path,
):
    ppm = tmp_path / "textures" / "shadow.ppm"
    _ppm(ppm)

    report = build_scene_external_sampler_capture_adapter(
        _scene_bundle(
            _scene_draw(draw_order=0, tx=1.0),
            _scene_draw(draw_order=1, tx=2.0),
        ),
        _bridge(draw_count=2),
        _pipeline("textures/shadow.ppm"),
        capture_root=tmp_path,
    )

    assert report["ready"] is False
    assert report["snapshot_contract"] is None
    assert any(
        "scene-draw-ambiguous:2" in reason
        for reason in report["blocking_reasons"]
    )


def test_capture_adapter_does_not_promote_material_textures(tmp_path):
    ppm = tmp_path / "textures" / "shadow.ppm"
    _ppm(ppm)
    bridge = _bridge()
    bridge["render_binding"]["render_commands"][0]["submeshes"][0] = {
        "external_samplers": [],
        "textures": [{
            "sampler": "diffuseMap",
            "d3d9_sampler_register": 7,
        }],
    }

    report = build_scene_external_sampler_capture_adapter(
        _scene_bundle(_scene_draw()),
        bridge,
        _pipeline("textures/shadow.ppm"),
        capture_root=tmp_path,
    )

    assert report["ready"] is True
    assert report["status"] == "not-needed"
    assert report["snapshot_count"] == 0
    assert report["snapshot_contract"]["snapshots"] == []
    assert report["boundary"]["material_textures_promoted"] is False


def test_capture_adapter_requires_observed_texture2d_creation(tmp_path):
    ppm = tmp_path / "textures" / "shadow.ppm"
    _ppm(ppm)
    pipeline = _pipeline("textures/shadow.ppm")
    binding = pipeline["resource_results"][0][
        "attributed_texture_observations"
    ][0]["active_texture_bindings"][0]
    binding["resource_creation"]["resource_type"] = "cube_texture"

    report = build_scene_external_sampler_capture_adapter(
        _scene_bundle(_scene_draw()),
        _bridge(),
        pipeline,
        capture_root=tmp_path,
    )

    assert report["ready"] is False
    assert any(
        "capture-observation-count:0" in reason
        for reason in report["blocking_reasons"]
    )


def test_capture_adapter_remaps_windows_path_by_unique_basename(
    tmp_path,
):
    ppm = tmp_path / "textures" / "shadow.ppm"
    _ppm(ppm)

    report = build_scene_external_sampler_capture_adapter(
        _scene_bundle(_scene_draw()),
        _bridge(),
        _pipeline(r"C:\capture\textures\shadow.ppm"),
        capture_root=tmp_path,
    )

    assert report["ready"] is True
    provenance = report["snapshot_contract"]["snapshots"][0][
        "provenance"
    ]
    assert provenance["path_resolution"] == (
        "capture-root-unique-basename"
    )
    assert provenance["resolved_snapshot_path"].endswith(
        "textures/shadow.ppm"
    )
