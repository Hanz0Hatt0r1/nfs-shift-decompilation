from pathlib import Path
import hashlib
from types import SimpleNamespace
import json

import pytest

import bmw_real_material_slice as slicer


class FakeEntry:
    def __init__(self, path, index):
        self.path = path
        self.index = index


class FakeArchive:
    def __init__(self, path):
        self.path = Path(path)
        self.entries = [
            FakeEntry("vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt", 0),
            FakeEntry("vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb", 1),
            FakeEntry("render/shaders/bodywork.fx", 2),
            FakeEntry("render/textures/COMMON_PAINT.dds", 3),
        ]

    def extract_entry(self, entry):
        return b"x"

    def close(self):
        pass


def _golden():
    return {
        "format": "SHIFT.BMWGoldenAssetManifest/1",
        "golden": {
            "resource": slicer.TARGET_MEB,
            "resource_sha256": hashlib.sha256(b"x").hexdigest(),
        },
        "mesh": {
            "vertex_count": 4,
            "triangle_count": 1,
            "color460_descriptor": {"words": [4, 6, 0]},
            "primitives": [
                {"first_index": 0, "index_count": 3, "material": "vehicles/bmw_m3_e36/bmw_m3_e36_badging.mtx"},
                {"first_index": 150, "index_count": 6294, "material": slicer.TARGET_BMT[:-4] + ".mtx"},
            ],
            "skinning": {"skinned": False},
        },
        "provenance": {
            "bundle": "fixture.zip",
            "bundle_resource_id": "fixture",
            "collector_version": "test",
            "raw_row_sha256": "a" * 64,
        },
    }


def _binding_report():
    return {
        "format": "SHIFT.RealBMWMaterialBindingEvidence/1",
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "material_binding": {
            "format": "SHIFT.MaterialBinding/1",
            "material": "BMW_M3_E36_PAINT",
            "shader": "bodywork.fx",
            "specialization": {"requested": ["USE_FRESNEL", "ALLOW_VINYLS", "DIRT_SCRATCH"]},
            "bindings": [
                {"texture_parameter":"diffuseTexture","sampler":"diffuseMap","d3d9_sampler_register":1,"texture":"COMMON_PAINT.dds","min_filter":"Linear","mag_filter":"Linear","mip_filter":"Linear","address_u":"Wrap","address_v":"Wrap","srgb":True,"binding":"material-texture"},
                {"texture_parameter":"specularTexture","sampler":"specularMap","d3d9_sampler_register":2,"texture":"COMMON_PAINT_SPECULAR.dds","min_filter":"Linear","mag_filter":"Linear","mip_filter":"Linear","address_u":"Wrap","address_v":"Wrap","srgb":True,"binding":"material-texture"},
                {"texture_parameter":"scratchControlTexture","sampler":"scratchControlMap","d3d9_sampler_register":4,"texture":"COMMON_BLANK.dds","min_filter":"Linear","mag_filter":"Linear","mip_filter":"None","address_u":"Clamp","address_v":"Clamp","srgb":False,"binding":"material-texture"},
                {"sampler":"environmentMap","d3d9_sampler_register":3,"binding":"external-or-specialised"},
                {"sampler":"sShadowMap_f1_0","d3d9_sampler_register":0,"binding":"external-or-specialised"},
            ],
            "unresolved_textures": [],
            "selection_status": "unique",
            "selected_fxo": {"file":"bodywork.fxo","program_offset":64,"exact":True,"vertex_pair_selection_status":"unique","pixel_sha256":"b"*64,"vertex_sha256":"c"*64,"pair_sha256":"d"*64,"specialization_matched":["USE_FRESNEL","ALLOW_VINYLS","DIRT_SCRATCH"]},
            "shader_pair": {"selection_status":"unique"},
            "linked_shader_pair": {"format":"SHIFT.LinkedShaderPair/1","vertex_glsl":"void main(){}","pixel_glsl":"void main(){}"},
            "permutation_identity": {"format":"SHIFT.ShaderPermutationIdentity/1","identity_sha256":"e"*64},
            "linked_shader_error": None,
            "uniform_binding": {"format":"SHIFT.MaterialUniformBinding/1","bindings":[]},
        },
        "paint_contract": {"ready": True, "blocking_reasons": []},
        "paint_shader_gate": {"ready": True, "blocking_reasons": []},
        "provenance": {},
    }


