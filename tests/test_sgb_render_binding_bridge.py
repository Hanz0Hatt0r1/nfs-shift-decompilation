import json

from sgb_render_binding_bridge import (
    FORMAT,
    build_sgb_render_binding_bridge,
)


def _world(tx=10.0, ty=20.0, tz=30.0):
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        tx, ty, tz, 1.0,
    ]


def _binding(
    *,
    index=0,
    ready=True,
    resource="tracks/test/object.meb",
    world=None,
):
    return {
        "binding_index": index,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": [] if ready else ["numeric-world-matrix-not-ready"],
        "placement": {
            "placement_index": index,
            "mode": "flat-summ",
            "wrapper_chunk": "SUMM",
            "source_record_index": index,
            "identity": {"runtime_index": index},
            "spatial": {"scope": "flat-leaf"},
        },
        "object": {
            "object_path": [0],
            "wrapper": {
                "chunk": "SUMM",
                "source_record_index": index,
            },
            "resource_reference": resource,
            "transform_mode": "explicit-object-transform",
            "world_matrix": _world() if world is None and ready else world,
        },
        "scene_admission": {
            "resource_identity_ready": bool(resource),
            "numeric_world_matrix_ready": ready,
            "spatial_culling_ready": True,
            "admitted_to_generic_render_binding": ready,
            "draw_admission": False,
        },
    }


def _admission(*rows):
    bindings = list(rows or [_binding()])
    admitted = sum(row.get("ready") is True for row in bindings)
    return {
        "format": "SHIFT.SGBRenderBindingAdmission/1",
        "version": 1,
        "status": "ready" if admitted == len(bindings) else "blocked",
        "ready": admitted == len(bindings),
        "binding_count": len(bindings),
        "admitted_binding_count": admitted,
        "blocked_binding_count": len(bindings) - admitted,
        "bindings": bindings,
    }


def _write_ir(root):
    for name in ("meshes", "materials", "shaders", "raw"):
        (root / name).mkdir()

    mesh = {
        "format": "SHIFT.MEB",
        "vertex_count": 3,
        "triangle_count": 1,
        "vertex_properties": ["200"],
        "property_layouts": [{
            "id": "200",
            "name": "position",
            "stride": 12,
            "bytes": 36,
            "storage": "f32x3",
            "components": 3,
            "normalized": False,
        }],
        "primitives": [{
            "material": "tracks/test/object.bmt",
            "first_index": 0,
            "index_count": 3,
        }],
    }
    material = {
        "format": "SHIFT.BMT",
        "material": {
            "name": "OBJECT",
            "shader": "render/shaders/object.fx",
            "technique": "Default",
            "shaderparams": [],
        },
    }
    (root / "meshes/object.json").write_text(json.dumps(mesh))
    (root / "materials/object.json").write_text(json.dumps(material))
    (root / "shaders/object.json").write_text(json.dumps({"format": "HLSL"}))
    (root / "raw/object.fx").write_bytes(
        b"float4 main() : COLOR0 { return 1; }"
    )
    (root / "raw/mesh").write_bytes(b"")
    (root / "raw/material").write_bytes(b"")

    manifest = [
        {
            "archive": "TRACK.bff",
            "path": "tracks/test/object.meb",
            "output": "meshes/object.json",
            "raw": "raw/mesh",
            "sha256": "mesh-sha",
        },
        {
            "archive": "TRACK.bff",
            "path": "tracks/test/object.bmt",
            "output": "materials/object.json",
            "raw": "raw/material",
        },
        {
            "archive": "RENDER.bff",
            "path": "render/shaders/object.fx",
            "output": "shaders/object.json",
            "raw": "raw/object.fx",
        },
    ]
    (root / "manifest.json").write_text(json.dumps(manifest))


