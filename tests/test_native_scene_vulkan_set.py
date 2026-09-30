import hashlib
import json
import struct

from imb_format import VERSION_0_4_0_0
from native_scene_bundle import build_native_scene_bundle
from native_scene_vulkan_set import (
    FORMAT,
    build_native_scene_vulkan_set,
)


def _sha(char):
    return char * 64


def _world(tx=10.0, ty=20.0, tz=30.0):
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        tx, ty, tz, 1.0,
    ]


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
    material = b"tracks/silverstone/object.bmt\x00"
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


def _dxt1_dds():
    values = (
        124, 0, 4, 4, 0, 0, 1,
        *([0] * 11),
        32, 0x4, struct.unpack("<I", b"DXT1")[0], 0,
        0, 0, 0, 0,
        0x1000, 0, 0, 0, 0,
    )
    return (
        b"DDS "
        + struct.pack("<31I", *values)
        + struct.pack("<HHI", 0xF800, 0x07E0, 0)
    )


def _runtime_provenance(resource_sha):
    return {
        "format": "SHIFT.RuntimeProvenDraw/1",
        "status": "proven",
        "binding_index": 17,
        "resource": {
            "source_kind": "IMB",
            "path": "tracks/silverstone/object.imb",
            "archive": "Silverstone_Era3_GrandPrix.bff",
            "sha256": resource_sha,
        },
        "primitive_index": 0,
        "draw_range": {
            "first_index": 0,
            "index_count": 3,
            "primitive_count": 1,
        },
        "shader_selection": {
            "selection_status": "unique",
            "selection_source": "runtime-admission",
            "runtime_selection_ready": True,
            "selected_variant": {
                "score": 100,
                "permutation_identity_sha256": _sha("5"),
            },
        },
        "boundary": {
            "render_backend_admission": False,
        },
    }


def _submesh(resource_sha, *, textured=False, external=False):
    row = {
        "primitive_index": 0,
        "first_index": 0,
        "index_count": 3,
        "runtime_provenance": _runtime_provenance(resource_sha),
        "render_state": {},
        "shader": {
            "vertex": "#version 450\nvoid main(){}\n",
            "pixel": "#version 450\nvoid main(){}\n",
            "source_payload_sha256": _sha("1"),
            "pair_sha256": _sha("2"),
            "vertex_sha256": _sha("3"),
            "pixel_sha256": _sha("4"),
            "permutation_identity": {
                "format": "SHIFT.ShaderPermutationIdentity/1",
                "identity_sha256": _sha("5"),
            },
        },
        "textures": [],
        "external_samplers": [],
        "uniforms": {
            "format": "SHIFT.MaterialUniformBinding/1",
            "bindings": [],
            "optimized_out_or_unreflected": [],
        },
        "constant_payload": None,
        "constant_commands": [],
    }
    if textured:
        row["textures"] = [{
            "sampler": "diffuseMap",
            "d3d9_sampler_register": 1,
            "resource_binding_id": "tb_test",
            "texture_id": "tex_test",
            "sampler_id": "smp_test",
            "sampler_state": {
                "format": "SHIFT.SamplerState/1",
                "ready": True,
                "blocking_reasons": [],
                "min_filter": "LINEAR",
                "mag_filter": "LINEAR",
                "mip_filter": "LINEAR",
                "address_u": "REPEAT",
                "address_v": "REPEAT",
                "address_w": "REPEAT",
            },
        }]
    if external:
        row["external_samplers"] = [{
            "sampler": "shadowMap",
            "sampler_type": "sampler2D",
            "d3d9_sampler_register": 7,
            "sampler_state": {
                "format": "SHIFT.SamplerState/1",
                "min_filter": "LINEAR",
                "mag_filter": "LINEAR",
                "address_u": "CLAMP_TO_EDGE",
                "address_v": "CLAMP_TO_EDGE",
            },
        }]
    return row


