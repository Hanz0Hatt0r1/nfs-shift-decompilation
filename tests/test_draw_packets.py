from pathlib import Path
import json
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from draw_packets import (
    build_draw_packets,
    build_from_analysis,
    resolve_ref,
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
