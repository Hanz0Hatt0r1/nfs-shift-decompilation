"""Universal SHIFT render-link stage: VHF -> MEB -> BMT -> FX/FXO -> draw bindings."""
from __future__ import annotations
import json, math
from pathlib import Path
from typing import Any
from material_linker import link_material

def norm_ref(v: str) -> str:
    return v.replace("\\","/").lower().lstrip("./")

def alias_ref(v: str) -> str:
    n=norm_ref(v)
    return n[:-4]+".bmt" if n.endswith(".mtx") else n

def _vec(s: str, n: int) -> list[float]:
    return [float(x) for x in s.replace(",", " ").split()][:n]

def quat_matrix(q: list[float]) -> list[float]:
    x,y,z,w=q
    return [
        1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w), 0,
        2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w), 0,
        2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y), 0,
        0,0,0,1,
    ]

def mat_mul(a: list[float], b: list[float]) -> list[float]:
    return [sum(a[r*4+k]*b[k*4+c] for k in range(4)) for r in range(4) for c in range(4)]

def matrix_from_vhf(rec: dict[str,Any]) -> list[float]:
    m=quat_matrix(_vec(rec.get("orientation","0 0 0 1"),4))
    p=_vec(rec.get("offset","0 0 0"),3)
    m[3],m[7],m[11]=p
    return m

def resolve_matrix(matrices: dict[str,dict[str,Any]], matrix_id: str|None, cache: dict[str,list[float]]) -> list[float]:
    key=str(matrix_id if matrix_id is not None else "0")
    if key in cache: return cache[key]
    rec=matrices.get(key, {})
    local=matrix_from_vhf(rec)
    parent=rec.get("parent")
    world=mat_mul(resolve_matrix(matrices,str(parent),cache),local) if parent is not None else local
    cache[key]=world
    return world

def _load_json(root: Path, row: dict[str,Any]) -> dict[str,Any]:
    p=root/row["output"]
    return json.loads(p.read_text(encoding="utf-8"))

def _load_raw(root: Path, row: dict[str,Any]) -> bytes:
    return (root/row["raw"]).read_bytes()

def build_render_bindings(ir_root: str|Path) -> dict[str,Any]:
    root=Path(ir_root)
    manifest=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    rows=[r for r in manifest if "error" not in r]
    by_path={norm_ref(r["path"]):r for r in rows}
    by_base={}
    for r in rows: by_base.setdefault(Path(norm_ref(r["path"])).name,[]).append(r)
    def resolve(ref: str, prefer: str|None=None):
        n=alias_ref(ref)
        if n in by_path: return by_path[n]
        hits=by_base.get(Path(n).name,[])
        if prefer:
            same=[x for x in hits if x.get("archive")==prefer]
            if same:return same[0]
        return hits[0] if len(hits)==1 else (hits[0] if hits else None)

    textures=[r["path"] for r in rows if norm_ref(r["path"]).endswith(".dds")]
    scenes=[r for r in rows if norm_ref(r["path"]).endswith(".vhf")]
    meshes=[r for r in rows if norm_ref(r["path"]).endswith(".meb")]
    packets=[]; unresolved=[]
    for scene_row in scenes:
        scene=_load_json(root,scene_row)
        matrices=scene.get("matrices",{}); cache={}
        def walk(node):
            mesh_refs=node.get("resources",[]) or []
            for mr in mesh_refs:
                mesh_row=resolve(mr,scene_row.get("archive"))
                if not mesh_row:
                    unresolved.append({"kind":"mesh","scene":scene_row["path"],"node":node.get("name"),"ref":mr}); continue
                mesh=_load_json(root,mesh_row)
                subs=[]
                for prim in mesh.get("primitives",[]) or []:
                    mat_ref=prim.get("material","")
                    mat_row=resolve(mat_ref,scene_row.get("archive"))
                    binding=None
                    if mat_row:
                        mat=_load_json(root,mat_row)
                        material=mat.get("material",mat)
                        shader_ref=material.get("shader")
                        fx_row=resolve(shader_ref) if shader_ref else None
                        if fx_row:
                            fx_source=_load_raw(root,fx_row)
                            fxo=[]
                            stem=Path(norm_ref(shader_ref)).stem
                            prefix=f"render/shaders/cache/render_shaders_{stem}_"
                            for rr in rows:
                                pn=norm_ref(rr["path"])
                                if pn.startswith(prefix) and pn.endswith(".fxo"):
                                    fxo.append((rr["path"],_load_raw(root,rr)))
                            binding=link_material(material,fx_source,fxo,textures)
                        else:
                            binding={"format":"SHIFT.MaterialBinding/1","material":material.get("name"),"shader":shader_ref,"selected_fxo":None,"bindings":[],"unresolved_reason":"shader-source-not-in-IR"}
                    else:
                        unresolved.append({"kind":"material","scene":scene_row["path"],"mesh":mesh_row["path"],"ref":mat_ref})
                    subs.append({"first_index":prim.get("first_index",0),"index_count":prim.get("index_count",0),"material_ref":mat_ref,"material":binding})
                world=resolve_matrix(matrices,node.get("matrix"),cache)
                packets.append({"scene":scene_row["path"],"node":node.get("name"),"node_type":node.get("type"),"matrix":node.get("matrix"),"world_matrix":world,"mesh":mesh_row["path"],"submeshes":subs})
            for child in node.get("children",[]) or []: walk(child)
        for n in scene.get("nodes",[]) or []: walk(n)
    return {"format":"SHIFT.RenderBinding/1","packets":packets,"stats":{"scenes":len(scenes),"draw_packets":len(packets),"unresolved":unresolved}}

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("ir_root"); ap.add_argument("output")
    a=ap.parse_args()
    out=build_render_bindings(a.ir_root)
    Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(out["stats"],ensure_ascii=False,indent=2))