def test_admitted_sgb_meb_enters_generic_render_binding(tmp_path):
    _write_ir(tmp_path)
    matrix = _world(11.0, 22.0, 33.0)

    report = build_sgb_render_binding_bridge(
        _admission(_binding(world=matrix)),
        tmp_path,
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["direct_render_instance_count"] == 1
    assert report["resource_adapter_blocked_count"] == 0
    assert report["resolved_instance_count"] == 1
    assert report["unresolved_instance_count"] == 0

    generic = report["render_binding"]
    assert generic["format"] == "SHIFT.RenderBinding/1"
    assert generic["source_format"] == "SHIFT.SGBRenderBindingAdmission/1"
    assert generic["stats"]["resource_instances"] == 1
    assert generic["stats"]["resolved_resource_instances"] == 1
    assert len(generic["packets"]) == 1

    packet = generic["packets"][0]
    assert packet["world_matrix"] == matrix
    assert packet["mesh"]["ref"] == "tracks/test/object.meb"
    assert packet["mesh"]["resolved"]["resource_sha256"] == "mesh-sha"
    assert packet["scene_binding"]["admission_binding_index"] == 0
    assert packet["scene_binding"]["placement"]["mode"] == "flat-summ"


def test_blocked_scene_rows_are_not_promoted(tmp_path):
    _write_ir(tmp_path)
    blocked = _binding(index=1, ready=False, world=None)

    report = build_sgb_render_binding_bridge(
        _admission(_binding(index=0), blocked),
        tmp_path,
    )

    assert report["ready"] is True
    assert report["scene_admitted_instance_count"] == 1
    assert report["resolved_instance_count"] == 1
    assert report["render_binding"]["stats"]["resource_instances"] == 1
    assert report["skipped_bindings"] == [{
        "binding_index": 1,
        "reason": "not-scene-admitted",
        "blocking_reasons": ["numeric-world-matrix-not-ready"],
    }]


def test_missing_resource_stays_fail_closed(tmp_path):
    _write_ir(tmp_path)

    report = build_sgb_render_binding_bridge(
        _admission(_binding(resource="tracks/test/missing.meb")),
        tmp_path,
    )

    assert report["ready"] is False
    assert report["resolved_instance_count"] == 0
    assert report["unresolved_instance_count"] == 1
    assert (
        "binding-0:resource-resolution:resource-not-in-ir"
        in report["blocking_reasons"]
    )


def test_non_meb_scene_resource_is_not_guessed(tmp_path):
    _write_ir(tmp_path)
    scene_doc = tmp_path / "scene.json"
    scene_doc.write_text(json.dumps({"format": "SHIFT.VHFScene"}))
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    manifest.append({
        "archive": "TRACK.bff",
        "path": "tracks/test/object.vhf",
        "output": "scene.json",
        "raw": "raw/mesh",
    })
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    report = build_sgb_render_binding_bridge(
        _admission(_binding(resource="tracks/test/object.vhf")),
        tmp_path,
    )

    assert report["ready"] is False
    assert report["direct_render_instance_count"] == 0
    assert report["resource_adapter_blocked_count"] == 1
    assert (
        "binding-0:scene-resource:meshtype-adapter-unimplemented"
        in report["blocking_reasons"]
    )
    assert report["resource_adapter_blocked"][0]["factory_type"] == 0
    assert report["resource_adapter_blocked"][0]["factory_name"] == "MeshType"


def test_imb_scene_resource_is_classified_as_meshinst_and_stays_blocked(
    tmp_path,
):
    _write_ir(tmp_path)
    report = build_sgb_render_binding_bridge(
        _admission(
            _binding(resource="tracks/test/crowd_banner_01_body_loda.imb")
        ),
        tmp_path,
    )

    assert report["ready"] is False
    assert report["scene_admitted_instance_count"] == 1
    assert report["direct_render_instance_count"] == 0
    assert report["resource_adapter_blocked_count"] == 1
    assert (
        "binding-0:scene-resource:meshinst-adapter-unimplemented"
        in report["blocking_reasons"]
    )
    blocked = report["resource_adapter_blocked"][0]
    assert blocked["factory_type"] == 7
    assert blocked["factory_name"] == "MeshInst"


def test_mixed_meb_and_meshinst_preserves_ready_meb_packet(tmp_path):
    _write_ir(tmp_path)
    report = build_sgb_render_binding_bridge(
        _admission(
            _binding(index=0, resource="tracks/test/object.meb"),
            _binding(index=1, resource="tracks/test/crowd_banner.imb"),
        ),
        tmp_path,
    )

    assert report["ready"] is False
    assert report["scene_admitted_instance_count"] == 2
    assert report["direct_render_instance_count"] == 1
    assert report["resolved_instance_count"] == 1
    assert report["resource_adapter_blocked_count"] == 1
    assert len(report["render_binding"]["packets"]) == 1
    assert (
        report["render_binding"]["packets"][0]["scene_binding"][
            "admission_binding_index"
        ]
        == 0
    )
    assert report["resource_adapter_blocked"][0]["binding_index"] == 1


def test_no_admitted_rows_is_blocked(tmp_path):
    _write_ir(tmp_path)
    report = build_sgb_render_binding_bridge(
        _admission(_binding(ready=False, world=None)),
        tmp_path,
    )
    assert report["ready"] is False
    assert (
        "sgb-render-binding-bridge:no-admitted-bindings"
        in report["blocking_reasons"]
    )
    assert report["direct_render_instance_count"] == 0
    assert report["render_binding"]["stats"]["resource_instances"] == 0
