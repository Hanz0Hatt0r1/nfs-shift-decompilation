import json
import struct

import render_pipeline
from imb_format import VERSION_0_4_0_0
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


def _imb_payload():
    data = bytearray(struct.pack("<IHH", VERSION_0_4_0_0, 0, 0))
    data += b"mesh\x00\xaa\xbb\xcc"
    data += struct.pack(
        "<III10f",
        3,
        1,
        1,
        0.0, 0.0, 0.0, 2.0,
        -1.0, -1.0, -1.0,
        1.0, 1.0, 1.0,
    )
    data += struct.pack("<III", 2, 0, 0)
    data += struct.pack(
        "<9f",
        0.0, 0.0, 0.0,
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
    )
    material = b"tracks/test/object.bmt\x00"
    data += material + b"\x00" * ((-len(material)) % 4)
    data += struct.pack("<II", 0, 1)
    data += struct.pack("<3H", 0, 1, 2)
    data += b"\x00\x00"
    data += struct.pack(
        "<HH10f",
        0,
        2,
        0.0, 0.0, 0.0, 2.0,
        -1.0, -1.0, -1.0,
        1.0, 1.0, 1.0,
    )
    return bytes(data)


def _imx_payload():
    return b"""<MESH Vertices="3" Streams="1" Buffers="1">
  <BOUNDSPHERE Centre="0 0 0" Radius="2"/>
  <AABBOX Min="-1 -1 -1" Max="1 1 1"/>
  <STREAM Type="F32Vec3" Usage="Position" Channel="0">
    <ITEM Pos="0 0 0"/>
    <ITEM Pos="1 0 0"/>
    <ITEM Pos="0 1 0"/>
  </STREAM>
  <INDEXBUFFER Type="TRIANGLE" Material="tracks/test/object.bmt" Entries="1">
    <TRIANGLE Indices="0 1 2"/>
  </INDEXBUFFER>
</MESH>
"""


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
    (root / "raw/object.imb").write_bytes(_imb_payload())
    (root / "raw/object.imx").write_bytes(_imx_payload())
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
            "path": "tracks/test/object.imb",
            "raw": "raw/object.imb",
            "sha256": "imb-sha",
        },
        {
            "archive": "TRACK.bff",
            "path": "tracks/test/object.imx",
            "raw": "raw/object.imx",
            "sha256": "imx-sha",
        },
        {
            "archive": "TRACK.bff",
            "path": "tracks/test/object.bmt",
            "output": "materials/object.json",
            "raw": "raw/material",
            "sha256": "bmt-sha",
        },
        {
            "archive": "RENDER.bff",
            "path": "render/shaders/object.fx",
            "output": "shaders/object.json",
            "raw": "raw/object.fx",
        },
    ]
    (root / "manifest.json").write_text(json.dumps(manifest))



def _runtime_shader_admission(*, sha="imb-sha", first_index=0):
    return {
        "format": "SHIFT.IMBRuntimeShaderAdmission/1",
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "admitted_bindings": [{
            "binding_index": 77,
            "archive": "TRACK.bff",
            "imb_path": "tracks/test/object.imb",
            "imb_sha256": sha,
            "primitive_index": 0,
            "draw_range": {
                "first_index": first_index,
                "index_count": 3,
                "primitive_count": 1,
            },
            "material_reference": "tracks/test/object.bmt",
            "bmt": "tracks/test/object.bmt",
            "bmt_sha256": "bmt-sha",
            "shader": "render/shaders/object.fx",
            "shader_family": "object",
            "selected_variant": {
                "score": 100,
                "permutation_identity_sha256": "1" * 64,
                "pair_byte_sha256": "2" * 64,
                "vertex_byte_sha256": "3" * 64,
                "pixel_byte_sha256": "4" * 64,
            },
            "shader_selection_admitted": True,
            "render_admission": False,
        }],
        "rejected_bindings": [],
    }


