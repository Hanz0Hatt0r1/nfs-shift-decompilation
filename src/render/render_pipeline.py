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
    unmatched_runtime_admissions = [
        binding_index
        for binding_index, count in sorted(
            runtime_application_counts.items()
        )
        if count <= 0
    ]
    runtime_join_blockers.extend(
        f"runtime-shader-admission:binding-{binding_index}:not-applied"
        for binding_index in unmatched_runtime_admissions
    )
    runtime_join_blockers = list(dict.fromkeys(runtime_join_blockers))
    runtime_shader_join = {
        "format": "SHIFT.IMBRuntimeRenderBindingJoin/1",
        "status": (
            "not-supplied"
            if runtime_shader_admission is None
            else "ready"
            if runtime_admissions and not runtime_join_blockers
            else "blocked"
        ),
        "ready": (
            None
            if runtime_shader_admission is None
            else bool(runtime_admissions)
            and not runtime_join_blockers
        ),
        "supplied_admission_count": len(runtime_admissions),
        "applied_admission_count": sum(
            count > 0 for count in runtime_application_counts.values()
        ),
        "application_count": sum(runtime_application_counts.values()),
        "application_counts": {
            str(key): value
            for key, value in sorted(runtime_application_counts.items())
        },
        "unmatched_binding_indices": unmatched_runtime_admissions,
        "blocking_reasons": runtime_join_blockers,
        "boundary": {
            "resource_identity": "archive + IMB path + decoded SHA-256",
            "primitive_identity": (
                "primitive index + first/index/primitive counts"
            ),
            "material_identity": (
                "source material reference + BMT path/SHA + shader path"
            ),
            "admission_scope": "resource-level shader identity; reusable by scene instances",
        },
    }

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



RUNTIME_SHADER_ADMISSION_FORMAT = "SHIFT.IMBRuntimeShaderAdmission/1"


def _runtime_admission_rows(
    runtime_shader_admission: Mapping[str, Any] | None,
) -> list[Mapping[str, Any]]:
    if runtime_shader_admission is None:
        return []
    if (
        runtime_shader_admission.get("format")
        != RUNTIME_SHADER_ADMISSION_FORMAT
    ):
        raise ValueError(
            "runtime shader admission must be "
            "SHIFT.IMBRuntimeShaderAdmission/1"
        )
    return [
        row
        for row in (
            runtime_shader_admission.get("admitted_bindings") or []
        )
        if isinstance(row, Mapping)
        and row.get("shader_selection_admitted") is True
    ]


def _primitive_draw_range(primitive: Mapping[str, Any]) -> dict[str, int] | None:
    try:
        first_index = int(primitive.get("first_index"))
        index_count = int(primitive.get("index_count"))
    except (TypeError, ValueError):
        return None
    if first_index < 0 or index_count <= 0 or index_count % 3:
        return None
    triangle_count = primitive.get("triangle_count")
    if triangle_count is None:
        primitive_count = index_count // 3
    else:
        try:
            primitive_count = int(triangle_count)
        except (TypeError, ValueError):
            return None
        if primitive_count * 3 != index_count:
            return None
    return {
        "first_index": first_index,
        "index_count": index_count,
        "primitive_count": primitive_count,
    }


def _same_draw_range(left: Any, right: Any) -> bool:
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        return False
    try:
        return all(
            int(left.get(key)) == int(right.get(key))
            for key in ("first_index", "index_count", "primitive_count")
        )
    except (TypeError, ValueError):
        return False