def _command(resource_sha, *, textured=False, external=False, tx=10.0):
    return {
        "format": "SHIFT.RenderCommand/1",
        "ready": True,
        "blocking_reasons": [],
        "validation": {
            "valid": True,
            "blocking_reasons": [],
        },
        "mesh": {
            "ref": "tracks/silverstone/object.imb",
            "vertex_count": 3,
            "triangle_count": 1,
            "vertex_layout": {
                "format": "SHIFT.VertexLayout/1",
                "buffer_stride": 12,
                "attributes": [{
                    "property_id": "200",
                    "usage": "POSITION",
                    "usage_index": 0,
                    "location": 0,
                    "offset": 0,
                    "stride": 12,
                    "element_size": 12,
                    "storage": "f32x3",
                    "components": 3,
                    "normalized": False,
                    "abi_status": "proven",
                }],
            },
            "attributes": [{
                "property_id": "200",
                "location": 0,
                "offset": 0,
                "stride": 12,
                "element_size": 12,
                "storage": "f32x3",
                "normalized": False,
                "abi_status": "proven",
            }],
            "attribute_setup": [],
        },
        "world_matrix": _world(tx=tx),
        "submeshes": [
            _submesh(
                resource_sha,
                textured=textured,
                external=external,
            )
        ],
        "runtime_proven_draw_count": 1,
        "resource_plan": {
            "format": "SHIFT.RenderResources/1",
            "texture_count": 1 if textured else 0,
            "sampler_count": 1 if textured else 0,
            "external_sampler_count": 1 if external else 0,
        },
    }


def _bridge(resource_sha, *, textured=False, external=False, tx=10.0):
    resources = {
        "format": "SHIFT.RenderResources/1",
        "textures": [],
        "samplers": [],
        "bindings": [],
        "unresolved": [],
        "stats": {
            "textures": 0,
            "samplers": 0,
            "bindings": 0,
            "gpu_ready_textures": 0,
            "gpu_ready_bindings": 0,
            "unresolved": 0,
        },
    }
    if textured:
        resources["textures"] = [{
            "id": "tex_test",
            "path": "tracks/silverstone/diffuse.dds",
            "sha256": _sha("d"),
            "gpu_ready": True,
            "blocking_reasons": [],
        }]
        resources["samplers"] = [{
            "id": "smp_test",
            "state": {
                "format": "SHIFT.SamplerState/1",
                "ready": True,
            },
        }]
        resources["bindings"] = [{
            "id": "tb_test",
            "texture_id": "tex_test",
            "sampler_id": "smp_test",
            "d3d9_sampler_register": 1,
            "gpu_ready": True,
            "blocking_reasons": [],
        }]
        resources["stats"].update({
            "textures": 1,
            "samplers": 1,
            "bindings": 1,
            "gpu_ready_textures": 1,
            "gpu_ready_bindings": 1,
        })

    command = _command(
        resource_sha,
        textured=textured,
        external=external,
        tx=tx,
    )
    return {
        "format": "SHIFT.SGBRenderBindingBridge/1",
        "ready": True,
        "runtime_shader_join": {
            "format": "SHIFT.IMBRuntimeRenderBindingJoin/1",
            "ready": True,
        },
        "render_binding": {
            "format": "SHIFT.RenderBinding/1",
            "runtime_shader_join": {
                "format": "SHIFT.IMBRuntimeRenderBindingJoin/1",
                "ready": True,
            },
            "packets": [{
                "scene": "tracks/silverstone/scene.sgb",
                "node": "GRANDSTAND",
                "node_type": "SGB_OBJECT",
                "scene_binding": {
                    "archive": "Silverstone_Era3_GrandPrix.bff",
                    "scene": "tracks/silverstone/scene.sgb",
                    "node": "GRANDSTAND",
                    "node_type": "SGB_OBJECT",
                    "binding_index": 123,
                },
                "mesh": {
                    "ref": "tracks/silverstone/object.imb",
                },
            }],
            "render_commands": [command],
            "resources": resources,
        },
    }


