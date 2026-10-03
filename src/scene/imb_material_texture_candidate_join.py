"""Narrow unresolved material candidates using exact BMT/FX/DDS texture evidence.

This stage is deliberately fail-closed.  BMT texture parameters are linked to FX
sampler names, then to draw-local CTAB sampler registers.  DDS payload SHA-256
and header-derived resource descriptors are compared against captured texture
identity/creation metadata.  Descriptor compatibility is never promoted to
resource identity; it can only contradict a candidate or keep it unresolved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Iterable, Mapping

from imb_material_constant_candidate_join import (
    _materialize_bffs,
    _norm,
    _valid_sha,
    load_materials_by_sha,
    load_verified_fxo_pairs,
    resolve_input_path,
)
from material_linker import parse_fx_samplers
from shift_importer import BFF

FORMAT = "SHIFT.IMBMaterialTextureCandidateJoin/1"
CONSTANT_FORMAT = "SHIFT.IMBMaterialConstantCandidateJoin/1"
DRAW_FORMAT = "SHIFT.D3D9TargetDrawLocalEvidence/1"
FXO_FORMAT = "SHIFT.IMBFXOPairProvenance/1"


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


def _dds_descriptor(data: bytes) -> dict[str, Any]:
    if len(data) < 128 or data[:4] != b"DDS ":
        raise ValueError("not a DDS resource")
    size = struct.unpack_from("<I", data, 4)[0]
    pf_size = struct.unpack_from("<I", data, 76)[0]
    if size != 124 or pf_size != 32:
        raise ValueError("invalid DDS header")
    height = struct.unpack_from("<I", data, 12)[0]
    width = struct.unpack_from("<I", data, 16)[0]
    depth = struct.unpack_from("<I", data, 24)[0]
    mipmaps = struct.unpack_from("<I", data, 28)[0] or 1
    fourcc = struct.unpack_from("<I", data, 84)[0]
    rgb_bits = struct.unpack_from("<I", data, 88)[0]
    r_mask, g_mask, b_mask, a_mask = struct.unpack_from("<4I", data, 92)
    caps2 = struct.unpack_from("<I", data, 112)[0]

    d3d_format = None
    if fourcc:
        d3d_format = fourcc
    elif rgb_bits == 32:
        masks = (r_mask, g_mask, b_mask, a_mask)
        known = {
            (0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000): 21,  # A8R8G8B8
            (0x00FF0000, 0x0000FF00, 0x000000FF, 0x00000000): 22,  # X8R8G8B8
            (0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000): 32,  # A8B8G8R8
            (0x000000FF, 0x0000FF00, 0x00FF0000, 0x00000000): 33,  # X8B8G8R8
        }
        d3d_format = known.get(masks)
    elif rgb_bits == 16:
        masks = (r_mask, g_mask, b_mask, a_mask)
        known = {
            (0xF800, 0x07E0, 0x001F, 0x0000): 23,  # R5G6B5
            (0x7C00, 0x03E0, 0x001F, 0x8000): 25,  # A1R5G5B5
            (0x0F00, 0x00F0, 0x000F, 0xF000): 26,  # A4R4G4B4
        }
        d3d_format = known.get(masks)

    cube = bool(caps2 & 0x00000200)
    return {
        "resource_type_name": "cube_texture" if cube else "texture2d",
        "width": width,
        "height": height,
        "depth": depth or None,
        "edge_length": width if cube and width == height else None,
        "format": d3d_format,
        "level_count": mipmaps,
        "dds_fourcc": fourcc or None,
        "dds_rgb_bits": rgb_bits or None,
    }


def _wanted_bmt_hashes(constant_report: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    for draw in constant_report.get("draws") or []:
        if not isinstance(draw, Mapping):
            continue
        for candidate in draw.get("candidate_results") or []:
            if not isinstance(candidate, Mapping):
                continue
            digest = _valid_sha(candidate.get("bmt_sha256"))
            if digest:
                result.add(digest)
    return result


def _texture_paths(materials: Mapping[str, Mapping[str, Any]]) -> set[str]:
    result: set[str] = set()
    for row in materials.values():
        material = row.get("material") if isinstance(row, Mapping) else None
        if not isinstance(material, Mapping):
            continue
        for param in material.get("shaderparams") or []:
            if not isinstance(param, Mapping):
                continue
            typ = str(param.get("type") or param.get("resource_type") or "").upper()
            value = param.get("value")
            if "TEXTURE" in typ and isinstance(value, str) and value:
                result.add(_norm(value))
    return result


def _shader_paths(materials: Mapping[str, Mapping[str, Any]]) -> set[str]:
    result = set()
    for row in materials.values():
        material = row.get("material") if isinstance(row, Mapping) else None
        if not isinstance(material, Mapping):
            continue
        shader = material.get("shader")
        if isinstance(shader, str) and shader:
            result.add(_norm(shader))
    return result


def load_fx_sources_by_path(
    inputs: Iterable[str | Path],
    wanted_paths: set[str],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    if not wanted_paths:
        return {}
    with ExitStack() as stack:
        for path, source_input in _materialize_bffs(inputs, stack):
            try:
                archive = stack.enter_context(BFF(path))
            except Exception:
                continue
            for entry in archive.entries:
                key = _norm(entry.path)
                if key not in wanted_paths:
                    continue
                try:
                    payload = archive.extract_entry(entry, type2="lzx")
                except Exception:
                    continue
                digest = hashlib.sha256(payload).hexdigest()
                row = grouped[key].setdefault(digest, {
                    "path": str(entry.path).replace("\\", "/"),
                    "payload_sha256": digest,
                    "payload": payload,
                    "occurrences": [],
                })
                row["occurrences"].append({
                    "source_input": source_input,
                    "archive": archive.path.name,
                    "entry_path": str(entry.path).replace("\\", "/"),
                    "entry_index": int(entry.index),
                })
    return {
        path: sorted(rows.values(), key=lambda row: str(row["payload_sha256"]))
        for path, rows in grouped.items()
    }


def load_dds_by_path(
    inputs: Iterable[str | Path],
    wanted_paths: set[str],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    if not wanted_paths:
        return {}
    with ExitStack() as stack:
        for path, source_input in _materialize_bffs(inputs, stack):
            try:
                archive = stack.enter_context(BFF(path))
            except Exception:
                continue
            for entry in archive.entries:
                key = _norm(entry.path)
                if key not in wanted_paths:
                    continue
                try:
                    payload = archive.extract_entry(entry, type2="lzx")
                    descriptor = _dds_descriptor(payload)
                except Exception:
                    continue
                digest = hashlib.sha256(payload).hexdigest()
                row = grouped[key].setdefault(digest, {
                    "resource_path": str(entry.path).replace("\\", "/"),
                    "resource_sha256": digest,
                    "descriptor": descriptor,
                    "occurrences": [],
                })
                row["occurrences"].append({
                    "source_input": source_input,
                    "archive": archive.path.name,
                    "entry_path": str(entry.path).replace("\\", "/"),
                    "entry_index": int(entry.index),
                })
    return {
        path: sorted(rows.values(), key=lambda row: str(row["resource_sha256"]))
        for path, rows in grouped.items()
    }


def _runtime_samplers(draw: Mapping[str, Any]) -> dict[str, list[Mapping[str, Any]]]:
    result: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in draw.get("sampler_bindings") or []:
        if not isinstance(row, Mapping):
            continue
        name = str(row.get("sampler_name") or "")
        if name:
            result[name].append(row)
    return dict(result)


def _descriptor_value_equal(key: str, left: Any, right: Any) -> bool:
    if key == "resource_type_name":
        return str(left or "").lower() == str(right or "").lower()
    try:
        return int(left) == int(right)
    except (TypeError, ValueError):
        return left == right


def compare_dds_to_runtime(
    static_resource: Mapping[str, Any],
    runtime_binding: Mapping[str, Any],
) -> dict[str, Any]:
    static_path = _norm(static_resource.get("resource_path"))
    static_sha = _valid_sha(static_resource.get("resource_sha256"))
    portable = runtime_binding.get("portable_resource_identity")
    portable = portable if isinstance(portable, Mapping) else {}
    runtime_path = _norm(portable.get("resource_path")) if portable.get("resource_path") else ""
    runtime_sha = _valid_sha(portable.get("resource_sha256"))

    if runtime_path and runtime_sha:
        if runtime_path != static_path:
            return {
                "status": "exact-resource-identity-contradiction",
                "confidence": "exact-runtime-path-sha",
                "reason": "resource-path-mismatch",
            }
        if runtime_sha != static_sha:
            return {
                "status": "exact-resource-identity-contradiction",
                "confidence": "exact-runtime-path-sha",
                "reason": "resource-sha256-mismatch",
            }
        return {
            "status": "exact-resource-identity-match",
            "confidence": "exact-runtime-path-sha",
            "reason": None,
        }

    static_descriptor = static_resource.get("descriptor")
    static_descriptor = static_descriptor if isinstance(static_descriptor, Mapping) else {}
    runtime_descriptor = runtime_binding.get("descriptor")
    runtime_descriptor = runtime_descriptor if isinstance(runtime_descriptor, Mapping) else {}
    compared = []
    mismatches = []
    for key in (
        "resource_type_name", "width", "height", "depth", "edge_length", "format", "level_count"
    ):
        left = static_descriptor.get(key)
        right = runtime_descriptor.get(key)
        if left is None or right is None:
            continue
        compared.append(key)
        if not _descriptor_value_equal(key, left, right):
            mismatches.append({"field": key, "static": left, "runtime": right})
    if mismatches:
        return {
            "status": "exact-resource-descriptor-contradiction",
            "confidence": "exact-dds-header-vs-create-descriptor",
            "compared_fields": compared,
            "mismatches": mismatches,
        }
    if compared:
        return {
            "status": "descriptor-compatible-not-identity",
            "confidence": "descriptor-only",
            "compared_fields": compared,
            "mismatches": [],
        }
    return {
        "status": "insufficient-runtime-texture-evidence",
        "confidence": "none",
        "compared_fields": [],
        "mismatches": [],
    }


def _candidate_pair(candidate: Mapping[str, Any]) -> tuple[str, str] | None:
    pair = candidate.get("shader_pair")
    pair = pair if isinstance(pair, Mapping) else {}
    vertex = _valid_sha(pair.get("vertex_shader_sha256"))
    pixel = _valid_sha(pair.get("pixel_shader_sha256"))
    return (vertex, pixel) if vertex and pixel else None


def evaluate_candidate(
    candidate: Mapping[str, Any],
    draw: Mapping[str, Any],
    *,
    materials_by_sha: Mapping[str, Mapping[str, Any]],
    fx_sources_by_path: Mapping[str, list[Mapping[str, Any]]],
    dds_by_path: Mapping[str, list[Mapping[str, Any]]],
    fxo_pairs: Mapping[tuple[str, str], list[Mapping[str, Any]]],
) -> dict[str, Any]:
    bmt_sha = _valid_sha(candidate.get("bmt_sha256"))
    pair = _candidate_pair(candidate)
    base = {
        "content_group_sha256": _valid_sha(candidate.get("content_group_sha256")),
        "bmt_sha256": bmt_sha,
        "constant_status": candidate.get("status"),
        "shader_pair": {
            "vertex_shader_sha256": pair[0] if pair else None,
            "pixel_shader_sha256": pair[1] if pair else None,
        },
    }
    material_row = materials_by_sha.get(bmt_sha or "")
    if not isinstance(material_row, Mapping) or material_row.get("parse_status") != "parsed":
        return {**base, "status": "insufficient-material-texture-evidence", "blocking_reasons": ["exact-bmt-payload-not-available"], "samplers": []}
    if pair is None or not fxo_pairs.get(pair):
        return {**base, "status": "insufficient-material-texture-evidence", "blocking_reasons": ["verified-fxo-pair-not-available"], "samplers": []}

    material = material_row.get("material") or {}
    shader_path = _norm(material.get("shader"))
    fx_rows = list(fx_sources_by_path.get(shader_path) or [])
    if len(fx_rows) != 1:
        reason = "exact-fx-source-not-available" if not fx_rows else "shader-source-path-has-distinct-payloads"
        return {**base, "status": "insufficient-material-texture-evidence", "blocking_reasons": [reason], "samplers": []}

    params = {
        str(row.get("name")): row
        for row in (material.get("shaderparams") or [])
        if isinstance(row, Mapping) and row.get("name")
    }
    runtime = _runtime_samplers(draw)
    sampler_rows = []
    for source_sampler in parse_fx_samplers(fx_rows[0].get("payload") or b""):
        texture_parameter = str(source_sampler.get("texture_parameter") or "")
        param = params.get(texture_parameter)
        if not isinstance(param, Mapping):
            continue
        typ = str(param.get("type") or param.get("resource_type") or "").upper()
        texture_path = param.get("value")
        if "TEXTURE" not in typ or not isinstance(texture_path, str) or not texture_path:
            continue
        name = str(source_sampler.get("sampler") or "")
        runtime_rows = runtime.get(name) or []
        static_rows = list(dds_by_path.get(_norm(texture_path)) or [])
        witness = {
            "sampler": name,
            "texture_parameter": texture_parameter,
            "texture_path": texture_path.replace("\\", "/"),
            "source_used": source_sampler.get("source_used") is True,
            "runtime_binding_count": len(runtime_rows),
            "static_resource_identity_count": len(static_rows),
            "comparisons": [],
        }
        if not runtime_rows:
            witness["status"] = "insufficient-runtime-sampler-binding"
        elif len(runtime_rows) != 1:
            witness["status"] = "ambiguous-runtime-sampler-binding"
        elif not static_rows:
            witness["status"] = "exact-dds-resource-not-available"
        else:
            comparison_rows = []
            for static_row in static_rows:
                compared = compare_dds_to_runtime(static_row, runtime_rows[0])
                comparison_rows.append({
                    "resource_path": static_row.get("resource_path"),
                    "resource_sha256": static_row.get("resource_sha256"),
                    "descriptor": static_row.get("descriptor"),
                    "occurrences": list(static_row.get("occurrences") or []),
                    **compared,
                })
            witness["comparisons"] = comparison_rows
            statuses = {str(row.get("status")) for row in comparison_rows}
            if "exact-resource-identity-match" in statuses:
                witness["status"] = "exact-resource-identity-match"
            elif statuses and statuses <= {
                "exact-resource-identity-contradiction",
                "exact-resource-descriptor-contradiction",
            }:
                witness["status"] = "exact-resource-contradiction"
            else:
                witness["status"] = "insufficient-resource-identity"
        sampler_rows.append(witness)

    material_samplers = [row for row in sampler_rows if row.get("source_used") is True]
    if not material_samplers:
        status = "insufficient-material-texture-evidence"
        blockers = ["no-source-used-material-texture-samplers"]
    elif any(row.get("status") == "exact-resource-contradiction" for row in material_samplers):
        status = "exact-material-texture-contradiction"
        blockers = []
    elif all(row.get("status") == "exact-resource-identity-match" for row in material_samplers):
        status = "exact-material-texture-match"
        blockers = []
    else:
        status = "insufficient-material-texture-evidence"
        blockers = ["material-texture-identity-incomplete"]

    return {
        **base,
        "status": status,
        "blocking_reasons": blockers,
        "shader_source": {
            "path": material.get("shader"),
            "payload_sha256": fx_rows[0].get("payload_sha256"),
            "occurrences": list(fx_rows[0].get("occurrences") or []),
        },
        "verified_fxo_occurrence_count": len(fxo_pairs.get(pair) or []),
        "bmt_occurrences": list(material_row.get("occurrences") or []),
        "samplers": sampler_rows,
    }


def _constant_survivors(draw: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = [row for row in (draw.get("candidate_results") or []) if isinstance(row, Mapping)]
    if draw.get("resolution_status") == "material-constant-conflict-no-survivor":
        return rows
    return [
        row for row in rows
        if row.get("status") != "exact-material-constant-contradiction"
    ]


def build_material_texture_candidate_join(
    constant_report: Mapping[str, Any],
    draw_local: Mapping[str, Any],
    *,
    materials_by_sha: Mapping[str, Mapping[str, Any]],
    fx_sources_by_path: Mapping[str, list[Mapping[str, Any]]],
    dds_by_path: Mapping[str, list[Mapping[str, Any]]],
    fxo_pairs: Mapping[tuple[str, str], list[Mapping[str, Any]]],
) -> dict[str, Any]:
    if constant_report.get("format") != CONSTANT_FORMAT:
        raise ValueError(f"constant report must be {CONSTANT_FORMAT}")
    if draw_local.get("format") != DRAW_FORMAT:
        raise ValueError(f"draw-local report must be {DRAW_FORMAT}")

    draws_by_event = {
        row.get("event_index"): row
        for row in (draw_local.get("draws") or [])
        if isinstance(row, Mapping) and isinstance(row.get("event_index"), int)
    }
    rows = []
    resolution_counts: Counter[str] = Counter()
    candidate_counts: Counter[str] = Counter()

    for constant_draw in constant_report.get("draws") or []:
        if not isinstance(constant_draw, Mapping):
            continue
        if constant_draw.get("resolution_status") == "single-candidate-by-exact-material-constants":
            continue
        event_index = constant_draw.get("event_index")
        runtime_draw = draws_by_event.get(event_index)
        candidates = _constant_survivors(constant_draw)
        if runtime_draw is None:
            evaluated = []
            resolution = "draw-local-evidence-missing"
            selected = None
        else:
            evaluated = [
                evaluate_candidate(
                    candidate,
                    runtime_draw,
                    materials_by_sha=materials_by_sha,
                    fx_sources_by_path=fx_sources_by_path,
                    dds_by_path=dds_by_path,
                    fxo_pairs=fxo_pairs,
                )
                for candidate in candidates
            ]
            for candidate in evaluated:
                candidate_counts[str(candidate.get("status"))] += 1
            matches = [row for row in evaluated if row.get("status") == "exact-material-texture-match"]
            contradictions = [row for row in evaluated if row.get("status") == "exact-material-texture-contradiction"]
            insufficient = [row for row in evaluated if row.get("status") == "insufficient-material-texture-evidence"]
            selected = None
            if len(matches) == 1 and len(contradictions) == len(evaluated) - 1 and not insufficient:
                resolution = "single-candidate-by-exact-material-textures"
                selected = matches[0]
            elif len(matches) > 1:
                resolution = "ambiguous-multiple-exact-material-texture-matches"
            elif matches and insufficient:
                resolution = "ambiguous-unexcluded-texture-candidates"
            elif not matches and contradictions and len(insufficient) == 1:
                resolution = "single-survivor-by-texture-contradiction-unproven"
            elif not matches and contradictions and not insufficient:
                resolution = "material-texture-conflict-no-survivor"
            else:
                resolution = "insufficient-material-texture-evidence"
        resolution_counts[resolution] += 1
        rows.append({
            "event_index": event_index,
            "frame": constant_draw.get("frame"),
            "constant_resolution_status": constant_draw.get("resolution_status"),
            "input_candidate_count": int(constant_draw.get("input_candidate_count") or len(constant_draw.get("candidate_results") or [])),
            "constant_survivor_count": len(candidates),
            "resolution_status": resolution,
            "selected_content_group_sha256": selected.get("content_group_sha256") if selected else None,
            "candidate_results": evaluated,
        })

    rows.sort(key=lambda row: int(row["event_index"]) if isinstance(row.get("event_index"), int) else 2**63 - 1)
    resolved = sum(row.get("resolution_status") == "single-candidate-by-exact-material-textures" for row in rows)
    return {
        "format": FORMAT,
        "version": 1,
        "status": "observed" if rows else "no-unresolved-material-candidates",
        "summary": {
            "input_unresolved_draw_count": len(rows),
            "single_candidate_draw_count": resolved,
            "remaining_unresolved_draw_count": len(rows) - resolved,
            "resolution_status_counts": dict(sorted(resolution_counts.items())),
            "candidate_status_counts": dict(sorted(candidate_counts.items())),
            "loaded_bmt_identity_count": len(materials_by_sha),
            "loaded_fx_path_count": len(fx_sources_by_path),
            "loaded_dds_path_count": len(dds_by_path),
            "verified_fxo_pair_identity_count": len(fxo_pairs),
        },
        "draws": rows,
        "boundary": {
            "proof_chain": "exact BMT SHA -> exact FX source path/bytes -> source sampler name -> verified FXO pair -> draw-local CTAB sampler register -> exact DDS path/bytes/header",
            "positive_identity": "requires runtime resource_path + resource_sha256 to exactly match the referenced DDS path + raw payload SHA-256",
            "descriptor_policy": "DDS header versus texture-creation descriptor equality is compatibility only; mismatch is an exact contradiction, equality is not identity proof",
            "selection_rule": "one exact texture identity match is accepted only when every other surviving candidate is exactly contradicted",
            "single_survivor_policy": "descriptor contradictions may narrow to one survivor but never promote that survivor without exact positive resource identity",
            "duplicate_policy": "byte-identical FX/DDS occurrences retain all provenance; distinct payloads at one exact path remain ambiguous",
            "ranking_policy": "file order, frequency, pointer identity and descriptor similarity are not proof",
            "render_admission": False,
            "capture_requirement": "none; missing portable texture identity remains conditional until offline contradictions are exhausted",
        },
    }


def build_report(
    constant_report: Mapping[str, Any],
    draw_local: Mapping[str, Any],
    fxo_report: Mapping[str, Any],
    corpus: Iterable[str | Path],
) -> dict[str, Any]:
    if fxo_report.get("format") != FXO_FORMAT:
        raise ValueError(f"FXO provenance must be {FXO_FORMAT}")
    corpus = list(corpus)
    wanted_bmts = _wanted_bmt_hashes(constant_report)
    materials = load_materials_by_sha(corpus, wanted_bmts)
    shader_paths = _shader_paths(materials)
    texture_paths = _texture_paths(materials)
    fx_sources = load_fx_sources_by_path(corpus, shader_paths)
    dds = load_dds_by_path(corpus, texture_paths)
    fxo_pairs = load_verified_fxo_pairs(corpus, fxo_report)
    report = build_material_texture_candidate_join(
        constant_report,
        draw_local,
        materials_by_sha=materials,
        fx_sources_by_path=fx_sources,
        dds_by_path=dds,
        fxo_pairs=fxo_pairs,
    )
    report["corpus_inputs"] = [str(value) for value in corpus]
    report["wanted_bmt_sha256s"] = sorted(wanted_bmts)
    report["wanted_shader_paths"] = sorted(shader_paths)
    report["wanted_texture_paths"] = sorted(texture_paths)
    report["missing_bmt_sha256s"] = sorted(wanted_bmts - set(materials))
    report["missing_shader_paths"] = sorted(shader_paths - set(fx_sources))
    report["missing_texture_paths"] = sorted(texture_paths - set(dds))
    report["evidence_sha256"] = _canonical_hash({
        "summary": report["summary"],
        "draws": report["draws"],
    })
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("material_constant_join")
    parser.add_argument("draw_local_evidence")
    parser.add_argument("fxo_pair_provenance")
    parser.add_argument("output")
    parser.add_argument("--corpus", action="append", required=True)
    args = parser.parse_args(argv)

    constant_report = json.loads(resolve_input_path(args.material_constant_join).read_text(encoding="utf-8"))
    draw_local = json.loads(resolve_input_path(args.draw_local_evidence).read_text(encoding="utf-8"))
    fxo_report = json.loads(resolve_input_path(args.fxo_pair_provenance).read_text(encoding="utf-8"))
    report = build_report(constant_report, draw_local, fxo_report, args.corpus)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