def _primitive_runtime_admission(
    rows: list[Mapping[str, Any]],
    *,
    mesh_row: Mapping[str, Any],
    primitive_index: int,
    primitive: Mapping[str, Any],
) -> tuple[Mapping[str, Any] | None, list[str]]:
    resource_path = norm_ref(str(mesh_row.get("path") or ""))
    resource_sha = str(mesh_row.get("sha256") or "").lower()
    archive = str(mesh_row.get("archive") or "")
    candidates: list[Mapping[str, Any]] = []
    for row in rows:
        try:
            row_primitive = int(row.get("primitive_index"))
        except (TypeError, ValueError):
            continue
        if (
            norm_ref(str(row.get("imb_path") or "")) == resource_path
            and str(row.get("imb_sha256") or "").lower() == resource_sha
            and str(row.get("archive") or "") == archive
            and row_primitive == primitive_index
        ):
            candidates.append(row)

    if not candidates:
        return None, []
    if len(candidates) != 1:
        return None, [
            f"runtime-shader-admission:primitive-{primitive_index}:"
            f"multiple-rows:{len(candidates)}"
        ]

    row = candidates[0]
    reasons: list[str] = []
    draw_range = _primitive_draw_range(primitive)
    if draw_range is None:
        reasons.append(
            f"runtime-shader-admission:primitive-{primitive_index}:"
            "source-draw-range-invalid"
        )
    elif not _same_draw_range(row.get("draw_range"), draw_range):
        reasons.append(
            f"runtime-shader-admission:primitive-{primitive_index}:"
            "draw-range-mismatch"
        )

    material_ref = norm_ref(str(primitive.get("material") or ""))
    if norm_ref(str(row.get("material_reference") or "")) != material_ref:
        reasons.append(
            f"runtime-shader-admission:primitive-{primitive_index}:"
            "material-reference-mismatch"
        )

    return (None if reasons else row), reasons


def _validate_runtime_admission_material(
    row: Mapping[str, Any],
    *,
    material_row: Mapping[str, Any],
    shader_ref: Any,
    primitive_index: int,
) -> list[str]:
    reasons: list[str] = []
    admission_bmt = norm_ref(str(row.get("bmt") or ""))
    material_path = norm_ref(str(material_row.get("path") or ""))
    if admission_bmt and admission_bmt != material_path:
        reasons.append(
            f"runtime-shader-admission:primitive-{primitive_index}:"
            "bmt-path-mismatch"
        )
    admission_bmt_sha = str(row.get("bmt_sha256") or "").lower()
    material_sha = str(material_row.get("sha256") or "").lower()
    if admission_bmt_sha:
        if not material_sha:
            reasons.append(
                f"runtime-shader-admission:primitive-{primitive_index}:"
                "bmt-sha256-not-in-ir"
            )
        elif admission_bmt_sha != material_sha:
            reasons.append(
                f"runtime-shader-admission:primitive-{primitive_index}:"
                "bmt-sha256-mismatch"
            )
    admission_shader = norm_ref(str(row.get("shader") or ""))
    if admission_shader and admission_shader != norm_ref(str(shader_ref or "")):
        reasons.append(
            f"runtime-shader-admission:primitive-{primitive_index}:"
            "shader-path-mismatch"
        )
    return reasons