def _write_ir(tmp_path, *, textured=False):
    root = tmp_path / "ir"
    (root / "raw").mkdir(parents=True)
    imb = _imb_payload()
    imb_sha = hashlib.sha256(imb).hexdigest()
    (root / "raw/object.imb").write_bytes(imb)
    manifest = [{
        "archive": "Silverstone_Era3_GrandPrix.bff",
        "path": "tracks/silverstone/object.imb",
        "raw": "raw/object.imb",
        "sha256": imb_sha,
    }]
    if textured:
        dds = _dxt1_dds()
        (root / "raw/diffuse.dds").write_bytes(dds)
        manifest.append({
            "archive": "Silverstone_Era3_GrandPrix.bff",
            "path": "tracks/silverstone/diffuse.dds",
            "raw": "raw/diffuse.dds",
            "sha256": _sha("d"),
        })
    (root / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    return root, imb_sha


def _scene_and_bridge(
    tmp_path,
    *,
    textured=False,
    external=False,
    tx=10.0,
):
    root, imb_sha = _write_ir(tmp_path, textured=textured)
    bridge = _bridge(
        imb_sha,
        textured=textured,
        external=external,
        tx=tx,
    )
    scene = build_native_scene_bundle(bridge)
    assert scene["ready"] is True, scene
    return root, scene, bridge


def test_native_scene_vulkan_set_builds_ordered_runtime_proven_child(
    tmp_path,
):
    root, scene, bridge = _scene_and_bridge(tmp_path)

    report = build_native_scene_vulkan_set(
        scene,
        bridge,
        root,
        tmp_path / "vulkan-set",
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True, report["blocking_reasons"]
    assert report["draw_count"] == 1
    assert report["ready_draw_count"] == 1
    child = report["draws"][0]
    assert child["draw_order"] == 0
    assert child["ready"] is True
    assert child["bundle"]["format"] == "SHIFT.VulkanDrawBundle/1"
    assert child["bundle"]["runtime_provenance_gate_ready"] is True
    assert child["bundle"]["manifest_sha256"]
    assert child["bundle"]["world_transform_serialized"] is True
    assert child["bundle"]["world_transform"]["ready"] is True
    assert child["bundle"]["world_transform"]["format"] == (
        "SHIFT.VulkanWorldTransformPacket/1"
    )
    assert (tmp_path / "vulkan-set/draw_0000/geometry.svpk").is_file()
    assert (tmp_path / "vulkan-set/draw_0000/world_transform.svwt").is_file()
    assert (tmp_path / "vulkan-set/bundle_set_manifest.json").is_file()
    assert (
        tmp_path / "vulkan-set/bundle_set.paths"
    ).read_text().strip() == "draw_0000"
    assert report["boundary"]["bundle_paths_relative_to_set_root"] is True

    assert report["native_scene_submission"]["ready"] is False
    assert (
        "draw-0:scene-world-transform-not-executed"
        in report["native_scene_submission"]["blocking_reasons"]
    )
    assert report["boundary"]["world_transform_serialized"] is True
    assert report["boundary"]["world_transform_executed"] is False


def test_native_scene_vulkan_set_resolves_material_dds_from_ir(tmp_path):
    root, scene, bridge = _scene_and_bridge(
        tmp_path,
        textured=True,
    )

    report = build_native_scene_vulkan_set(
        scene,
        bridge,
        root,
        tmp_path / "vulkan-set",
    )

    assert report["ready"] is True, report["blocking_reasons"]
    child = report["draws"][0]
    assert child["ready"] is True
    assert child["texture_sources"][0]["register"] == 1
    assert child["texture_sources"][0]["path"] == (
        "tracks/silverstone/diffuse.dds"
    )
    assert (tmp_path / "vulkan-set/draw_0000/textures.svtp").is_file()


def test_native_scene_vulkan_set_rejects_tampered_scene_hash(tmp_path):
    root, scene, bridge = _scene_and_bridge(tmp_path)
    scene["draws"][0]["hashes"]["submesh_sha256"] = _sha("f")

    report = build_native_scene_vulkan_set(
        scene,
        bridge,
        root,
        tmp_path / "vulkan-set",
    )

    assert report["ready"] is False
    assert report["ready_draw_count"] == 0
    assert (
        "scene-hash:submesh-mismatch"
        in report["draws"][0]["blocking_reasons"]
    )


def test_native_scene_vulkan_set_rejects_wrong_exact_imb_sha(tmp_path):
    root, scene, bridge = _scene_and_bridge(tmp_path)
    scene["draws"][0]["resource"]["sha256"] = _sha("e")
    # Keep the draw identity internally self-consistent so exact IR identity,
    # not the Phase 578 hash guard, is the blocker under test.
    draw = scene["draws"][0]
    draw_identity = {
        "resource": draw["resource"],
        "primitive_index": draw["primitive_index"],
        "draw_range": draw["draw_range"],
        "shader_identity": draw["shader_identity"],
        "world_matrix": draw["world_matrix"],
    }
    draw["hashes"]["draw_identity_sha256"] = hashlib.sha256(
        json.dumps(
            draw_identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    report = build_native_scene_vulkan_set(
        scene,
        bridge,
        root,
        tmp_path / "vulkan-set",
    )

    assert report["ready"] is False
    assert any(
        reason.startswith("scene-identity:resource-sha256-mismatch")
        or reason.startswith("imb-resource:not-found")
        for reason in report["draws"][0]["blocking_reasons"]
    )


def test_native_scene_vulkan_set_keeps_external_sampler_fail_closed(
    tmp_path,
):
    root, scene, bridge = _scene_and_bridge(
        tmp_path,
        external=True,
    )

    report = build_native_scene_vulkan_set(
        scene,
        bridge,
        root,
        tmp_path / "vulkan-set",
    )

    assert report["ready"] is True
    assert report["native_scene_submission"]["ready"] is False
    assert any(
        "external-sampler:runtime-resource-unresolved:s7:sampler2D"
        in reason
        for reason in report["native_scene_submission"]["blocking_reasons"]
    )
    assert report["boundary"]["unresolved_external_samplers_promoted"] is False



def _write_external_snapshot_set(
    tmp_path,
    scene,
    *,
    draw_identity=None,
    sampler="shadowMap",
):
    reference = tmp_path / "shadow-s7.json"
    reference.write_text(
        json.dumps({
            "format": "SHIFT.ReferenceTexture/1",
            "source_format": "D3D9_CAPTURE_PPM",
            "width": 1,
            "height": 1,
            "pixel_format": "RGBA8",
            "pixels": [9, 8, 7, 255],
        }, sort_keys=True),
        encoding="utf-8",
    )
    reference_sha = hashlib.sha256(reference.read_bytes()).hexdigest()
    contract = tmp_path / "external-snapshots.json"
    contract.write_text(
        json.dumps({
            "format": "SHIFT.SceneExternalTextureSnapshotSet/1",
            "version": 1,
            "snapshots": [{
                "draw_order": 0,
                "scene_draw_identity_sha256": (
                    draw_identity
                    or scene["draws"][0]["hashes"][
                        "draw_identity_sha256"
                    ]
                ),
                "sampler": sampler,
                "sampler_type": "sampler2D",
                "d3d9_sampler_register": 7,
                "reference_texture_path": reference.name,
                "reference_texture_sha256": reference_sha,
                "source_provenance": {
                    "kind": "D3D9_CAPTURE_PPM",
                    "frame": 12,
                    "draw": 34,
                    "stage": 7,
                },
            }],
        }),
        encoding="utf-8",
    )
    return contract


def test_native_scene_vulkan_set_admits_exact_external_sampler2d_snapshot(
    tmp_path,
):
    root, scene, bridge = _scene_and_bridge(
        tmp_path,
        external=True,
    )
    snapshots = _write_external_snapshot_set(tmp_path, scene)

    report = build_native_scene_vulkan_set(
        scene,
        bridge,
        root,
        tmp_path / "vulkan-set",
        external_texture_snapshots=snapshots,
    )

    assert report["ready"] is True, report["blocking_reasons"]
    assert report["boundary"]["external_sampler2d_snapshots_admitted"] == 1
    assert report["source"]["external_texture_snapshot_set"]["ready"] is True
    child = report["draws"][0]
    assert child["external_runtime_blocking_reasons"] == []
    assert child["external_texture_sources"][0]["register"] == 7
    assert child["external_texture_sources"][0]["sampler"] == "shadowMap"
    assert child["external_texture_sources"][0]["source_provenance"][
        "kind"
    ] == "D3D9_CAPTURE_PPM"
    assert (tmp_path / "vulkan-set/draw_0000/textures.svtp").is_file()
    assert not any(
        "external-sampler:runtime-resource-unresolved:s7:sampler2D"
        in reason
        for reason in report["native_scene_submission"]["blocking_reasons"]
    )
    assert report["native_scene_submission"]["blocking_reasons"] == [
        "draw-0:scene-world-transform-not-executed"
    ]


def test_native_scene_vulkan_set_rejects_external_snapshot_draw_identity_mismatch(
    tmp_path,
):
    root, scene, bridge = _scene_and_bridge(
        tmp_path,
        external=True,
    )
    snapshots = _write_external_snapshot_set(
        tmp_path,
        scene,
        draw_identity=_sha("e"),
    )

    report = build_native_scene_vulkan_set(
        scene,
        bridge,
        root,
        tmp_path / "vulkan-set",
        external_texture_snapshots=snapshots,
    )

    assert report["ready"] is False
    assert any(
        "external-snapshot:s7:draw-identity-mismatch" in reason
        for reason in report["blocking_reasons"]
    )
    assert (
        "external-snapshot:unused:draw-0:s7"
        in report["blocking_reasons"]
    )


def test_native_scene_vulkan_set_rejects_external_snapshot_sampler_mismatch(
    tmp_path,
):
    root, scene, bridge = _scene_and_bridge(
        tmp_path,
        external=True,
    )
    snapshots = _write_external_snapshot_set(
        tmp_path,
        scene,
        sampler="otherShadowMap",
    )

    report = build_native_scene_vulkan_set(
        scene,
        bridge,
        root,
        tmp_path / "vulkan-set",
        external_texture_snapshots=snapshots,
    )

    assert report["ready"] is False
    assert any(
        "external-snapshot:s7:sampler-declaration-mismatch" in reason
        for reason in report["blocking_reasons"]
    )
    assert (
        "external-snapshot:unused:draw-0:s7"
        in report["blocking_reasons"]
    )


def test_native_scene_vulkan_set_requires_scene_and_bridge_contracts(
    tmp_path,
):
    root, scene, bridge = _scene_and_bridge(tmp_path)

    try:
        build_native_scene_vulkan_set(
            {"format": "SHIFT.Other/1"},
            bridge,
            root,
            tmp_path / "bad-scene",
        )
    except ValueError as error:
        assert "SHIFT.NativeSceneBundle/1" in str(error)
    else:
        raise AssertionError("invalid scene bundle format was accepted")

    try:
        build_native_scene_vulkan_set(
            scene,
            {"format": "SHIFT.Other/1"},
            root,
            tmp_path / "bad-bridge",
        )
    except ValueError as error:
        assert "SHIFT.SGBRenderBindingBridge/1" in str(error)
    else:
        raise AssertionError("invalid scene bridge format was accepted")
