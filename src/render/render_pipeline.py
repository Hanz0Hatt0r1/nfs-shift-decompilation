"""Universal SHIFT render-link stage: VHF -> MEB -> BMT -> FX/FXO -> draw bindings."""
from __future__ import annotations
import json, math, re
from pathlib import Path
from typing import Any, Mapping
from material_linker import link_material
from static_draw import build_static_draw_contract
from renderer_resources import build_resource_index
from render_command import build_render_command
from vertex_layout import build_layout_from_summary

def norm_ref(v: str) -> str:
    return re.sub(r"/+", "/", v.replace("\\","/")).lower().lstrip("./")

def alias_ref(v: str) -> str:
    n=norm_ref(v)
    if n.endswith(".mtx"): return n[:-4]+".bmt"
    return n

def shader_family(path: str) -> str:
    stem=Path(path).stem.lower()
    stem=re.sub(r"_[0-9a-f]{8,}$", "", stem)
    for prefix in ("render_shaders_","effects_particles_shaders_"):
        if stem.startswith(prefix): stem=stem[len(prefix):]; break
    return re.sub(r"[^a-z0-9]", "", stem)

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
    by_path={}
    by_base={}
    for r in rows:
        by_path.setdefault(norm_ref(r["path"]),[]).append(r)
        by_base.setdefault(Path(norm_ref(r["path"])).name,[]).append(r)
    def resolve(ref: str, prefer: str|None=None):
        n=alias_ref(ref)
        hits=by_path.get(n,[])
        if prefer:
            same=[x for x in hits if x.get("archive")==prefer]
            if same:return same[0]
        if hits: return hits[0] if len(hits)==1 else hits[0]
        hits=by_base.get(Path(n).name,[])
        if prefer:
            same=[x for x in hits if x.get("archive")==prefer]
            if same:return same[0]
        return hits[0] if hits else None

    textures=[r["path"] for r in rows if norm_ref(r["path"]).endswith(".dds")]
    scenes=[r for r in rows if norm_ref(r["path"]).endswith(".vhf")]
    meshes=[r for r in rows if norm_ref(r["path"]).endswith(".meb")]
    packets=[]; unresolved=[]; static_draws=[]; texture_bindings=[]
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
                            family=shader_family(shader_ref)
                            for rr in rows:
                                pn=norm_ref(rr["path"])
                                if pn.endswith(".fxo") and shader_family(pn)==family:
                                    fxo.append((rr["path"],_load_raw(root,rr)))
                            binding=link_material(material,fx_source,fxo_candidates=fxo,texture_paths=textures,vertex_properties=mesh.get("vertex_properties",[]))
                        else:
                            binding={"format":"SHIFT.MaterialBinding/1","material":material.get("name"),"shader":shader_ref,"selected_fxo":None,"bindings":[],"unresolved_reason":"shader-source-not-in-IR"}
                    else:
                        unresolved.append({"kind":"material","scene":scene_row["path"],"mesh":mesh_row["path"],"ref":mat_ref})
                    subs.append({"first_index":prim.get("first_index",0),"index_count":prim.get("index_count",0),"material_ref":mat_ref,"material":binding})
                world=resolve_matrix(matrices,node.get("matrix"),cache)
                packet = {
                    "scene": scene_row["path"],
                    "node": node.get("name"),
                    "node_type": node.get("type"),
                    "matrix": node.get("matrix"),
                    "world_matrix": world,
                    "mesh": {
                        "ref": mesh_row["path"],
                        "resolved": {
                            "path": mesh_row["path"],
                            "archive": mesh_row.get("archive"),
                            **(
                                {"resource_sha256": mesh_row.get("sha256")}
                                if mesh_row.get("sha256")
                                else {}
                            ),
                        },
                        "vertex_count": mesh.get("vertex_count"),
                        "triangle_count": mesh.get("triangle_count"),
                        "vertex_layout": build_layout_from_summary(mesh),
                        "skinning": mesh.get("skinning") or {},
                    },
                    "submeshes": subs,
                }
                packet["shader_selection"] = {
                    "status": (
                        "ambiguous"
                        if any(
                            (x.get("material") or {}).get("selection_status") == "ambiguous"
                            for x in subs
                        )
                        else "unique"
                        if any(
                            (x.get("material") or {}).get("selection_status") == "unique"
                            for x in subs
                        )
                        else "none"
                    )
                }
                packets.append(packet)
                static_draws.append(build_static_draw_contract(packet))
                for submesh in subs:
                    material_binding = submesh.get("material") or {}
                    for binding in material_binding.get("bindings", []) or []:
                        if binding.get("binding") == "material-texture":
                            texture_bindings.append({
                                "material_parameter": binding.get("texture_parameter"),
                                "ref": binding.get("texture"),
                                "d3d9_sampler_register": binding.get("d3d9_sampler_register"),
                                "binding_source": "fxo-ctab",
                                "min_filter": binding.get("min_filter"),
                                "mag_filter": binding.get("mag_filter"),
                                "mip_filter": binding.get("mip_filter"),
                                "address_u": binding.get("address_u"),
                                "address_v": binding.get("address_v"),
                                "address_w": binding.get("address_w"),
                                "lod_bias": binding.get("lod_bias"),
                                "max_anisotropy": binding.get("max_anisotropy"),
                                "srgb": binding.get("srgb"),
                                "linear": binding.get("linear"),
                            })
            for child in node.get("children",[]) or []: walk(child)
        for n in scene.get("nodes",[]) or []: walk(n)
    resources = build_resource_index(
        [
            {
                **row,
                "analysis": (
                    _load_json(root, row)
                    if norm_ref(row.get("path", "")).endswith(".dds")
                    and row.get("output")
                    else row.get("analysis", {})
                ),
            }
            for row in rows
        ],
        texture_bindings,
    )
    render_commands = [
        build_render_command(draw, resources)
        for draw in static_draws
    ]
    return {
        "format": "SHIFT.RenderBinding/1",
        "packets": packets,
        "static_draws": static_draws,
        "render_commands": render_commands,
        "resources": resources,
        "stats": {
            "scenes": len(scenes),
            "draw_packets": len(packets),
            "static_draws": len(static_draws),
            "render_commands": len(render_commands),
            "ready_static_draws": sum(1 for x in static_draws if x.get("ready")),
            "blocked_static_draws": sum(1 for x in static_draws if not x.get("ready")),
            "unresolved": unresolved,
        },
    }


