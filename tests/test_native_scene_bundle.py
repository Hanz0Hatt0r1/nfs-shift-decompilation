from native_scene_bundle import (
    FORMAT,
    build_native_scene_bundle,
)


def _sha(char):
    return char * 64


def _world():
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        10.0, 20.0, 30.0, 1.0,
    ]


def _provenance(*, binding_index=7, first_index=0, index_count=3):
    return {
        "format": "SHIFT.RuntimeProvenDraw/1",
        "status": "proven",
        "binding_index": binding_index,
        "resource": {
            "source_kind": "IMB",
            "path": "tracks/silverstone/object.imb",
            "archive": "Silverstone_Era3_GrandPrix.bff",
            "sha256": _sha("a"),
        },
        "primitive_index": 2,
        "draw_range": {
            "first_index": first_index,
            "index_count": index_count,
            "primitive_count": index_count // 3,
        },
        "shader_selection": {
            "selection_status": "unique",
            "selection_source": "runtime-admission",
            "runtime_selection_ready": True,
            "selected_variant": {
                "score": 100,
                "permutation_identity_sha256": _sha("b"),
            },
        },
        "boundary": {
            "render_backend_admission": False,
        },
    }


def _submesh(*, provenance=True, first_index=0, index_count=3):
    return {
        "primitive_index": 2,
        "first_index": first_index,
        "index_count": index_count,
        "runtime_provenance": (
            _provenance(
                first_index=first_index,
                index_count=index_count,
            )
            if provenance
            else None
        ),
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


def _command(*submeshes, ready=True, world=None):
    return {
        "format": "SHIFT.RenderCommand/1",
        "ready": ready,
        "blocking_reasons": [] if ready else ["synthetic-blocker"],
        "mesh": {
            "ref": "tracks/silverstone/object.imb",
            "vertex_count": 3,
            "triangle_count": max(1, len(submeshes)),
            "vertex_layout": {
                "format": "SHIFT.VertexLayout/1",
                "buffer_stride": 12,
                "attributes": [{
                    "property_id": "200",
                    "location": 0,
                    "offset": 0,
                    "stride": 12,
                    "element_size": 12,
                    "storage": "f32x3",
                }],
            },
            "attributes": [{
                "property_id": "200",
                "location": 0,
                "offset": 0,
                "stride": 12,
                "element_size": 12,
                "storage": "f32x3",
            }],
            "attribute_setup": [],
        },
        "world_matrix": _world() if world is None else world,
        "submeshes": list(submeshes),
        "runtime_proven_draw_count": sum(
            row.get("runtime_provenance") is not None
            for row in submeshes
        ),
        "resource_plan": {
            "format": "SHIFT.RenderResources/1",
            "texture_count": 0,
            "sampler_count": 0,
            "external_sampler_count": 0,
        },
    }


def _packet():
    return {
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
    }


def _bridge(*commands):
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
            "packets": [_packet() for _ in commands],
            "render_commands": list(commands),
        },
    }


def test_native_scene_bundle_accepts_only_runtime_proven_ready_draw():
    report = build_native_scene_bundle(
        _bridge(_command(_submesh()))
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["draw_count"] == 1
    assert report["coverage"] == {
        "total_render_submeshes": 1,
        "runtime_proven_submeshes": 1,
        "native_packable_proven_submeshes": 1,
        "excluded_submeshes": 0,
        "complete_scene_coverage": True,
    }

    draw = report["draws"][0]
    assert draw["draw_order"] == 0
    assert draw["binding_index"] == 7
    assert draw["primitive_index"] == 2
    assert draw["resource"]["source_kind"] == "IMB"
    assert draw["resource"]["sha256"] == _sha("a")
    assert draw["world_matrix"][12:15] == [10.0, 20.0, 30.0]
    assert draw["scene"]["node"] == "GRANDSTAND"
    assert draw["shader_identity"]["pair_sha256"] == _sha("2")
    assert all(len(value) == 64 for value in draw["hashes"].values())


def test_unproven_draw_is_not_promoted():
    report = build_native_scene_bundle(
        _bridge(_command(_submesh(provenance=False)))
    )

    assert report["ready"] is False
    assert report["draw_count"] == 0
    assert report["coverage"]["runtime_proven_submeshes"] == 0
    assert report["excluded_draws"][0]["reason"] == "not-runtime-proven"
    assert report["boundary"]["unproven_draws_promoted"] is False


def test_partial_scene_coverage_keeps_only_proven_draws():
    report = build_native_scene_bundle(
        _bridge(
            _command(
                _submesh(provenance=True, first_index=0),
                _submesh(provenance=False, first_index=3),
            )
        )
    )

    assert report["ready"] is True
    assert report["draw_count"] == 1
    assert report["coverage"]["total_render_submeshes"] == 2
    assert report["coverage"]["native_packable_proven_submeshes"] == 1
    assert report["coverage"]["excluded_submeshes"] == 1
    assert report["coverage"]["complete_scene_coverage"] is False
    assert report["boundary"]["partial_scene_coverage_allowed"] is True


def test_tampered_runtime_draw_range_is_excluded():
    submesh = _submesh()
    submesh["runtime_provenance"]["draw_range"]["first_index"] = 9
    report = build_native_scene_bundle(
        _bridge(_command(submesh))
    )

    assert report["ready"] is False
    assert report["draw_count"] == 0
    assert (
        "runtime-provenance:draw-range-mismatch"
        in report["excluded_draws"][0]["blocking_reasons"]
    )


def test_invalid_world_matrix_excludes_runtime_proven_draw():
    report = build_native_scene_bundle(
        _bridge(_command(_submesh(), world=None))
    )
    # world=None means use fixture default; explicitly break it.
    broken = _bridge(_command(_submesh()))
    broken["render_binding"]["render_commands"][0]["world_matrix"] = None
    report = build_native_scene_bundle(broken)

    assert report["ready"] is False
    assert report["draw_count"] == 0
    assert (
        "world-matrix:missing-or-invalid"
        in report["excluded_draws"][0]["blocking_reasons"]
    )


def test_incomplete_shader_identity_excludes_draw():
    command = _command(_submesh())
    command["submeshes"][0]["shader"]["pair_sha256"] = None
    report = build_native_scene_bundle(_bridge(command))

    assert report["ready"] is False
    assert report["draw_count"] == 0
    assert (
        "shader-identity:pair_sha256:missing-or-invalid"
        in report["excluded_draws"][0]["blocking_reasons"]
    )


def test_scene_bridge_runtime_join_must_be_ready():
    bridge = _bridge(_command(_submesh()))
    bridge["runtime_shader_join"]["ready"] = False
    report = build_native_scene_bundle(bridge)

    assert report["ready"] is False
    assert report["draw_count"] == 1
    assert "runtime-shader-join:not-ready" in report["blocking_reasons"]


def test_native_scene_hashes_are_deterministic():
    bridge = _bridge(_command(_submesh()))
    first = build_native_scene_bundle(bridge)
    second = build_native_scene_bundle(bridge)

    assert first["draws"][0]["hashes"] == second["draws"][0]["hashes"]
    assert (
        first["draws"][0]["runtime_provenance"]
        == second["draws"][0]["runtime_provenance"]
    )


def test_wrong_input_format_is_rejected():
    try:
        build_native_scene_bundle({"format": "SHIFT.Other/1"})
    except ValueError as error:
        assert "SHIFT.SGBRenderBindingBridge/1" in str(error)
    else:
        raise AssertionError("invalid scene bridge format was accepted")
