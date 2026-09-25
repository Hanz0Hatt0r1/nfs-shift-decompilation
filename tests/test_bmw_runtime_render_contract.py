from pathlib import Path
from types import SimpleNamespace

import bmw_runtime_render_contract as contract
import bmw_runtime_shader_select


class FakeArchive:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.name == "RENDER.bff":
            self.entries = [SimpleNamespace(
                path="render/shaders/cache/render_shaders_bodywork_test.fxo",
                index=77,
            )]
        else:
            self.entries = [SimpleNamespace(
                path=contract.TARGET_MEB,
                index=863,
            )]

    def extract_entry(self, entry):
        return b"fxo" if self.path.name == "RENDER.bff" else b"meb"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _material_input():
    return {
        "format": "SHIFT.RealBMWMaterialBindingEvidence/1",
        "provenance": {
            "mesh_entry": {
                "path": contract.TARGET_MEB,
                "sha256": "m" * 64,
            }
        },
        "material_binding": {
            "bindings": [
                {
                    "binding": "external-or-specialised",
                    "sampler": "sShadowMap_f1_0",
                    "sampler_type": "sampler2D",
                    "d3d9_sampler_register": 0,
                },
                {
                    "binding": "external-or-specialised",
                    "sampler": "environmentMap",
                    "sampler_type": "samplerCube",
                    "d3d9_sampler_register": 3,
                },
            ],
            "fxo_candidates": [
                {
                    "file": "RENDER.bff::render/shaders/cache/render_shaders_bodywork_test.fxo",
                    "program_offset": 128,
                    "pixel_sha256": "p" * 64,
                    "vertex_sha256": "v" * 64,
                    "pair_sha256": "q" * 64,
                    "permutation_identity": {
                        "vertex_offset": 64,
                        "pixel_offset": 128,
                    },
                }
            ],
        },
    }


def _runtime():
    return {
        "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
        "frames": [{
            "frame": 9,
            "shader_permutation_identity": {
                "format": "SHIFT.ShaderPermutationIdentity/1",
                "identity_sha256": "i" * 64,
            },
            "vertex_shader": {"shader_ptr": "0x100"},
            "pixel_shader": {"shader_ptr": "0x200"},
            "constant_writes": [
                {
                    "stage": "vertex",
                    "start_register": 0,
                    "vector4f_count": 2,
                    "values": [
                        1.0, 2.0, 3.0, 4.0,
                        5.0, 6.0, 7.0, 8.0,
                    ],
                },
                {
                    "stage": "pixel",
                    "start_register": 4,
                    "vector4f_count": 1,
                    "values": [9.0, 10.0, 11.0, 12.0],
                },
            ],
            "texture_bindings": [
                {"stage": 0, "texture_ptr": "0x300"},
                {"stage": 3, "texture_ptr": "0x400", "resource_descriptor": {"resource_type_name": "cube_texture", "width": 128, "height": 128, "level_count": 8}},
            ],
            "draws": [{"primitive_count": 1}],
        }],
    }


def test_runtime_render_contract_builds_stage_specific_inputs(monkeypatch, tmp_path):
    monkeypatch.setattr(contract, "BFF", FakeArchive)
    monkeypatch.setattr(
        contract,
        "read_meb",
        lambda data: SimpleNamespace(
            vertex_properties=["200", "460", "220", "240", "250", "130", "132", "133"],
            vertex_count=3550,
            triangle_count=5034,
        ),
    )
    monkeypatch.setattr(
        contract,
        "translate_pair_blob",
        lambda *args, **kwargs: {
            "format": "SHIFT.LinkedShaderPair/1",
            "vertex_glsl": "void main(){}",
            "pixel_glsl": "void main(){}",
        },
    )
    monkeypatch.setattr(
        bmw_runtime_shader_select,
        "select_runtime_shader",
        lambda material, runtime: {
            "format": "SHIFT.BMWRuntimeShaderSelection/1",
            "status": "match",
            "ready": True,
            "blocking_reasons": [],
            "selected": {
                "frame": 9,
                "candidate_file": "RENDER.bff::render/shaders/cache/render_shaders_bodywork_test.fxo",
                "candidate_program_offset": 128,
            },
        },
    )

    report = contract.build_runtime_render_contract(
        _material_input(),
        _runtime(),
        primary_bff=tmp_path / "BMW_M3_E36.bff",
        render_bff=tmp_path / "RENDER.bff",
    )

    assert report["format"] == "SHIFT.BMWRuntimeRenderContract/1"
    assert report["ready"] is True
    assert report["reference_render_ready"] is True
    assert report["constants"]["vertex"]["c"][0] == [1.0, 2.0, 3.0, 4.0]
    assert report["constants"]["vertex"]["c"][1] == [5.0, 6.0, 7.0, 8.0]
    assert report["constants"]["pixel"]["c"][4] == [9.0, 10.0, 11.0, 12.0]
    assert {row["d3d9_sampler_register"]: row["texture_ptr"] for row in report["external_textures"]} == {
        0: "0x300",
        3: "0x400",
    }
    assert report["external_textures"][1]["resource_descriptor"]["resource_type_name"] == "cube_texture"
    assert report["shader"]["linked_shader_pair"]["format"] == "SHIFT.LinkedShaderPair/1"


