import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from render_pipeline import quat_matrix, mat_mul, alias_ref, build_render_bindings

def test_mtx_alias():
    assert alias_ref(r"vehicles\\A\\body.mtx")=="vehicles/a/body.bmt"
def test_vhf_quaternion_identity():
    m=quat_matrix([0,0,0,1]); assert m==[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
def test_render_binding_end_to_end(tmp_path):
    root=tmp_path
    (root/"scenes").mkdir(); (root/"meshes").mkdir(); (root/"materials").mkdir()
    scene={"format":"SHIFT.VHFScene","matrices":{"0":{"offset":"0 0 0","orientation":"0 0 0 1"},"1":{"offset":"1 2 3","orientation":"0 0 0 1","parent":"0"}},"nodes":[{"name":"BODY","type":"OBJECT","matrix":"1","resources":["vehicles/A/body.meb"]}]}
    mesh={"format":"SHIFT.MEB","vertex_count":3,"triangle_count":1,"vertex_properties":["200"],"property_layouts":[{"id":"200","name":"position","stride":12,"bytes":36,"storage":"f32x3","components":3,"normalized":False}],"primitives":[{"material":"vehicles/A/body.mtx","first_index":0,"index_count":3}]}
    material={"format":"SHIFT.BMT","material":{"name":"BODY","shader":"render\\shaders\\body.fx","technique":"Default","shaderparams":[]}}
    for d,n,x in [("scenes","scene.json",scene),("meshes","mesh.json",mesh),("materials","mat.json",material)]: (root/d/n).write_text(json.dumps(x),encoding="utf-8")
    (root/"shaders").mkdir()
    (root/"shaders"/"fx.json").write_text(json.dumps({"format":"HLSL"}),encoding="utf-8")
    (root/"raw"/"fx").parent.mkdir(parents=True,exist_ok=True)
    (root/"raw"/"fx").write_bytes(b"float4 main() : COLOR0 { return 1; }")
    manifest=[
      {"archive":"CAR.bff","path":"vehicles/A/car.vhf","output":"scenes/scene.json","raw":"raw/a"},
      {"archive":"CAR.bff","path":"vehicles/A/body.meb","output":"meshes/mesh.json","raw":"raw/b"},
      {"archive":"CAR.bff","path":"vehicles/A/body.bmt","output":"materials/mat.json","raw":"raw/c"},
      {"archive":"RENDER.bff","path":"render/shaders/body.fx","output":"shaders/fx.json","raw":"raw/fx"}]
    (root/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
    (root/"raw").mkdir(exist_ok=True); [(root/"raw"/x).write_bytes(b"") for x in ("a","b","c")]
    r=build_render_bindings(root)
    assert r["stats"]["draw_packets"]==1
    assert r["packets"][0]["world_matrix"][3:12:4]==[1,2,3]
    assert r["packets"][0]["submeshes"][0]["material"]["shader"]=="render\\shaders\\body.fx"
    assert r["packets"][0]["submeshes"][0]["material"]["selected_fxo"] is None


def test_render_binding_emits_static_draw_contract_and_normalized_mesh():
    root = Path("/tmp")
    # Reuse the end-to-end fixture without depending on persistent files by
    # constructing a minimal temporary analysis tree inline.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp/"scenes").mkdir(); (tmp/"meshes").mkdir(); (tmp/"materials").mkdir(); (tmp/"shaders").mkdir(); (tmp/"raw").mkdir()
        scene = {
            "format": "SHIFT.VHFScene",
            "matrices": {"0": {"offset": "0 0 0", "orientation": "0 0 0 1"}},
            "nodes": [{"name": "BODY", "type": "OBJECT", "matrix": "0", "resources": ["vehicles/A/body.meb"]}],
        }
        mesh = {
            "format": "SHIFT.MEB",
            "vertex_count": 3,
            "triangle_count": 1,
            "vertex_properties": ["200"],
            "property_layouts": [{
                "id": "200", "name": "position", "stride": 12, "bytes": 36,
                "storage": "f32x3", "components": 3, "normalized": False,
            }],
            "primitives": [{"material": "vehicles/A/body.mtx", "first_index": 0, "index_count": 3}],
        }
        material = {"format": "SHIFT.BMT", "material": {"name": "BODY", "shader": "render\shaders\body.fx", "technique": "Default", "shaderparams": []}}
        (tmp/"scenes/scene.json").write_text(json.dumps(scene))
        (tmp/"meshes/mesh.json").write_text(json.dumps(mesh))
        (tmp/"materials/mat.json").write_text(json.dumps(material))
        (tmp/"shaders/fx.json").write_text(json.dumps({"format":"HLSL"}))
        (tmp/"raw/fx").write_bytes(b"")
        (tmp/"raw/a").write_bytes(b""); (tmp/"raw/b").write_bytes(b""); (tmp/"raw/c").write_bytes(b"")
        manifest = [
            {"archive":"CAR.bff","path":"vehicles/A/car.vhf","output":"scenes/scene.json","raw":"raw/a"},
            {"archive":"CAR.bff","path":"vehicles/A/body.meb","output":"meshes/mesh.json","raw":"raw/b"},
            {"archive":"CAR.bff","path":"vehicles/A/body.bmt","output":"materials/mat.json","raw":"raw/c"},
            {"archive":"RENDER.bff","path":"render/shaders/body.fx","output":"shaders/fx.json","raw":"raw/fx"},
        ]
        (tmp/"manifest.json").write_text(json.dumps(manifest))
        result = build_render_bindings(tmp)
        assert result["stats"]["static_draws"] == 1
        assert result["static_draws"][0]["ready"] is False
        assert result["static_draws"][0]["mesh"]["vertex_layout"]["format"] == "SHIFT.VertexLayout/1"
        assert result["static_draws"][0]["mesh"]["vertex_count"] == 3


def test_render_binding_attaches_render_resources_contract(tmp_path):
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root/"scenes").mkdir(); (root/"meshes").mkdir(); (root/"materials").mkdir(); (root/"shaders").mkdir(); (root/"raw").mkdir()
        scene = {
            "format": "SHIFT.VHFScene",
            "matrices": {"0": {"offset": "0 0 0", "orientation": "0 0 0 1"}},
            "nodes": [{"name": "BODY", "type": "OBJECT", "matrix": "0", "resources": ["vehicles/A/body.meb"]}],
        }
        mesh = {
            "format": "SHIFT.MEB", "vertex_count": 3, "triangle_count": 1,
            "vertex_properties": ["200"],
            "property_layouts": [{
                "id": "200", "name": "position", "stride": 12, "bytes": 36,
                "storage": "f32x3", "components": 3, "normalized": False,
            }],
            "primitives": [{"material": "vehicles/A/body.bmt", "first_index": 0, "index_count": 3}],
        }
        material = {
            "format": "SHIFT.BMT",
            "material": {
                "name": "BODY",
                "shader": "render\\shaders\\body.fx",
                "technique": "Default",
                "shaderparams": [],
            },
        }
        dds = {
            "format": "DDS", "width": 64, "height": 64, "mipmaps": 1,
            "fourcc": "", "rgb_bits": 32, "byte_size": 16384,
        }
        (root/"scenes/scene.json").write_text(json.dumps(scene))
        (root/"meshes/mesh.json").write_text(json.dumps(mesh))
        (root/"materials/mat.json").write_text(json.dumps(material))
        (root/"shaders/fx.json").write_text(json.dumps({"format":"HLSL"}))
        (root/"dds.json").write_text(json.dumps(dds))
        for raw in ["scene","mesh","mat","fx","dds"]:
            (root/f"raw/{raw}").write_bytes(b"")
        manifest = [
            {"archive":"CAR.bff","path":"vehicles/A/body.vhf","output":"scenes/scene.json","raw":"raw/scene"},
            {"archive":"CAR.bff","path":"vehicles/A/body.meb","output":"meshes/mesh.json","raw":"raw/mesh"},
            {"archive":"CAR.bff","path":"vehicles/A/body.bmt","output":"materials/mat.json","raw":"raw/mat"},
            {"archive":"RENDER.bff","path":"render/shaders/body.fx","output":"shaders/fx.json","raw":"raw/fx"},
            {"archive":"CAR.bff","path":"vehicles/A/body.dds","output":"dds.json","raw":"raw/dds"},
        ]
        (root/"manifest.json").write_text(json.dumps(manifest))
        result = build_render_bindings(root)
        assert result["resources"]["format"] == "SHIFT.RenderResources/1"
        assert result["resources"]["stats"]["textures"] >= 1
        assert "stats" in result["resources"]
