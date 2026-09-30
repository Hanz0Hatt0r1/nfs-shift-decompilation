import hashlib
import json

import native_scene_bundle as scene_bundle


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _world(tx=0.0):
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        tx, 0.0, 0.0, 1.0,
    ]


def _packet(resource_sha, *, admitted=True, tx=0.0):
    return {
        "scene": "tracks/silverstone/scene.sgb",
        "node": "OBJECT",
        "world_matrix": _world(tx),
        "mesh": {
            "ref": "tracks/silverstone/object.imb",
            "resolved": {
                "path": "tracks/silverstone/object.imb",
                "archive": "TRACK.bff",
                "resource_sha256": resource_sha,
            },
            "source_kind": "IMB",
        },
        "submeshes": [{
            "primitive_index": 0,
            "first_index": 0,
            "index_count": 3,
            "runtime_shader_admission": (
                {
                    "binding_index": 77,
                    "shader_selection_admitted": True,
                    "selection_status": "unique",
                    "selection_source": "runtime-admission",
                }
                if admitted
                else None
            ),
        }],
    }


def _runtime_provenance(resource_sha, *, tx=0.0):
    return {
        "format": "SHIFT.RuntimeProvenDraw/1",
        "status": "proven",
        "binding_index": 77,
        "resource": {
            "source_kind": "IMB",
            "path": "tracks/silverstone/object.imb",
            "archive": "TRACK.bff",
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
                "permutation_identity_sha256": "b" * 64,
            },
        },
        "boundary": {
            "claim": "runtime-proven shader selection on exact IMB primitive",
            "render_backend_admission": False,
        },
    }


def _command(resource_sha, *, proven=True, tx=0.0):
    return {
        "format": "SHIFT.RenderCommand/1",
        "ready": True,
        "blocking_reasons": [],
        "validation": {"valid": True, "blocking_reasons": []},
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
                    "storage": "FLOAT32x3",
                    "android": "FLOAT32x3",
                    "components": 3,
                    "normalized": False,
                    "element_size": 12,
                    "abi_status": "proven",
                }],
            },
        },
        "world_matrix": _world(tx),
        "runtime_proven_draw_count": 1 if proven else 0,
        "submeshes": [{
            "primitive_index": 0,
            "first_index": 0,
            "index_count": 3,
            "runtime_provenance": (
                _runtime_provenance(resource_sha, tx=tx)
                if proven else None
            ),
            "shader": {
                "vertex": "#version 450\nvoid main(){}",
                "pixel": (
                    "#version 450\nlayout(location=0) out vec4 o;"
                    "void main(){o=vec4(1.0);}"
                ),
                "vulkan_vertex_glsl": "#version 450\nvoid main(){}",
                "vulkan_pixel_glsl": (
                    "#version 450\nlayout(location=0) out vec4 o;"
                    "void main(){o=vec4(1.0);}"
                ),
                "source_payload_sha256": "a" * 64,
                "permutation_identity": {
                    "format": "SHIFT.ShaderPermutationIdentity/1",
                    "identity_sha256": "b" * 64,
                },
            },
            "constant_commands": [],
            "constant_payload": {
                "format": "SHIFT.MaterialConstantPayload/1",
                "ready": True,
                "registers": [],
            },
            "textures": [],
            "external_samplers": [],
        }],
    }


def _bridge(
    resource_sha,
    *,
    admitted=True,
    proven=True,
    join_ready=True,
    instances=1,
):
    packets = []
    commands = []
    for index in range(instances):
        tx = float(index)
        packets.append(
            _packet(resource_sha, admitted=admitted, tx=tx)
        )
        commands.append(
            _command(resource_sha, proven=proven, tx=tx)
        )
    return {
        "format": "SHIFT.SGBRenderBindingBridge/1",
        "runtime_shader_join": {
            "format": "SHIFT.IMBRuntimeRenderBindingJoin/1",
            "ready": join_ready,
            "status": "ready" if join_ready else "blocked",
            "blocking_reasons": (
                [] if join_ready else ["runtime-admission:not-ready"]
            ),
        },
        "render_binding": {
            "format": "SHIFT.RenderBinding/1",
            "runtime_shader_join": {
                "ready": join_ready,
                "blocking_reasons": [],
            },
            "packets": packets,
            "render_commands": commands,
            "resources": {
                "format": "SHIFT.RenderResources/1",
                "textures": [],
                "samplers": [],
                "bindings": [],
                "stats": {
                    "textures": 0,
                    "samplers": 0,
                    "bindings": 0,
                },
            },
        },
    }


