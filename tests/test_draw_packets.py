from pathlib import Path
import json
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from draw_packets import (
    build_draw_packets,
    build_from_analysis,
    resolve_ref,
    resolve_bind_skeleton,
)


def _records():
    scene = [{
        "archive": "VEHICLES.bff",
        "path": "vehicles/test/test.vhf",
        "analysis": {
            "format": "SHIFT.VHFScene",
            "nodes": [{
                "name": "ROOT",
                "type": "HIERARCHY",
                "matrix": "0",
                "children": [{
                    "name": "BODY",
                    "type": "OBJECT",
                    "matrix": "0",
                    "resources": ["vehicles\\test\\body.meb"],
                }],
            }],
        },
    }]
    mesh = [{
        "archive": "VEHICLES.bff",
        "path": "vehicles/test/body.meb",
        "analysis": {
            "format": "SHIFT.MEB",
            "vertex_count": 3,
            "triangle_count": 1,
            "primitives": [{
                "material": "vehicles/test/body.mtx",
                "first_index": 0,
                "index_count": 3,
            }],
        },
    }]
    material = [{
        "archive": "VEHICLES.bff",
        "path": "vehicles/test/body.bmt",
        "analysis": {
            "format": "SHIFT.BMT",
            "material": {
                "name": "BODY",
                "shader": "shaders/body.fx",
                "technique": "Default",
                "shaderparams": [
                    {
                        "name": "Diffuse",
                        "resource_type": "texture",
                        "value": "textures/body.dds",
                    },
                    {
                        "name": "Tint",
                        "resource_type": "float4",
                        "value": [1, 1, 1, 1],
                    },
                ],
            },
        },
    }]
    texture = [{
        "archive": "VEHICLES.bff",
        "path": "textures/body.dds",
        "analysis": {
            "format": "DDS",
            "width": 1024,
            "height": 512,
            "mipmaps": 9,
            "fourcc": "DXT5",
            "byte_size": 12345,
        },
    }]
    shader = [{
        "archive": "VEHICLES.bff",
        "path": "shaders/body.fx",
        "analysis": {"format": "HLSL"},
    }]
    return scene, mesh, material, texture, shader


def _skeleton_records():
    bab = {
        "archive": "ANIMATION.bff",
        "path": "animation/test/test.bab",
        "analysis": {
            "format": "SHIFT.BAB",
            "header": {"name": "test"},
            "bones": [
                {
                    "index": 0,
                    "name": "Hips",
                    "rotation_quaternion_xyzw": [0, 0, 0, 1],
                    "translation": [1, 2, 3],
                },
                {
                    "index": 1,
                    "name": "Spine",
                    "rotation_quaternion_xyzw": [0, 0, 0, 1],
                    "translation": [0, 1, 0],
                },
            ],
            "animation_payload_offset": 128,
            "animation_payload_size": 16,
            "animation_payload_sha256": "deadbeef",
        },
    }
    bas = {
        "archive": "VEHICLES.bff",
        "path": "vehicles/test/test.bas",
        "analysis": {
            "format": "SHIFT.BAS",
            "name": "test",
            "nodes": [
                {"index": 0, "name": "Hips", "parent": None},
                {"index": 1, "name": "Spine", "parent": 0},
            ],
        },
    }
    return [bab], [bas]


def test_resolve_bind_skeleton_requires_exact_meb_bone_names():
    bab, bas = _skeleton_records()
    mesh_analysis = {
        "format": "SHIFT.MEB",
        "skeleton": {"num_bones": 2, "bone_names": ["Hips", "Spine"]},
    }
    bind, resolution = resolve_bind_skeleton(mesh_analysis, bab, bas)
    assert resolution["status"] == "resolved"
    assert resolution["method"] == "exact-meb-bone-name-set"
    assert bind["format"] == "SHIFT.BindSkeleton/1"
    assert bind["coverage"] == 1.0
    assert bind["links"][1]["parent"] == "Hips"
    assert bind["animation_payload"]["decoded"] is False
    assert bind["animation_payload"]["sha256"] == "deadbeef"