def _install_runtime_link_spy(monkeypatch):
    calls = []

    def fake_link_material(
        material,
        fx_source,
        *,
        fxo_candidates=(),
        texture_paths=(),
        vertex_properties=(),
        runtime_admission=None,
    ):
        calls.append(runtime_admission)
        admitted = runtime_admission is not None
        return {
            "format": "SHIFT.MaterialBinding/1",
            "material": material.get("name"),
            "shader": material.get("shader"),
            "selection_status": "unique" if admitted else "ambiguous",
            "selection_source": (
                "runtime-admission" if admitted else "static-ranking"
            ),
            "runtime_selection": (
                {
                    "status": "ready",
                    "ready": True,
                    "blocking_reasons": [],
                }
                if admitted
                else None
            ),
            "selected_fxo": None,
            "bindings": [],
            "shader_pair": None,
            "linked_shader_pair": None,
            "uniform_binding": None,
            "unresolved_textures": [],
        }

    monkeypatch.setattr(
        render_pipeline,
        "link_material",
        fake_link_material,
    )
    return calls

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


def test_imb_scene_resource_enters_generic_render_binding(tmp_path):
    _write_ir(tmp_path)
    report = build_sgb_render_binding_bridge(
        _admission(_binding(resource="tracks/test/object.imb")),
        tmp_path,
    )

    assert report["ready"] is True
    assert report["scene_admitted_instance_count"] == 1
    assert report["direct_render_instance_count"] == 1
    assert report["resource_adapter_blocked_count"] == 0
    assert report["resolved_instance_count"] == 1
    assert report["unresolved_instance_count"] == 0

    generic = report["render_binding"]
    assert generic["stats"]["resolved_resource_instances"] == 1
    packet = generic["packets"][0]
    assert packet["mesh"]["ref"] == "tracks/test/object.imb"
    assert packet["mesh"]["resolved"]["resource_sha256"] == "imb-sha"
    assert packet["mesh"]["source_kind"] == "IMB"
    assert packet["mesh"]["neutral_adapter_format"] == "SHIFT.IMBNeutralGeometry/1"
    assert packet["mesh"]["vertex_layout"]["source"] == "IMB"
    assert (
        packet["mesh"]["vertex_layout"]["source_adapter"]
        == "SHIFT.IMBNeutralGeometry/1"
    )


def test_imx_scene_resource_enters_generic_render_binding(tmp_path):
    _write_ir(tmp_path)
    report = build_sgb_render_binding_bridge(
        _admission(_binding(resource="tracks/test/object.imx")),
        tmp_path,
    )

    assert report["ready"] is True
    assert report["scene_admitted_instance_count"] == 1
    assert report["direct_render_instance_count"] == 1
    assert report["resource_adapter_blocked_count"] == 0
    assert report["resolved_instance_count"] == 1

    packet = report["render_binding"]["packets"][0]
    assert packet["mesh"]["ref"] == "tracks/test/object.imx"
    assert packet["mesh"]["resolved"]["resource_sha256"] == "imx-sha"
    assert packet["mesh"]["source_kind"] == "IMX"
    assert packet["mesh"]["neutral_adapter_format"] == (
        "SHIFT.IMXNeutralGeometry/1"
    )
    assert packet["mesh"]["vertex_layout"]["source"] == "IMX"
    assert packet["mesh"]["vertex_layout"]["source_adapter"] == (
        "SHIFT.IMXNeutralGeometry/1"
    )


def test_mixed_meb_and_imb_resolve_independently(tmp_path):
    _write_ir(tmp_path)
    report = build_sgb_render_binding_bridge(
        _admission(
            _binding(index=0, resource="tracks/test/object.meb"),
            _binding(index=1, resource="tracks/test/object.imb"),
        ),
        tmp_path,
    )

    assert report["ready"] is True
    assert report["scene_admitted_instance_count"] == 2
    assert report["direct_render_instance_count"] == 2
    assert report["resolved_instance_count"] == 2
    assert report["resource_adapter_blocked_count"] == 0
    packets = report["render_binding"]["packets"]
    assert len(packets) == 2
    assert packets[0]["scene_binding"]["admission_binding_index"] == 0
    assert packets[0]["mesh"]["source_kind"] == "MEB"
    assert packets[1]["scene_binding"]["admission_binding_index"] == 1
    assert packets[1]["mesh"]["source_kind"] == "IMB"


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