def _write_ir(tmp_path):
    raw = b"synthetic-imb"
    sha = _sha(raw)
    raw_path = tmp_path / "raw" / "object.imb"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_bytes(raw)
    (tmp_path / "manifest.json").write_text(
        json.dumps([{
            "archive": "TRACK.bff",
            "path": "tracks/silverstone/object.imb",
            "raw": "raw/object.imb",
            "sha256": sha,
        }]),
        encoding="utf-8",
    )
    return sha


def _install_builders(monkeypatch):
    monkeypatch.setattr(
        scene_bundle,
        "build_imb_neutral_geometry",
        lambda data: {
            "format": "SHIFT.IMBNeutralGeometry/1",
            "ready": True,
            "blocking_reasons": [],
            "mesh": {
                "format": "SHIFT.NeutralMesh/1",
                "vertices": [
                    [0.0, 0.0, 0.0],
                    [1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                ],
                "indices": [0, 1, 2],
            },
        },
    )

    calls = []

    def fake_bundle(
        command,
        mesh,
        output_dir,
        *,
        textures=None,
        environment_cube=None,
        command_index=0,
        submesh_index=0,
        expected_mesh_ref=None,
    ):
        calls.append({
            "mesh_ref": command["mesh"]["ref"],
            "expected_mesh_ref": expected_mesh_ref,
            "submesh_index": submesh_index,
            "textures": textures,
            "runtime_provenance": (
                command["submeshes"][submesh_index].get(
                    "runtime_provenance"
                )
            ),
        })
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "format": "SHIFT.BMWVulkanBundle/1",
            "ready": True,
            "status": "ready",
            "blocking_reasons": [],
        }
        (output_dir / "bundle_manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        return manifest

    monkeypatch.setattr(
        scene_bundle,
        "build_bmw_vulkan_bundle",
        fake_bundle,
    )
    return calls


def test_builds_native_bundle_set_from_runtime_proven_render_command(
    tmp_path,
    monkeypatch,
):
    sha = _write_ir(tmp_path)
    calls = _install_builders(monkeypatch)
    out = tmp_path / "bundle"

    report = scene_bundle.build_native_scene_bundle(
        _bridge(sha),
        tmp_path,
        out,
    )

    assert report["format"] == "SHIFT.NativeSceneBundle/1"
    assert report["ready"] is True
    assert report["bundle_set_ready"] is True
    assert report["native_execution_ready"] is False
    assert report["coverage_complete"] is True
    assert report["summary"]["runtime_proven_draw_count"] == 1
    assert report["summary"]["bundle_set_draw_count"] == 1
    assert calls[0]["mesh_ref"] == "tracks/silverstone/object.imb"
    assert calls[0]["expected_mesh_ref"] == (
        "tracks/silverstone/object.imb"
    )
    assert calls[0]["runtime_provenance"]["format"] == (
        "SHIFT.RuntimeProvenDraw/1"
    )

    bundle_set = json.loads(
        (out / "bundle_set_manifest.json").read_text(encoding="utf-8")
    )
    assert bundle_set["format"] == "SHIFT.BMWVulkanBundleSet/1"
    assert bundle_set["ready"] is True
    assert bundle_set["draw_count"] == 1
    assert (out / "bundle_set.paths").read_text(
        encoding="utf-8"
    ).splitlines() == [
        "draws/command_00000_submesh_000"
    ]
    assert report["boundary"]["scene_transform_parity"] is False
    included = report["included_draws"][0]
    assert included["runtime_binding_index"] == 77
    assert len(included["runtime_provenance_sha256"]) == 64


def test_unique_shader_without_runtime_proven_draw_is_excluded(
    tmp_path,
    monkeypatch,
):
    sha = _write_ir(tmp_path)
    calls = _install_builders(monkeypatch)

    report = scene_bundle.build_native_scene_bundle(
        _bridge(sha, proven=False),
        tmp_path,
        tmp_path / "bundle",
    )

    assert calls == []
    assert report["ready"] is False
    assert report["bundle_set_ready"] is False
    assert report["summary"]["runtime_proven_draw_count"] == 0
    assert report["excluded_draws"][0]["reason"] == (
        "runtime-provenance-not-proven"
    )
    assert (
        "runtime-provenance-missing"
        in report["excluded_draws"][0]["blocking_reasons"]
    )


def test_packet_admission_is_required_as_cross_check(
    tmp_path,
    monkeypatch,
):
    sha = _write_ir(tmp_path)
    calls = _install_builders(monkeypatch)

    report = scene_bundle.build_native_scene_bundle(
        _bridge(sha, admitted=False, proven=True),
        tmp_path,
        tmp_path / "bundle",
    )

    assert calls == []
    reasons = report["excluded_draws"][0]["blocking_reasons"]
    assert "packet-runtime-admission-missing" in reasons


def test_not_ready_phase576_join_cannot_be_bypassed_by_provenance(
    tmp_path,
    monkeypatch,
):
    sha = _write_ir(tmp_path)
    calls = _install_builders(monkeypatch)

    report = scene_bundle.build_native_scene_bundle(
        _bridge(sha, join_ready=False),
        tmp_path,
        tmp_path / "bundle",
    )

    assert calls == []
    assert report["bundle_set_ready"] is False
    assert (
        "runtime-shader-join:runtime-admission:not-ready"
        in report["blocking_reasons"]
    )
    assert report["excluded_draws"][0]["reason"] == (
        "runtime-shader-join-not-ready"
    )


def test_tampered_runtime_resource_identity_is_excluded(
    tmp_path,
    monkeypatch,
):
    sha = _write_ir(tmp_path)
    calls = _install_builders(monkeypatch)
    bridge = _bridge(sha)
    provenance = (
        bridge["render_binding"]["render_commands"][0]
        ["submeshes"][0]["runtime_provenance"]
    )
    provenance["resource"]["sha256"] = "0" * 64

    report = scene_bundle.build_native_scene_bundle(
        bridge,
        tmp_path,
        tmp_path / "bundle",
    )

    assert calls == []
    assert (
        "runtime-provenance-resource-sha256-mismatch"
        in report["excluded_draws"][0]["blocking_reasons"]
    )


def test_resource_level_admission_can_emit_multiple_scene_draws(
    tmp_path,
    monkeypatch,
):
    sha = _write_ir(tmp_path)
    calls = _install_builders(monkeypatch)

    report = scene_bundle.build_native_scene_bundle(
        _bridge(sha, instances=2),
        tmp_path,
        tmp_path / "bundle",
    )

    assert len(calls) == 2
    assert report["summary"]["runtime_proven_draw_count"] == 2
    assert report["bundle_set"]["draw_count"] == 2
    assert report["included_draws"][0]["runtime_binding_index"] == 77
    assert report["included_draws"][1]["runtime_binding_index"] == 77
    assert report["included_draws"][0]["world_matrix_identity"] is True
    assert report["included_draws"][1]["world_matrix_identity"] is False


def test_prepare_result_controls_native_execution_ready(
    tmp_path,
    monkeypatch,
):
    sha = _write_ir(tmp_path)
    _install_builders(monkeypatch)
    monkeypatch.setattr(
        scene_bundle,
        "prepare_bmw_vulkan_bundle_set",
        lambda root, validator=None: {
            "format": "SHIFT.BMWVulkanBundleSetPrepare/1",
            "ready": True,
            "status": "ready",
            "draw_count": 1,
            "blocking_reasons": [],
        },
    )

    report = scene_bundle.build_native_scene_bundle(
        _bridge(sha),
        tmp_path,
        tmp_path / "bundle",
        prepare=True,
        validator="fake-validator",
    )

    assert report["bundle_set_ready"] is True
    assert report["native_execution_ready"] is True
    assert report["bundle_set_prepare"]["ready"] is True