def test_resolve_bind_skeleton_rejects_ambiguous_pairs():
    bab, bas = _skeleton_records()
    duplicate = dict(bab[0])
    duplicate["path"] = "animation/alt/test.bab"
    bind, resolution = resolve_bind_skeleton(
        {
            "format": "SHIFT.MEB",
            "skeleton": {"num_bones": 2, "bone_names": ["Hips", "Spine"]},
        },
        [bab[0], duplicate],
        bas,
    )
    assert bind is None
    assert resolution["status"] == "ambiguous"
    assert resolution["reason"] == "multiple-exact-pairs"
    assert len(resolution["candidate_pairs"]) == 2


def test_build_draw_packet_attaches_exact_bind_skeleton():
    scene, mesh, material, texture, shader = _records()
    mesh[0]["analysis"]["skinning"] = {
        "has_weights": True,
        "has_indices": True,
        "skinned": True,
        "valid": True,
        "bone_count": 2,
    }
    mesh[0]["analysis"]["vertex_properties"] = ["200", "310", "580"]
    mesh[0]["analysis"]["property_layouts"] = [
        {
            "id": "200",
            "name": "position",
            "payload_offset": 0,
            "stride": 12,
            "bytes": 36,
            "storage": "f32x3",
            "components": 3,
            "normalized": False,
        },
        {
            "id": "310",
            "name": "bone_weights",
            "payload_offset": 36,
            "stride": 16,
            "bytes": 48,
            "storage": "f32x4",
            "components": 4,
            "normalized": False,
        },
        {
            "id": "580",
            "name": "vertex_index_hint",
            "payload_offset": 84,
            "stride": 4,
            "bytes": 12,
            "storage": "u8x4",
            "components": 4,
            "normalized": False,
        },
    ]
    mesh[0]["analysis"]["skeleton"] = {
        "num_bones": 2,
        "num_chars": 11,
        "bone_names": ["Hips", "Spine"],
    }
    bab, bas = _skeleton_records()

    result = build_draw_packets(
        scene,
        mesh,
        material,
        texture,
        shader,
        bab_records=bab,
        bas_records=bas,
    )
    packet = result["packets"][0]
    assert packet["bind_skeleton"]["coverage"] == 1.0
    assert packet["skeleton_resolution"]["status"] == "resolved"
    assert result["stats"]["resolved_skeletons"] == 1
    assert not result["stats"]["unresolved_skeletons"]
    assert result["packets"][0]["static_draw"]["format"] == "SHIFT.StaticDraw/1"
    assert result["stats"]["blocked_static_draws"] == 1


def test_build_from_analysis_passes_bab_and_bas_records(tmp_path):
    scene, mesh, material, texture, shader = _records()
    mesh[0]["analysis"]["skinning"] = {
        "has_weights": True,
        "has_indices": True,
        "skinned": True,
        "valid": True,
        "bone_count": 2,
    }
    mesh[0]["analysis"]["vertex_properties"] = ["200", "310", "580"]
    mesh[0]["analysis"]["skeleton"] = {
        "num_bones": 2,
        "num_chars": 11,
        "bone_names": ["Hips", "Spine"],
    }
    bab, bas = _skeleton_records()
    analysis = tmp_path / "resource_analysis.json"
    analysis.write_text(
        json.dumps(scene + mesh + material + texture + shader + bab + bas),
        encoding="utf-8",
    )
    result = build_from_analysis(analysis)
    assert result["stats"]["resolved_skeletons"] == 1
    assert result["packets"][0]["bind_skeleton"]["format"] == "SHIFT.BindSkeleton/1"


def test_path_and_legacy_alias_resolution():
    _, mesh, material, texture, shader = _records()
    records = mesh + material + texture + shader
    path_map = {}
    base_map = {}
    from draw_packets import build_index

    path_map, base_map = build_index(records)
    hits = resolve_ref(
        "vehicles/test/body.mtx", path_map, base_map, "VEHICLES.bff"
    )
    assert hits[0]["path"] == "vehicles/test/body.bmt"
    assert hits[0]["method"] == "path"


