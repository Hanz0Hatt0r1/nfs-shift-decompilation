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