def build_render_bindings_from_resource_instances(
    ir_root: str | Path,
    instances: list[Mapping[str, Any]],
    *,
    source_format: str | None = None,
) -> dict[str, Any]:
    """Resolve externally placed MEB instances through the generic render path.

    Each instance supplies a proven resource reference and numeric 4x4 world
    matrix.  Resource/material/shader resolution remains identical to the
    existing VHF-driven path; unsupported resource kinds stay fail-closed.
    """
    root = Path(ir_root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    rows = [r for r in manifest if "error" not in r]
    by_path: dict[str, list[dict[str, Any]]] = {}
    by_base: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_path.setdefault(norm_ref(row["path"]), []).append(row)
        by_base.setdefault(Path(norm_ref(row["path"])).name, []).append(row)

    def resolve(ref: str, prefer: str | None = None):
        normalized = alias_ref(ref)
        hits = by_path.get(normalized, [])
        if prefer:
            same = [x for x in hits if x.get("archive") == prefer]
            if same:
                return same[0]
        if hits:
            return hits[0]
        hits = by_base.get(Path(normalized).name, [])
        if prefer:
            same = [x for x in hits if x.get("archive") == prefer]
            if same:
                return same[0]
        return hits[0] if hits else None

    textures = [
        row["path"]
        for row in rows
        if norm_ref(row["path"]).endswith(".dds")
    ]
    packets: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    static_draws: list[dict[str, Any]] = []
    texture_bindings: list[dict[str, Any]] = []

    for instance_index, instance in enumerate(instances):
        resource_ref = instance.get("resource_reference")
        world_value = instance.get("world_matrix")
        source = instance.get("source") or {}
        if not isinstance(source, Mapping):
            source = {}
        admission_binding_index = source.get("admission_binding_index")

        if not resource_ref:
            unresolved.append({
                "kind": "mesh",
                "reason": "resource-reference-missing",
                "instance_index": instance_index,
                "admission_binding_index": admission_binding_index,
            })
            continue
        if not isinstance(world_value, (list, tuple)) or len(world_value) != 16:
            unresolved.append({
                "kind": "transform",
                "reason": "numeric-world-matrix-invalid",
                "ref": str(resource_ref),
                "instance_index": instance_index,
                "admission_binding_index": admission_binding_index,
            })
            continue
        try:
            world = [float(value) for value in world_value]
        except (TypeError, ValueError):
            unresolved.append({
                "kind": "transform",
                "reason": "numeric-world-matrix-invalid",
                "ref": str(resource_ref),
                "instance_index": instance_index,
                "admission_binding_index": admission_binding_index,
            })
            continue

        prefer_archive = instance.get("prefer_archive")
        mesh_row = resolve(str(resource_ref), prefer_archive)
        if not mesh_row:
            unresolved.append({
                "kind": "mesh",
                "reason": "resource-not-in-ir",
                "ref": str(resource_ref),
                "instance_index": instance_index,
                "admission_binding_index": admission_binding_index,
            })
            continue
        if not norm_ref(mesh_row["path"]).endswith(".meb"):
            unresolved.append({
                "kind": "resource-kind",
                "reason": "unsupported-scene-resource-kind",
                "ref": str(resource_ref),
                "resolved_path": mesh_row["path"],
                "instance_index": instance_index,
                "admission_binding_index": admission_binding_index,
            })
            continue

        mesh = _load_json(root, mesh_row)
        if mesh.get("format") not in {"SHIFT.MEB", None}:
            unresolved.append({
                "kind": "mesh",
                "reason": "resolved-resource-not-meb",
                "ref": str(resource_ref),
                "resolved_path": mesh_row["path"],
                "instance_index": instance_index,
                "admission_binding_index": admission_binding_index,
            })
            continue

        submeshes = []
        for prim in mesh.get("primitives", []) or []:
            material_ref = prim.get("material", "")
            material_row = resolve(material_ref, prefer_archive)
            binding = None
            if material_row:
                material_doc = _load_json(root, material_row)
                material = material_doc.get("material", material_doc)
                shader_ref = material.get("shader")
                fx_row = resolve(shader_ref) if shader_ref else None
                if fx_row:
                    fx_source = _load_raw(root, fx_row)
                    fxo = []
                    family = shader_family(shader_ref)
                    for candidate in rows:
                        candidate_path = norm_ref(candidate["path"])
                        if (
                            candidate_path.endswith(".fxo")
                            and shader_family(candidate_path) == family
                        ):
                            fxo.append(
                                (candidate["path"], _load_raw(root, candidate))
                            )
                    binding = link_material(
                        material,
                        fx_source,
                        fxo_candidates=fxo,
                        texture_paths=textures,
                        vertex_properties=mesh.get("vertex_properties", []),
                    )
                else:
                    binding = {
                        "format": "SHIFT.MaterialBinding/1",
                        "material": material.get("name"),
                        "shader": shader_ref,
                        "selected_fxo": None,
                        "bindings": [],
                        "unresolved_reason": "shader-source-not-in-IR",
                    }
            else:
                unresolved.append({
                    "kind": "material",
                    "reason": "material-not-in-ir",
                    "mesh": mesh_row["path"],
                    "ref": material_ref,
                    "instance_index": instance_index,
                    "admission_binding_index": admission_binding_index,
                })

            submeshes.append({
                "first_index": prim.get("first_index", 0),
                "index_count": prim.get("index_count", 0),
                "material_ref": material_ref,
                "material": binding,
            })

        packet = {
            "scene": source.get("scene"),
            "node": source.get("node"),
            "node_type": source.get("node_type") or "SGB_OBJECT",
            "matrix": None,
            "world_matrix": world,
            "scene_binding": dict(source),
            "mesh": {
                "ref": mesh_row["path"],
                "resolved": {
                    "path": mesh_row["path"],
                    "archive": mesh_row.get("archive"),
                    **(
                        {"resource_sha256": mesh_row.get("sha256")}
                        if mesh_row.get("sha256")
                        else {}
                    ),
                },
                "vertex_count": mesh.get("vertex_count"),
                "triangle_count": mesh.get("triangle_count"),
                "vertex_layout": build_layout_from_summary(mesh),
                "skinning": mesh.get("skinning") or {},
            },
            "submeshes": submeshes,
        }
        packet["shader_selection"] = {
            "status": (
                "ambiguous"
                if any(
                    (item.get("material") or {}).get("selection_status")
                    == "ambiguous"
                    for item in submeshes
                )
                else "unique"
                if any(
                    (item.get("material") or {}).get("selection_status")
                    == "unique"
                    for item in submeshes
                )
                else "none"
            )
        }
        packets.append(packet)
        static_draws.append(build_static_draw_contract(packet))

        for submesh in submeshes:
            material_binding = submesh.get("material") or {}
            for binding in material_binding.get("bindings", []) or []:
                if binding.get("binding") == "material-texture":
                    texture_bindings.append({
                        "material_parameter": binding.get("texture_parameter"),
                        "ref": binding.get("texture"),
                        "d3d9_sampler_register": binding.get(
                            "d3d9_sampler_register"
                        ),
                        "binding_source": "fxo-ctab",
                        "min_filter": binding.get("min_filter"),
                        "mag_filter": binding.get("mag_filter"),
                        "mip_filter": binding.get("mip_filter"),
                        "address_u": binding.get("address_u"),
                        "address_v": binding.get("address_v"),
                        "address_w": binding.get("address_w"),
                        "lod_bias": binding.get("lod_bias"),
                        "max_anisotropy": binding.get("max_anisotropy"),
                        "srgb": binding.get("srgb"),
                        "linear": binding.get("linear"),
                    })

    resources = build_resource_index(
        [
            {
                **row,
                "analysis": (
                    _load_json(root, row)
                    if norm_ref(row.get("path", "")).endswith(".dds")
                    and row.get("output")
                    else row.get("analysis", {})
                ),
            }
            for row in rows
        ],
        texture_bindings,
    )
    render_commands = [
        build_render_command(draw, resources)
        for draw in static_draws
    ]
    return {
        "format": "SHIFT.RenderBinding/1",
        "source_format": source_format,
        "packets": packets,
        "static_draws": static_draws,
        "render_commands": render_commands,
        "resources": resources,
        "stats": {
            "resource_instances": len(instances),
            "resolved_resource_instances": len(packets),
            "draw_packets": len(packets),
            "static_draws": len(static_draws),
            "render_commands": len(render_commands),
            "ready_static_draws": sum(
                1 for item in static_draws if item.get("ready")
            ),
            "blocked_static_draws": sum(
                1 for item in static_draws if not item.get("ready")
            ),
            "unresolved": unresolved,
        },
    }

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("ir_root"); ap.add_argument("output")
    a=ap.parse_args()
    out=build_render_bindings(a.ir_root)
    Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(out["stats"],ensure_ascii=False,indent=2))