def test_build_draw_packet_links_vhf_meb_bmt_dds():
    scene, mesh, material, texture, shader = _records()
    material_binding = [{
        "material": "BODY",
        "bindings": [{
            "sampler": "sDiffuse",
            "sampler_type": "sampler2D",
            "texture": "textures/body.dds",
            "d3d9_sampler_register": 3,
        }],
        "selection_status": "ambiguous",
        "permutation_identity": {"format": "SHIFT.ShaderPermutationIdentity/1", "identity_sha256": "id"},
        "ambiguous_candidates": [
            {"file": "a.fxo", "program_offset": 100},
            {"file": "b.fxo", "program_offset": 200},
        ],
        "selected_fxo": {
            "file": "a.fxo",
            "program_offset": 100,
            "vertex_pair_selection_status": "ambiguous",
        },
    }]
    result = build_draw_packets(
        scene, mesh, material, texture, shader, [*material_binding]
    )

    assert result["schema"] == "SHIFT.DrawPacket/1"
    assert result["stats"]["draw_packets"] == 1
    assert result["stats"]["submeshes"] == 1
    assert result["stats"]["resolved_materials"] == 1
    assert result["stats"]["texture_bindings"] == 1
    assert not result["stats"]["unresolved_mesh_refs"]
    assert not result["stats"]["unresolved_material_refs"]

    packet = result["packets"][0]
    assert packet["mesh"]["resolved"]["path"].endswith("body.meb")
    material_ir = packet["submeshes"][0]["material"]
    assert material_ir["resolved"][0]["path"].endswith("body.bmt")
    assert material_ir["shader"]["resolved"][0]["path"].endswith("body.fx")
    assert material_ir["textures"][0]["dds"]["fourcc"] == "DXT5"
    assert material_ir["textures"][0]["binding_source"] == "fxo-ctab"
    assert material_ir["textures"][0]["d3d9_sampler_register"] == 3
    assert material_ir["textures"][0]["sampler"] == "sDiffuse"
    assert material_ir["textures"][0]["sampler_type"] == "sampler2D"
    assert material_ir["shader_selection"]["status"] == "ambiguous"
    assert len(material_ir["shader_selection"]["ambiguous_candidates"]) == 2
    assert material_ir["shader_selection"]["vertex_pair_selection_status"] == "ambiguous"
    assert packet["shader_selection"]["status"] == "ambiguous"
    assert packet["submeshes"][0]["material"]["shader_selection"]["permutation_identity"]["identity_sha256"] == "id"


def test_build_from_analysis_and_cli(tmp_path):
    scene, mesh, material, texture, shader = _records()
    analysis = tmp_path / "resource_analysis.json"
    analysis.write_text(
        json.dumps(scene + mesh + material + texture + shader),
        encoding="utf-8",
    )
    result = build_from_analysis(analysis)
    assert result["stats"]["draw_packets"] == 1

    output = tmp_path / "draw_packets.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "draw_packets.py"),
            str(analysis),
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "SHIFT.DrawPacket/1"
    assert payload["packets"][0]["submeshes"][0]["index_count"] == 3


def test_cli_material_binding_report_reaches_draw_packet(tmp_path):
    scene, mesh, material, texture, shader = _records()
    analysis = tmp_path / "resource_analysis.json"
    analysis.write_text(
        json.dumps(scene + mesh + material + texture + shader),
        encoding="utf-8",
    )
    report = tmp_path / "material_bindings.json"
    report.write_text(
        json.dumps({
            "materials": [{
                "material": "BODY",
                "selection_status": "unique",
                "selected_fxo": {
                    "file": "body.fxo",
                    "program_offset": 100,
                    "vertex_pair_selection_status": "unique",
                },
                "bindings": [{
                    "sampler": "s7",
                    "sampler_type": "sampler2D",
                    "texture": "textures/body.dds",
                    "d3d9_sampler_register": 7,
                }],
            }]
        }),
        encoding="utf-8",
    )
    output = tmp_path / "draw_packets.json"
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "draw_packets.py"),
            str(analysis),
            str(output),
            "--material-binding-report",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    binding = payload["packets"][0]["submeshes"][0]["material"]["textures"][0]
    assert binding["d3d9_sampler_register"] == 7
    assert binding["sampler"] == "s7"
    assert binding["binding_source"] == "fxo-ctab"
    assert payload["packets"][0]["shader_selection"]["status"] == "unique"


def test_draw_packet_does_not_infer_texture_slot_from_material_order():
    scene, mesh, material, texture, shader = _records()
    result = build_draw_packets(scene, mesh, material, texture, shader)
    binding = result["packets"][0]["submeshes"][0]["material"]["textures"][0]
    assert binding["slot"] is None
    assert binding["binding_source"] == "unresolved"
    assert binding["material_parameter"] == "Diffuse"