def test_runtime_render_contract_blocks_missing_external_texture_object(monkeypatch, tmp_path):
    monkeypatch.setattr(contract, "BFF", FakeArchive)
    monkeypatch.setattr(
        contract,
        "read_meb",
        lambda data: SimpleNamespace(vertex_properties=["200"], vertex_count=3, triangle_count=1),
    )
    monkeypatch.setattr(
        contract,
        "translate_pair_blob",
        lambda *args, **kwargs: {"format": "SHIFT.LinkedShaderPair/1"},
    )
    monkeypatch.setattr(
        bmw_runtime_shader_select,
        "select_runtime_shader",
        lambda material, runtime: {
            "format": "SHIFT.BMWRuntimeShaderSelection/1",
            "status": "match",
            "ready": True,
            "blocking_reasons": [],
            "selected": {
                "frame": 9,
                "candidate_file": "RENDER.bff::render/shaders/cache/render_shaders_bodywork_test.fxo",
                "candidate_program_offset": 128,
            },
        },
    )
    runtime = _runtime()
    runtime["frames"][0]["texture_bindings"] = [
        {"stage": 0, "texture_ptr": "0x300"}
    ]

    report = contract.build_runtime_render_contract(
        _material_input(),
        runtime,
        primary_bff=tmp_path / "BMW_M3_E36.bff",
        render_bff=tmp_path / "RENDER.bff",
    )

    assert report["ready"] is True
    assert report["reference_render_ready"] is False
    assert "runtime:texture-object-not-bound:s3" in report["blocking_reasons"]


def test_runtime_render_contract_uses_selected_draw_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(contract, "BFF", FakeArchive)
    monkeypatch.setattr(
        contract,
        "read_meb",
        lambda data: SimpleNamespace(vertex_properties=["200"], vertex_count=3, triangle_count=1),
    )
    monkeypatch.setattr(
        contract,
        "translate_pair_blob",
        lambda *args, **kwargs: {"format": "SHIFT.LinkedShaderPair/1"},
    )
    monkeypatch.setattr(
        bmw_runtime_shader_select,
        "select_runtime_shader",
        lambda material, runtime: {
            "format": "SHIFT.BMWRuntimeShaderSelection/1",
            "status": "match",
            "ready": True,
            "blocking_reasons": [],
            "selected": {
                "frame": 9,
                "draw_index": 1,
                "source": "draw-snapshot",
                "candidate_file": "RENDER.bff::render/shaders/cache/render_shaders_bodywork_test.fxo",
                "candidate_program_offset": 128,
            },
        },
    )
    runtime = _runtime()
    runtime["frames"][0]["constant_writes"] = [{
        "stage": "pixel",
        "start_register": 5,
        "vector4f_count": 1,
        "values": [99.0, 99.0, 99.0, 99.0],
    }]
    runtime["frames"][0]["texture_bindings"] = [{"stage": 0, "texture_ptr": "0x900"}]
    runtime["frames"][0]["draw_snapshots"] = [
        {
            "frame": 9,
            "draw_index": 0,
            "vertex_shader": {"shader_ptr": "0xdead"},
            "pixel_shader": {"shader_ptr": "0xbeef"},
            "constant_writes": [{
                "stage": "pixel",
                "start_register": 5,
                "vector4f_count": 1,
                "values": [1.0, 1.0, 1.0, 1.0],
            }],
            "texture_bindings": [{"stage": 0, "texture_ptr": "0x100"}],
            "draw": {"primitive_count": 1},
        },
        {
            "frame": 9,
            "draw_index": 1,
            "vertex_shader": {"shader_ptr": "0x200"},
            "pixel_shader": {"shader_ptr": "0x300"},
            "constant_writes": [{
                "stage": "pixel",
                "start_register": 5,
                "vector4f_count": 1,
                "values": [2.0, 3.0, 4.0, 5.0],
            }],
            "texture_bindings": [{"stage": 0, "texture_ptr": "0x400"}],
            "draw": {"primitive_count": 2},
        },
    ]

    report = contract.build_runtime_render_contract(
        _material_input(),
        runtime,
        primary_bff=tmp_path / "BMW_M3_E36.bff",
        render_bff=tmp_path / "RENDER.bff",
    )

    assert report["constants"]["pixel"]["c"][5] == [2.0, 3.0, 4.0, 5.0]
    assert report["external_textures"][0]["texture_ptr"] == "0x400"
    assert report["frame"]["indexed_draw_count"] == 1