def test_real_bmw_material_slice_builds_renderer_compatible_slice(monkeypatch, tmp_path):
    primary=tmp_path/"BMW_M3_E36.bff"
    primary.write_bytes(b"fixture")
    archive=FakeArchive(primary)

    monkeypatch.setattr(slicer, "build_real_bmw_material_binding", lambda *a, **k: _binding_report())
    monkeypatch.setattr(slicer, "BFF", lambda path: archive)
    golden_path=tmp_path/"golden.json"
    golden_path.write_text(json.dumps(_golden()), encoding="utf-8")
    monkeypatch.setattr(slicer, "validate_bmw_paint_asset", lambda golden: {"ready":True,"blocking_reasons":[]})
    mesh=SimpleNamespace(
        name="BMW_M3_E36_KIT00_BODY_LODA",
        vertex_count=4,
        triangle_count=1,
        property_descriptors=[{"id":"200","words":[2,0,0]},{"id":"460","words":[4,6,0]}],
        primitives=[
            SimpleNamespace(first_index=0,index_count=3,material="vehicles/bmw_m3_e36/bmw_m3_e36_badging.mtx"),
            SimpleNamespace(first_index=150,index_count=6294,material="vehicles/bmw_m3_e36/bmw_m3_e36_paint.mtx"),
        ],
    )
    monkeypatch.setattr(slicer, "read_meb", lambda data: mesh)
    monkeypatch.setattr(slicer, "mesh_summary", lambda m: {"format":"SHIFT.MEB","vertex_count":4,"triangle_count":1,"skinning":{"skinned":False},"property_descriptors":m.property_descriptors,"primitives":[
            {"first_index":0,"index_count":3,"material":m.primitives[0].material},
            {"first_index":150,"index_count":6294,"material":m.primitives[1].material},
        ]})
    monkeypatch.setattr(slicer, "mesh_to_jsonable", lambda m: {"format":"SHIFT.MEB","vertices":[[0,0,0]]*4,"indices":[0,1,2]})
    monkeypatch.setattr(slicer, "build_layout_from_summary", lambda x: {"format":"SHIFT.VertexLayout/1","buffer_stride":32,"attributes":[{"property_id":"200","usage":"POSITION","usage_index":0,"location":0,"offset":0,"stride":32,"storage":"f32x3"}]})
    monkeypatch.setattr(slicer, "parse_bmt_material", lambda data: {"material":{"name":"BMW_M3_E36_PAINT","shader":"bodywork.fx","shaderparams":[]}})
    monkeypatch.setattr(slicer, "parse_dds_metadata", lambda data: {"format":"DDS","width":64,"height":64,"mipmaps":1,"fourcc":"DXT5","rgb_bits":0,"byte_size":1})
    monkeypatch.setattr(slicer, "compile_material", lambda *a, **k: {
        "ref":"vehicles/bmw_m3_e36/bmw_m3_e36_paint.mtx",
        "name":"BMW_M3_E36_PAINT",
        "shader_selection":{"status":"unique","linked_shader_pair":{"format":"SHIFT.LinkedShaderPair/1","vertex_glsl":"void main(){}","pixel_glsl":"void main(){}"},"shader_pair":{"selection_status":"unique"},"permutation_identity":{"format":"SHIFT.ShaderPermutationIdentity/1","identity_sha256":"f"*64},"uniform_binding":{"format":"SHIFT.MaterialUniformBinding/1","bindings":[]}},
        "textures":[],
        "paint_contract":{"ready":True,"blocking_reasons":[]},
        "paint_shader_gate":{"ready":True,"blocking_reasons":[]},
        "blocking_reasons":[],
    })
    monkeypatch.setattr(slicer, "build_static_draw_contract", lambda packet: {
        "format":"SHIFT.StaticDraw/1","ready":True,"blocking_reasons":[],
        "mesh":packet["mesh"],"submeshes":packet["submeshes"],"world_matrix":None
    })
    monkeypatch.setattr(slicer, "build_resource_index", lambda *a, **k: {"format":"SHIFT.RenderResources/1","textures":[],"samplers":[],"bindings":[],"stats":{"textures":0,"samplers":0,"bindings":0}})
    monkeypatch.setattr(slicer, "build_render_command", lambda *a, **k: {"format":"SHIFT.RenderCommand/1","ready":True,"blocking_reasons":[],"mesh":{"vertex_layout":{"format":"SHIFT.VertexLayout/1"},"vertex_count":4,"attributes":[]},"submeshes":[{"first_index":0,"index_count":3,"shader":{"vertex":"void main(){}","pixel":"void main(){}"}}],"resource_plan":{"format":"SHIFT.RenderResources/1","texture_count":0,"sampler_count":0,"external_sampler_count":0}})
    report=slicer.build_real_bmw_material_slice(primary, golden_path)
    assert report["format"]=="SHIFT.BMWMaterialSlice/1"
    assert report["ready"] is True
    assert report["render_command"]["ready"] is True
    assert report["static_draw"]["ready"] is True
    assert report["slice_golden_gate"]["ready"] is True
    assert report["source_format"]=="SHIFT.RealBMWMaterialSliceEvidence/1"


def test_real_bmw_material_slice_blocks_non_paint_primitive(monkeypatch, tmp_path):
    primary=tmp_path/"BMW_M3_E36.bff"
    primary.write_bytes(b"fixture")
    monkeypatch.setattr(slicer, "build_real_bmw_material_binding", lambda *a, **k: _binding_report())
    monkeypatch.setattr(slicer, "BFF", lambda path: FakeArchive(path))
    golden_path=tmp_path/"golden.json"
    golden_path.write_text(json.dumps(_golden()), encoding="utf-8")
    monkeypatch.setattr(slicer, "validate_bmw_paint_asset", lambda golden: {"ready":True,"blocking_reasons":[]})
    mesh=SimpleNamespace(name="M3",vertex_count=4,triangle_count=1,property_descriptors=[],primitives=[
        SimpleNamespace(first_index=0,index_count=3,material="vehicles/bmw_m3_e36/BMW_M3_E36_BADGING.mtx")
    ])
    monkeypatch.setattr(slicer, "read_meb", lambda data: mesh)
    monkeypatch.setattr(slicer, "mesh_summary", lambda m: {"format":"SHIFT.MEB","vertex_count":4,"triangle_count":1,"skinning":{"skinned":False},"property_descriptors":[],"primitives":[]})
    monkeypatch.setattr(slicer, "mesh_to_jsonable", lambda m: {"format":"SHIFT.MEB"})
    report=slicer.build_real_bmw_material_slice(primary,golden_path,primitive_index=0)
    assert report["ready"] is False
    assert "material-slice:primitive-not-bmw-paint" in report["blocking_reasons"]
