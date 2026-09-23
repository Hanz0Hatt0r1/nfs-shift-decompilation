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
    mesh={"format":"SHIFT.MEB","vertex_count":3,"triangle_count":1,"primitives":[{"material":"vehicles/A/body.mtx","first_index":0,"index_count":3}]}
    material={"format":"SHIFT.BMT","material":{"name":"BODY","shader":"render\\shaders\\missing.fx","technique":"Default","shaderparams":[]}}
    for d,n,x in [("scenes","scene.json",scene),("meshes","mesh.json",mesh),("materials","mat.json",material)]: (root/d/n).write_text(json.dumps(x),encoding="utf-8")
    manifest=[
      {"archive":"CAR.bff","path":"vehicles/A/car.vhf","output":"scenes/scene.json","raw":"raw/a"},
      {"archive":"CAR.bff","path":"vehicles/A/body.meb","output":"meshes/mesh.json","raw":"raw/b"},
      {"archive":"CAR.bff","path":"vehicles/A/body.bmt","output":"materials/mat.json","raw":"raw/c"}]
    (root/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
    (root/"raw").mkdir(); [(root/"raw"/x).write_bytes(b"") for x in ("a","b","c")]
    r=build_render_bindings(root)
    assert r["stats"]["draw_packets"]==1
    assert r["packets"][0]["world_matrix"][3:12:4]==[1,2,3]
    assert r["packets"][0]["submeshes"][0]["material"]["unresolved_reason"]=="shader-source-not-in-IR"