def build_render_bindings_from_resource_instances(
    ir_root: str | Path,
    instances: list[Mapping[str, Any]],
    *,
    source_format: str | None = None,
    runtime_shader_admission: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve externally placed MEB/IMB instances through the generic render path.

    Each instance supplies a proven resource reference and numeric 4x4 world
    matrix. Resource/material/shader resolution remains identical to the
    existing VHF-driven path. IMB uses its independent source-backed neutral
    geometry adapter; unsupported resource kinds stay fail-closed.
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
    runtime_admissions = _runtime_admission_rows(runtime_shader_admission)
    runtime_application_counts = {
        int(row.get("binding_index")): 0
        for row in runtime_admissions
        if row.get("binding_index") is not None
    }
    runtime_join_blockers: list[str] = []
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
        resolved_norm = norm_ref(mesh_row["path"])
        mesh_source_kind: str
        mesh_adapter_format: str | None = None
        if resolved_norm.endswith(".meb"):
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
            mesh_source_kind = "MEB"
        elif resolved_norm.endswith(".imb"):
            from imb_neutral_geometry import build_imb_neutral_geometry

            try:
                neutral = build_imb_neutral_geometry(_load_raw(root, mesh_row))
            except (KeyError, OSError, ValueError) as exc:
                unresolved.append({
                    "kind": "mesh",
                    "reason": "imb-neutral-geometry-decode-failed",
                    "detail": str(exc),
                    "ref": str(resource_ref),
                    "resolved_path": mesh_row["path"],
                    "instance_index": instance_index,
                    "admission_binding_index": admission_binding_index,
                })
                continue
            if neutral.get("ready") is not True:
                unresolved.append({
                    "kind": "mesh",
                    "reason": "imb-neutral-geometry-blocked",
                    "blocking_reasons": list(
                        neutral.get("blocking_reasons") or []
                    ),
                    "ref": str(resource_ref),
                    "resolved_path": mesh_row["path"],
                    "instance_index": instance_index,
                    "admission_binding_index": admission_binding_index,
                })
                continue
            mesh = neutral["mesh"]
            mesh_source_kind = "IMB"
            mesh_adapter_format = str(neutral.get("format"))
        else:
            unresolved.append({
                "kind": "resource-kind",
                "reason": "unsupported-scene-resource-kind",
                "ref": str(resource_ref),
                "resolved_path": mesh_row["path"],
                "instance_index": instance_index,
                "admission_binding_index": admission_binding_index,
            })
            continue

        submeshes = []
        for primitive_index, prim in enumerate(
            mesh.get("primitives", []) or []
        ):
            material_ref = prim.get("material", "")
            primitive_admission = None
            primitive_admission_reasons: list[str] = []
            if mesh_source_kind == "IMB" and runtime_admissions:
                (
                    primitive_admission,
                    primitive_admission_reasons,
                ) = _primitive_runtime_admission(
                    runtime_admissions,
                    mesh_row=mesh_row,
                    primitive_index=primitive_index,
                    primitive=prim,
                )
                runtime_join_blockers.extend(
                    primitive_admission_reasons
                )
            material_row = resolve(material_ref, prefer_archive)
            binding = None
            if material_row:
                material_doc = _load_json(root, material_row)
                material = material_doc.get("material", material_doc)
                shader_ref = material.get("shader")
                if primitive_admission is not None:
                    material_reasons = _validate_runtime_admission_material(
                        primitive_admission,
                        material_row=material_row,
                        shader_ref=shader_ref,
                        primitive_index=primitive_index,
                    )
                    if material_reasons:
                        runtime_join_blockers.extend(material_reasons)
                        primitive_admission = None
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
                        runtime_admission=primitive_admission,
                    )
                    if primitive_admission is not None:
                        runtime_index = primitive_admission.get(
                            "binding_index"
                        )
                        if runtime_index is not None:
                            runtime_index = int(runtime_index)
                            runtime_application_counts[runtime_index] = (
                                runtime_application_counts.get(
                                    runtime_index, 0
                                )
                                + 1
                            )
                        runtime_selection = (
                            binding.get("runtime_selection") or {}
                        )
                        if runtime_selection.get("ready") is not True:
                            runtime_join_blockers.extend(
                                "runtime-shader-admission:"
                                + str(reason)
                                for reason in (
                                    runtime_selection.get(
                                        "blocking_reasons"
                                    )
                                    or []
                                )
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
                "primitive_index": primitive_index,
                "first_index": prim.get("first_index", 0),
                "index_count": prim.get("index_count", 0),
                "material_ref": material_ref,
                "runtime_shader_admission": (
                    {
                        "binding_index": primitive_admission.get(
                            "binding_index"
                        ),
                        "shader_selection_admitted": True,
                        "selection_status": (
                            (binding or {}).get("selection_status")
                        ),
                        "selection_source": (
                            (binding or {}).get("selection_source")
                        ),
                    }
                    if primitive_admission is not None
                    else None
                ),
                "runtime_shader_admission_blocking_reasons": (
                    primitive_admission_reasons
                ),
                "material": binding,
            })

        vertex_layout = build_layout_from_summary(mesh)
        if mesh_source_kind == "IMB":
            vertex_layout = {
                **vertex_layout,
                "source": "IMB",
                "source_adapter": mesh_adapter_format,
            }

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
                "vertex_layout": vertex_layout,
                "skinning": mesh.get("skinning") or {},
                "source_kind": mesh_source_kind,
                "neutral_adapter_format": mesh_adapter_format,
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
        "runtime_shader_join": runtime_shader_join,
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