def test_draw_packet_carries_explicit_vertex_layout():
    scene, mesh, material, texture, shader = _records()
    mesh[0]["analysis"]["vertex_properties"] = ["200", "220", "130"]
    result = build_draw_packets(scene, mesh, material, texture, shader)
    layout = result["packets"][0]["mesh"]["vertex_layout"]
    assert layout["format"] == "SHIFT.VertexLayout/1"
    assert {x["property_id"] for x in layout["attributes"]} == {"200", "220", "130"}
    assert result["packets"][0]["mesh"]["skinning"] == {}


def test_draw_packet_preserves_external_sampler_requirements():
    scene, mesh, material, texture, shader = _records()
    material_binding = [{
        "material": "BODY",
        "bindings": [
            {"binding": "external-or-specialised", "sampler": "environmentMap", "sampler_type": "samplerCUBE", "d3d9_sampler_register": 3},
        ],
        "selection_status": "unique",
        "shader_pair": {"vertex_bindings": [{"property_id": "200", "target_location": 0}]},
    }]
    result = build_draw_packets(scene, mesh, material, texture, shader, material_binding)
    sel = result["packets"][0]["submeshes"][0]["material"]["shader_selection"]
    assert sel["external_samplers"][0]["sampler"] == "environmentMap"
    assert sel["vertex_bindings"][0]["target_location"] == 0


def test_draw_packet_attaches_static_draw_contract():
    scene, mesh, material, texture, shader = _records()
    mesh[0]["analysis"]["vertex_properties"] = ["200"]
    result = build_draw_packets(scene, mesh, material, texture, shader)
    packet = result["packets"][0]
    contract = packet["static_draw"]
    assert contract["format"] == "SHIFT.StaticDraw/1"
    assert contract["mesh"]["vertex_count"] == 3
    assert contract["ready"] is False
    assert "shader-selection:none" in contract["blocking_reasons"]
    assert result["stats"]["draw_packets"] == 1
    assert result["stats"]["blocked_static_draws"] == 1


def test_resource_ref_preserves_content_addressed_identity():
    from draw_packets import _resource_ref

    result = _resource_ref({
        "archive": "BMW_M3_E36.bff",
        "path": "vehicles/bmw/body.meb",
        "sha256": "abc",
        "size": 300764,
    })
    assert result == {
        "archive": "BMW_M3_E36.bff",
        "path": "vehicles/bmw/body.meb",
        "resource_sha256": "abc",
        "resource_size": 300764,
    }


def test_draw_packet_preserves_meb_property_descriptors():
    scene, mesh, material, texture, shader = _records()
    mesh[0]["analysis"]["property_descriptors"] = [
        {"id": "200", "offset": 88, "words": [2, 0, 0], "raw_hex": "020000000000000000000000"},
        {"id": "460", "offset": 42700, "words": [4, 6, 0], "raw_hex": "040000000600000000000000"},
    ]
    result = build_draw_packets(scene, mesh, material, texture, shader)
    descriptors = result["packets"][0]["mesh"]["property_descriptors"]
    assert descriptors == mesh[0]["analysis"]["property_descriptors"]


def _bmw_paint_compile_material(binding_rows=None, specializations=None, material_ref="vehicles/BMW_M3_E36/BMW_M3_E36_PAINT.mtx"):
    from draw_packets import compile_material

    rows = binding_rows if binding_rows is not None else [
        {
            "texture_parameter": "diffuseTexture",
            "sampler": "diffuseMap",
            "d3d9_sampler_register": 1,
            "min_filter": "Linear", "mag_filter": "Linear", "mip_filter": "Linear",
            "address_u": "Wrap", "address_v": "Wrap", "srgb": True,
            "binding": "material-texture",
        },
        {
            "texture_parameter": "specularTexture",
            "sampler": "specularMap",
            "d3d9_sampler_register": 2,
            "min_filter": "Linear", "mag_filter": "Linear", "mip_filter": "Linear",
            "address_u": "Wrap", "address_v": "Wrap", "srgb": True,
            "binding": "material-texture",
        },
        {
            "texture_parameter": "scratchControlTexture",
            "sampler": "scratchControlMap",
            "d3d9_sampler_register": 4,
            "min_filter": "Linear", "mag_filter": "Linear", "mip_filter": "None",
            "address_u": "Clamp", "address_v": "Clamp", "srgb": False,
            "binding": "material-texture",
        },
        {
            "sampler": "environmentMap",
            "d3d9_sampler_register": 3,
            "sampler_type": "samplerCube",
            "binding": "external-or-specialised",
        },
        {
            "sampler": "sShadowMap_f1_0",
            "d3d9_sampler_register": 0,
            "sampler_type": "sampler2D",
            "binding": "external-or-specialised",
        },
    ]
    material = {
        "name": "BMW_M3_E36_PAINT",
        "shader": "bodywork.fx",
        "specializations": specializations or ["USE_FRESNEL", "ALLOW_VINYLS", "DIRT_SCRATCH"],
        "shaderparams": [
            {"name": "diffuseTexture", "resource_type": "EPT_TEXTURE", "value": "COMMON_PAINT.dds"},
            {"name": "specularTexture", "resource_type": "EPT_TEXTURE", "value": "COMMON_PAINT_SPECULAR.dds"},
            {"name": "scratchControlTexture", "resource_type": "EPT_TEXTURE", "value": "COMMON_BLANK.dds"},
        ],
    }
    return compile_material(
        {"analysis": {"material": material}},
        material_ref,
        {},
        {},
        {},
        {},
        None,
        {"bindings": rows, "selected_fxo": {"specialization_matched": specializations or ["USE_FRESNEL", "ALLOW_VINYLS", "DIRT_SCRATCH"]}},
    )


