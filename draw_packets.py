from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

SCHEMA = "SHIFT.DrawPacket/1"


def norm_ref(value: str | None) -> str:
    value = str(value or "").replace("\\", "/").strip().lower()
    while value.startswith("./"):
        value = value[2:]
    while "//" in value:
        value = value.replace("//", "/")
    return value


def aliases(ref: str) -> list[str]:
    ref = norm_ref(ref)
    out = [ref] if ref else []
    if ref.endswith(".mtx"):
        out.append(ref[:-4] + ".bmt")
    elif ref.endswith(".bmt"):
        out.append(ref[:-4] + ".mtx")
    if ref.endswith(".fx"):
        out.append(ref[:-3] + ".fxh")
    elif ref.endswith(".fxh"):
        out.append(ref[:-4] + ".fx")
    return list(dict.fromkeys(out))


def build_index(records: Iterable[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    path_map: dict[str, list[dict[str, Any]]] = {}
    basename_map: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        path = norm_ref(rec.get("path"))
        if not path:
            continue
        path_map.setdefault(path, []).append(rec)
        basename_map.setdefault(PurePosixPath(path).name, []).append(rec)
    return path_map, basename_map


def resolve_ref(
    ref: str,
    path_map: dict[str, list[dict[str, Any]]],
    basename_map: dict[str, list[dict[str, Any]]],
    prefer_archive: str | None = None,
) -> list[dict[str, Any]]:
    """Resolve a game reference without claiming type semantics that are unknown."""
    hits: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for candidate in aliases(ref):
        for rec in path_map.get(candidate, []):
            key = (str(rec.get("archive", "")), str(rec.get("path", "")))
            if key not in seen:
                hits.append({
                    "archive": rec.get("archive"),
                    "path": rec.get("path"),
                    "method": "path",
                })
                seen.add(key)

    if not hits:
        candidates = [PurePosixPath(x).name for x in aliases(ref)]
        base_hits: list[dict[str, Any]] = []
        for base in candidates:
            base_hits.extend(basename_map.get(base, []))
        base_hits.sort(
            key=lambda r: (
                0 if prefer_archive and r.get("archive") == prefer_archive else 1,
                norm_ref(r.get("path")),
            )
        )
        for rec in base_hits:
            key = (str(rec.get("archive", "")), str(rec.get("path", "")))
            if key not in seen:
                hits.append({
                    "archive": rec.get("archive"),
                    "path": rec.get("path"),
                    "method": "basename",
                })
                seen.add(key)

    return hits


def _resource_ref(rec: dict[str, Any]) -> dict[str, Any]:
    return {"archive": rec.get("archive"), "path": rec.get("path")}


def compile_material(
    material_record: dict[str, Any] | None,
    material_ref: str,
    material_by_path: dict[str, list[dict[str, Any]]],
    all_basename_map: dict[str, list[dict[str, Any]]],
    texture_by_path: dict[str, list[dict[str, Any]]] | None = None,
    shader_by_path: dict[str, list[dict[str, Any]]] | None = None,
    prefer_archive: str | None = None,
    material_binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    material = (
        (material_record or {}).get("analysis", {}).get("material")
        or (material_record or {}).get("material")
        or {}
    )

    hits = resolve_ref(material_ref, material_by_path, all_basename_map, prefer_archive)

    shader_ref = norm_ref(material.get("shader"))
    shader_hits = (
        resolve_ref(
            shader_ref,
            shader_by_path or {},
            all_basename_map,
            prefer_archive,
        )
        if shader_ref
        else []
    )

    params: list[dict[str, Any]] = []
    texture_refs: list[str] = []

    for index, param in enumerate(material.get("shaderparams", []) or []):
        value = param.get("value")
        values = value if isinstance(value, list) else [value]
        texture_candidates = [
            norm_ref(v)
            for v in values
            if isinstance(v, str) and norm_ref(v).endswith(".dds")
        ]
        texture_refs.extend(x for x in texture_candidates if x)
        params.append({
            "index": index,
            "name": param.get("name"),
            "resource_type": param.get("resource_type"),
            "value": value,
            "texture_refs": texture_candidates,
        })

    texture_bindings: list[dict[str, Any]] = []
    for slot, tref in enumerate(dict.fromkeys(texture_refs)):
        texture_hits = resolve_ref(
            tref,
            texture_by_path or {},
            all_basename_map,
            prefer_archive,
        )
        binding: dict[str, Any] = {
            "slot": slot,
            "ref": tref,
            "resolved": texture_hits,
            # The BMT parser does not yet recover exact D3D9 sampler-state
            # bindings, so this is deliberately marked as inferred.
            "binding_source": "material-order-inferred",
        }
        if material_binding:
            for reflected in material_binding.get("bindings", []) or []:
                if norm_ref(reflected.get("texture")) == tref:
                    if reflected.get("d3d9_sampler_register") is not None:
                        binding["d3d9_sampler_register"] = reflected["d3d9_sampler_register"]
                        binding["sampler"] = reflected.get("sampler")
                        binding["sampler_type"] = reflected.get("sampler_type")
                        binding["binding_source"] = "fxo-ctab"
                    break

        if len(texture_hits) == 1 and texture_by_path:
            texture_records = texture_by_path.get(
                norm_ref(texture_hits[0]["path"]), []
            )
            if texture_records:
                analysis = texture_records[0].get("analysis") or {}
                if analysis.get("format") == "DDS":
                    binding["dds"] = {
                        "width": analysis.get("width"),
                        "height": analysis.get("height"),
                        "mipmaps": analysis.get("mipmaps", 1),
                        "fourcc": analysis.get("fourcc", ""),
                        "rgb_bits": analysis.get("rgb_bits"),
                        "byte_size": analysis.get("byte_size"),
                    }

        texture_bindings.append(binding)

    return {
        "ref": material_ref,
        "resolved": hits,
        "name": material.get("name"),
        "shader": (
            {"ref": shader_ref, "resolved": shader_hits}
            if shader_ref
            else None
        ),
        "shader_selection": (
            {
                "status": material_binding.get("selection_status", "none"),
                "ambiguous_candidates": material_binding.get("ambiguous_candidates", []),
                "selected_fxo": material_binding.get("selected_fxo"),
                "vertex_pair_selection_status": (
                    material_binding.get("selected_fxo", {}) or {}
                ).get("vertex_pair_selection_status", "none"),
            }
            if material_binding
            else {"status": "none", "ambiguous_candidates": []}
        ),
        "technique": material.get("technique"),
        "render_state": {
            "fog": material.get("fog"),
            "antialias": material.get("antialias"),
            "cull": material.get("cull"),
        },
        "shaderparams": params,
        "textures": texture_bindings,
    }


def build_draw_packets(
    scene_records: Iterable[dict[str, Any]],
    mesh_records: Iterable[dict[str, Any]],
    material_records: Iterable[dict[str, Any]],
    texture_records: Iterable[dict[str, Any]] = (),
    shader_records: Iterable[dict[str, Any]] = (),
    material_binding_records: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Build one neutral draw packet per VHF node/MEB resource pair."""
    scene_records = list(scene_records)
    mesh_records = list(mesh_records)
    material_records = list(material_records)
    texture_records = list(texture_records)
    shader_records = list(shader_records)
    material_binding_records = list(material_binding_records)
    material_binding_by_name = {
        str(r.get("material")): r
        for r in material_binding_records
        if r.get("material")
    }

    all_records = [*mesh_records, *material_records, *texture_records, *shader_records]
    _all_path_map, all_basename_map = build_index(all_records)
    mesh_map, _ = build_index(mesh_records)
    material_map, _ = build_index(material_records)
    texture_map, _ = build_index(texture_records)
    shader_map, _ = build_index(shader_records)

    packets: list[dict[str, Any]] = []
    unresolved_meshes: list[dict[str, Any]] = []
    unresolved_materials: list[dict[str, Any]] = []

    def emit_node(scene_rec: dict[str, Any], node: dict[str, Any]) -> None:
        prefer_archive = scene_rec.get("archive")

        for raw_mesh_ref in node.get("resources", []) or []:
            mesh_hits = resolve_ref(
                raw_mesh_ref,
                mesh_map,
                all_basename_map,
                prefer_archive,
            )
            mesh_ref = mesh_hits[0] if mesh_hits else None

            if mesh_ref is None:
                unresolved_meshes.append({
                    "scene": scene_rec.get("path"),
                    "node": node.get("name"),
                    "ref": raw_mesh_ref,
                })
                continue

            mesh_records_for_ref = mesh_map.get(
                norm_ref(mesh_ref["path"]), []
            )
            mesh_rec = mesh_records_for_ref[0] if mesh_records_for_ref else None
            analysis = (mesh_rec or {}).get("analysis") or {}
            primitives = analysis.get("primitives") or []
            packet_prims: list[dict[str, Any]] = []

            for prim_index, primitive in enumerate(primitives):
                mat_ref = primitive.get("material") or ""
                mat_hits = (
                    resolve_ref(
                        mat_ref,
                        material_map,
                        all_basename_map,
                        prefer_archive,
                    )
                    if mat_ref
                    else []
                )

                mat_rec = None
                if mat_hits:
                    material_records_for_ref = material_map.get(
                        norm_ref(mat_hits[0]["path"]), []
                    )
                    mat_rec = (
                        material_records_for_ref[0]
                        if material_records_for_ref
                        else None
                    )

                if mat_ref and not mat_hits:
                    unresolved_materials.append({
                        "scene": scene_rec.get("path"),
                        "node": node.get("name"),
                        "mesh": mesh_ref["path"],
                        "ref": mat_ref,
                    })

                packet_prims.append({
                    "index": prim_index,
                    "first_index": primitive.get("first_index", 0),
                    "index_count": primitive.get("index_count", 0),
                    "material": (
                        compile_material(
                            mat_rec,
                            mat_ref,
                            material_map,
                            all_basename_map,
                            texture_map,
                            shader_map,
                            prefer_archive,
                            material_binding_by_name.get(
                                str(
                                    (mat_rec or {}).get("analysis", {}).get("material", {}).get("name")
                                    or (mat_rec or {}).get("material", {}).get("name")
                                    or ""
                                )
                            ),
                        )
                        if mat_ref
                        else None
                    ),
                })

            material_selections = [
                (s.get("material") or {}).get("shader_selection", {})
                for s in packet_prims
            ]
            ambiguous_candidates = [
                candidate
                for selection in material_selections
                for candidate in selection.get("ambiguous_candidates", [])
            ]
            selected_fxos = [
                selection.get("selected_fxo")
                for selection in material_selections
                if selection.get("selected_fxo")
            ]
            packet_status = (
                "ambiguous"
                if any(s.get("status") == "ambiguous" for s in material_selections)
                else "unique"
                if any(s.get("status") == "unique" for s in material_selections)
                else "none"
            )
            packets.append({
                "scene": _resource_ref(scene_rec),
                "node": {
                    "name": node.get("name"),
                    "type": node.get("type"),
                    "matrix": node.get("matrix"),
                },
                "mesh": {
                    "ref": raw_mesh_ref,
                    "resolved": mesh_ref,
                    "vertex_count": analysis.get("vertex_count"),
                    "triangle_count": analysis.get("triangle_count"),
                },
                "submeshes": packet_prims,
                "shader_selection": {
                    "status": packet_status,
                    "ambiguous_candidates": ambiguous_candidates[:8],
                    "selected_fxos": selected_fxos[:8],
                },
            })

        for child in node.get("children", []) or []:
            emit_node(scene_rec, child)

    for scene_rec in scene_records:
        analysis = scene_rec.get("analysis") or {}
        for node in analysis.get("nodes", []) or []:
            emit_node(scene_rec, node)

    resolved_materials = sum(
        1
        for packet in packets
        for submesh in packet.get("submeshes", [])
        if submesh.get("material", {}).get("resolved")
    )
    texture_bindings = sum(
        len(submesh.get("material", {}).get("textures", []))
        for packet in packets
        for submesh in packet.get("submeshes", [])
    )

    return {
        "schema": SCHEMA,
        "version": 1,
        "packets": packets,
        "stats": {
            "scenes": len(scene_records),
            "draw_packets": len(packets),
            "submeshes": sum(
                len(packet.get("submeshes", [])) for packet in packets
            ),
            "resolved_materials": resolved_materials,
            "texture_bindings": texture_bindings,
            "unresolved_mesh_refs": unresolved_meshes,
            "unresolved_material_refs": unresolved_materials,
        },
    }


def load_analysis(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("resources", "rows", "analyses"):
            if isinstance(payload.get(key), list):
                return payload[key]
    raise ValueError(
        "analysis input must be a JSON list or an object containing "
        "resources/rows/analyses"
    )


def build_from_analysis(
    path: str | Path,
    shader_report: str | Path | None = None,
    material_binding_report: str | Path | None = None,
) -> dict[str, Any]:
    records = load_analysis(path)
    scenes = [
        r for r in records
        if norm_ref(r.get("path")).endswith(".vhf")
        and (r.get("analysis") or {}).get("format") == "SHIFT.VHFScene"
    ]
    meshes = [
        r for r in records
        if norm_ref(r.get("path")).endswith(".meb")
        and (r.get("analysis") or {}).get("format") == "SHIFT.MEB"
    ]
    materials = [
        r for r in records
        if norm_ref(r.get("path")).endswith(".bmt")
        and (r.get("analysis") or {}).get("format") == "SHIFT.BMT"
    ]
    textures = [
        r for r in records
        if norm_ref(r.get("path")).endswith(".dds")
        and (r.get("analysis") or {}).get("format") == "DDS"
    ]
    shaders = [
        r for r in records
        if norm_ref(r.get("path")).endswith((".fx", ".fxh"))
    ]

    material_bindings: list[dict[str, Any]] = []
    if material_binding_report:
        report = json.loads(Path(material_binding_report).read_text(encoding="utf-8"))
        material_bindings = report.get("materials", report.get("bindings", []))
        if isinstance(material_bindings, dict):
            material_bindings = [material_bindings]

    if shader_report:
        report = json.loads(
            Path(shader_report).read_text(encoding="utf-8")
        )
        for row in report.get("programs", []):
            row = dict(row)
            if row.get("path"):
                row["path"] = row["path"]
            row["analysis"] = {
                "format": "SHIFT.ShaderProgramReport",
                **row,
            }
            shaders.append(row)

    return build_draw_packets(
        scenes,
        meshes,
        materials,
        textures,
        shaders,
        material_bindings,
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Build neutral SHIFT draw packets from resource_analysis.json"
        )
    )
    ap.add_argument(
        "input",
        help="resource_analysis.json produced by shift_importer analyze-dir",
    )
    ap.add_argument("output", help="output SHIFT.DrawPacket/1 JSON")
    ap.add_argument(
        "--shader-report",
        help="optional analyze-shader-asm report JSON",
    )
    ap.add_argument(
        "--material-binding-report",
        help="optional material_linker report JSON with exact FXO sampler bindings",
    )
    args = ap.parse_args()

    result = build_from_analysis(
        args.input,
        args.shader_report,
        args.material_binding_report,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result["stats"], ensure_ascii=False, indent=2))
    unresolved = (
        result["stats"]["unresolved_mesh_refs"]
        or result["stats"]["unresolved_material_refs"]
    )
    return 1 if unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