def test_runtime_shader_admission_joins_exact_imb_primitive(
    tmp_path,
    monkeypatch,
):
    _write_ir(tmp_path)
    calls = _install_runtime_link_spy(monkeypatch)

    report = build_sgb_render_binding_bridge(
        _admission(_binding(resource="tracks/test/object.imb")),
        tmp_path,
        runtime_shader_admission=_runtime_shader_admission(),
    )

    assert report["ready"] is True
    join = report["runtime_shader_join"]
    assert join["ready"] is True
    assert join["supplied_admission_count"] == 1
    assert join["applied_admission_count"] == 1
    assert join["application_count"] == 1
    assert calls[0]["binding_index"] == 77

    packet = report["render_binding"]["packets"][0]
    submesh = packet["submeshes"][0]
    assert submesh["primitive_index"] == 0
    assert submesh["runtime_shader_admission"] == {
        "binding_index": 77,
        "shader_selection_admitted": True,
        "selection_status": "unique",
        "selection_source": "runtime-admission",
    }
    assert submesh["material"]["selection_source"] == "runtime-admission"


def test_runtime_shader_admission_mismatch_is_fail_closed(
    tmp_path,
    monkeypatch,
):
    _write_ir(tmp_path)
    calls = _install_runtime_link_spy(monkeypatch)

    report = build_sgb_render_binding_bridge(
        _admission(_binding(resource="tracks/test/object.imb")),
        tmp_path,
        runtime_shader_admission=_runtime_shader_admission(
            sha="wrong-imb-sha"
        ),
    )

    assert report["ready"] is False
    join = report["runtime_shader_join"]
    assert join["ready"] is False
    assert join["applied_admission_count"] == 0
    assert join["unmatched_binding_indices"] == [77]
    assert (
        "runtime-shader-join:"
        "runtime-shader-admission:binding-77:not-applied"
        in report["blocking_reasons"]
    )
    assert calls == [None]


def test_runtime_shader_admission_is_not_applied_to_meb(
    tmp_path,
    monkeypatch,
):
    _write_ir(tmp_path)
    calls = _install_runtime_link_spy(monkeypatch)

    report = build_sgb_render_binding_bridge(
        _admission(
            _binding(index=0, resource="tracks/test/object.meb"),
            _binding(index=1, resource="tracks/test/object.imb"),
        ),
        tmp_path,
        runtime_shader_admission=_runtime_shader_admission(),
    )

    assert report["ready"] is True
    assert len(calls) == 2
    assert calls[0] is None
    assert calls[1]["binding_index"] == 77
    assert report["runtime_shader_join"]["application_count"] == 1


def test_one_resource_shader_admission_reuses_across_scene_instances(
    tmp_path,
    monkeypatch,
):
    _write_ir(tmp_path)
    calls = _install_runtime_link_spy(monkeypatch)

    report = build_sgb_render_binding_bridge(
        _admission(
            _binding(index=0, resource="tracks/test/object.imb"),
            _binding(index=1, resource="tracks/test/object.imb"),
        ),
        tmp_path,
        runtime_shader_admission=_runtime_shader_admission(),
    )

    assert report["ready"] is True
    assert len(calls) == 2
    assert all(call["binding_index"] == 77 for call in calls)
    join = report["runtime_shader_join"]
    assert join["applied_admission_count"] == 1
    assert join["application_count"] == 2
    assert join["application_counts"] == {"77": 2}


def test_empty_runtime_shader_admission_report_is_blocked(
    tmp_path,
    monkeypatch,
):
    _write_ir(tmp_path)
    _install_runtime_link_spy(monkeypatch)
    empty = {
        "format": "SHIFT.IMBRuntimeShaderAdmission/1",
        "status": "not-admitted",
        "ready": False,
        "admitted_bindings": [],
        "rejected_bindings": [],
    }

    report = build_sgb_render_binding_bridge(
        _admission(_binding(resource="tracks/test/object.imb")),
        tmp_path,
        runtime_shader_admission=empty,
    )

    assert report["ready"] is False
    assert report["runtime_shader_join"]["ready"] is False
    assert (
        "runtime-shader-join:"
        "runtime-shader-admission:no-admitted-bindings"
        in report["blocking_reasons"]
    )
