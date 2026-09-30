import json

from vulkan_draw_bundle import (
    FORMAT,
    build_vulkan_draw_bundle,
)


def _sha(char):
    return char * 64


def _provenance(*, first_index=0, index_count=3):
    return {
        "format": "SHIFT.RuntimeProvenDraw/1",
        "status": "proven",
        "binding_index": 17,
        "resource": {
            "source_kind": "IMB",
            "path": "tracks/silverstone/object.imb",
            "archive": "Silverstone_Era3_GrandPrix.bff",
            "sha256": _sha("a"),
        },
        "primitive_index": 0,
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
                "permutation_identity_sha256": _sha("5"),
            },
        },
    }


def _command(*, provenance=True, world=True):
    submesh = {
        "primitive_index": 0,
        "first_index": 0,
        "index_count": 3,
        "runtime_provenance": (
            _provenance() if provenance else None
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
        "constant_commands": [],
        "constant_payload": {
            "format": "SHIFT.MaterialConstantPayload/1",
            "registers": [],
            "ready": True,
        },
        "textures": [],
        "external_samplers": [],
    }
    return {
        "format": "SHIFT.RenderCommand/1",
        "ready": True,
        "validation": {
            "valid": True,
            "blocking_reasons": [],
        },
        "mesh": {
            "ref": "tracks/silverstone/object.imb",
            "resolved": {
                "path": "tracks/silverstone/object.imb",
                "resource_sha256": _sha("a"),
            },
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
        "world_matrix": (
            [
                1.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                10.0, 20.0, 30.0, 1.0,
            ]
            if world else None
        ),
        "submeshes": [submesh],
        "runtime_proven_draw_count": 1 if provenance else 0,
    }


def _mesh():
    return {
        "format": "SHIFT.NeutralMesh/1",
        "source_format": "SHIFT.IMBBinaryMesh/1",
        "vertices": [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        "indices": [0, 1, 2],
    }


def test_generic_vulkan_bundle_accepts_runtime_proven_neutral_imb_mesh(
    tmp_path,
):
    result = build_vulkan_draw_bundle(
        _command(),
        _mesh(),
        tmp_path,
    )

    assert result["format"] == FORMAT
    assert result["ready"] is True, result["blocking_reasons"]
    assert result["runtime_provenance_gate"]["ready"] is True
    assert result["native_submission_gate"]["ready"] is True
    assert result["source"]["mesh_provenance"] == {
        "input_format": "SHIFT.NeutralMesh/1",
        "mesh_format": "SHIFT.NeutralMesh/1",
        "source_format": "SHIFT.IMBBinaryMesh/1",
    }
    assert result["artifacts"]["geometry"]["ready"] is True
    assert result["artifacts"]["constants"]["ready"] is True
    assert result["artifacts"]["pipeline_state"]["ready"] is True
    assert result["artifacts"]["sampler_contracts"]["ready"] is True
    assert len(result["artifacts"]["shaders"]) == 2
    assert (tmp_path / "geometry.svpk").exists()
    assert (tmp_path / "constants.svcp").exists()
    assert (tmp_path / "runtime_provenance_gate.json").exists()

    manifest = json.loads(
        (tmp_path / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["format"] == FORMAT


def test_generic_bundle_preserves_but_does_not_claim_scene_transform(
    tmp_path,
):
    result = build_vulkan_draw_bundle(
        _command(world=True),
        _mesh(),
        tmp_path,
    )

    assert result["ready"] is True
    transform = result["scene_transform"]
    assert transform["world_matrix"][12:15] == [10.0, 20.0, 30.0]
    assert transform["execution_status"] == "preserved-not-applied"
    assert transform["blocking_for_scene_native_submission"] is True
    assert result["boundary"]["scene_world_transform_executed"] is False


def test_generic_bundle_blocks_missing_runtime_provenance_by_default(
    tmp_path,
):
    result = build_vulkan_draw_bundle(
        _command(provenance=False),
        _mesh(),
        tmp_path,
    )

    assert result["ready"] is False
    assert (
        "vulkan-draw-bundle:runtime-provenance-missing"
        in result["blocking_reasons"]
    )
    assert result["artifacts"] == {}
    assert (
        result["native_execution"]["status"]
        == "blocked-by-admission-gate"
    )


def test_generic_bundle_can_be_reused_for_static_non_scene_draws(
    tmp_path,
):
    result = build_vulkan_draw_bundle(
        _command(provenance=False, world=False),
        _mesh(),
        tmp_path,
        require_runtime_provenance=False,
    )

    assert result["ready"] is True
    assert result["runtime_provenance_gate"]["required"] is False
    assert result["runtime_provenance_gate"]["ready"] is True


def test_generic_bundle_blocks_tampered_runtime_draw_range(tmp_path):
    command = _command()
    command["submeshes"][0]["runtime_provenance"]["draw_range"][
        "first_index"
    ] = 9

    result = build_vulkan_draw_bundle(
        command,
        _mesh(),
        tmp_path,
    )

    assert result["ready"] is False
    assert (
        "vulkan-draw-bundle:runtime-draw-range-mismatch"
        in result["blocking_reasons"]
    )


def test_generic_bundle_unwraps_imb_neutral_geometry(tmp_path):
    report = {
        "format": "SHIFT.IMBNeutralGeometry/1",
        "ready": True,
        "mesh": _mesh(),
    }
    result = build_vulkan_draw_bundle(
        _command(),
        report,
        tmp_path,
    )

    assert result["ready"] is True
    assert (
        result["source"]["mesh_provenance"]["input_format"]
        == "SHIFT.IMBNeutralGeometry/1"
    )
    assert (
        result["artifacts"]["geometry"]["source_mesh_format"]
        == "SHIFT.NeutralMesh/1"
    )


def test_generic_bundle_rejects_unknown_mesh_contract(tmp_path):
    mesh = _mesh()
    mesh["format"] = "SHIFT.UnknownMesh/1"
    try:
        build_vulkan_draw_bundle(
            _command(),
            mesh,
            tmp_path,
        )
    except ValueError as error:
        assert "SHIFT.NeutralMesh/1" in str(error)
    else:
        raise AssertionError("unknown mesh contract was accepted")


def test_generic_geometry_metadata_no_longer_claims_meb_space(tmp_path):
    result = build_vulkan_draw_bundle(
        _command(),
        _mesh(),
        tmp_path,
    )
    assert result["ready"] is True

    # Geometry binary ABI remains unchanged; its returned metadata is not
    # embedded in bundle_manifest, so verify through the neutral bundle source
    # and the Phase 579 boundary instead.
    assert result["source"]["mesh_provenance"]["mesh_format"] == (
        "SHIFT.NeutralMesh/1"
    )
    assert result["boundary"]["neutral_mesh_container_equivalence"] is False


def test_generic_bundle_can_execute_scene_transform_into_geometry(tmp_path):
    result = build_vulkan_draw_bundle(
        _command(world=True),
        _mesh(),
        tmp_path,
        apply_scene_transform=True,
    )

    assert result["ready"] is True, result["blocking_reasons"]
    transform = result["scene_transform"]
    assert transform["execution_status"] == "baked-into-geometry"
    assert transform["blocking_for_scene_native_submission"] is False
    assert transform["geometry_mode"] == "cpu-baked-row-vector-affine"
    assert transform["transformed_properties"] == ["200"]
    assert result["boundary"]["scene_world_transform_executed"] is True
    assert result["boundary"]["scene_transform_mode"] == (
        "cpu-baked-row-vector-affine"
    )