def test_compile_material_enforces_exact_bmw_paint_contract():
    material = _bmw_paint_compile_material()
    assert material["paint_contract"]["ready"] is True
    assert material["blocking_reasons"] == []


def test_compile_material_blocks_bmw_paint_contract_on_missing_sampler():
    rows = _bmw_paint_compile_material(binding_rows=[])
    assert rows["paint_contract"]["ready"] is False
    assert "paint-contract:not-ready" in rows["blocking_reasons"]


def test_non_bmw_material_does_not_activate_paint_contract():
    material = _bmw_paint_compile_material(material_ref="vehicles/other/PAINT.mtx")
    assert material["paint_contract"] is None
    assert material["blocking_reasons"] == []


def test_compile_material_enforces_bmw_paint_shader_gate():
    from draw_packets import compile_material
    material = {
        "name": "BMW_M3_E36_PAINT",
        "shader": "bodywork.fx",
        "specializations": ["USE_FRESNEL", "ALLOW_VINYLS", "DIRT_SCRATCH"],
        "shaderparams": [
            {"name": "diffuseTexture", "resource_type": "EPT_TEXTURE", "value": "COMMON_PAINT.dds"},
            {"name": "specularTexture", "resource_type": "EPT_TEXTURE", "value": "COMMON_PAINT_SPECULAR.dds"},
            {"name": "scratchControlTexture", "resource_type": "EPT_TEXTURE", "value": "COMMON_BLANK.dds"},
        ],
    }
    selection = {
        "status": "ambiguous",
        "ambiguous_candidates": [{"file": "a.fxo"}, {"file": "b.fxo"}],
        "selected_fxo": None,
    }
    result = compile_material(
        {"analysis": {"material": material}},
        "vehicles/BMW_M3_E36/BMW_M3_E36_PAINT.mtx",
        {}, {}, {}, {}, None,
        {
            "bindings": [],
            "selection_status": selection["status"],
            "ambiguous_candidates": selection["ambiguous_candidates"],
            "selected_fxo": selection["selected_fxo"],
        },
    )
    assert result["paint_shader_gate"]["ready"] is False
    assert any(x.startswith("paint-shader:shader-selection:") for x in result["blocking_reasons"])


def test_static_draw_propagates_bmw_paint_shader_gate_blocker():
    packet = {
        "scene": {},
        "node": {"name": "BODY"},
        "mesh": {
            "ref": "vehicles/BMW_M3_E36/body.meb",
            "vertex_count": 1,
            "triangle_count": 1,
            "vertex_layout": {
                "format": "SHIFT.VertexLayout/1",
                "buffer_stride": 12,
                "attributes": [],
            },
        },
        "submeshes": [{
            "first_index": 0,
            "index_count": 3,
            "material": {
                "name": "BMW_M3_E36_PAINT",
                "paint_contract": {"ready": True, "blocking_reasons": []},
                "paint_shader_gate": {
                    "ready": False,
                    "blocking_reasons": ["shader-selection:not-unique"],
                },
            },
        }],
    }
    report = build_static_draw_contract(packet)
    assert report["ready"] is False
    assert "shader-selection:not-unique" in report["blocking_reasons"]
