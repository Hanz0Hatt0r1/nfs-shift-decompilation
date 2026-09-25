"""Select the exact BMW shader permutation from a runtime D3D9 trace.

Static BMT/FX/FXO analysis can leave multiple equivalent candidates. Once the
runtime capture contains the created VS/PS byte identity, this module matches
that identity back to the static FXO candidates without inventing a permutation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWRuntimeShaderSelection/1"

from bmw_runtime_shader_join import _runtime_draw_states
from runtime_resource_identity import match_resource_identity


def _candidate_rows(material_input: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if isinstance(material_input.get("material_binding"), Mapping):
        rows = material_input["material_binding"].get("fxo_candidates")
    else:
        rows = material_input.get("fxo_candidates")
    return [row for row in (rows or []) if isinstance(row, Mapping)]


def _runtime_identity(frame: Mapping[str, Any]) -> Mapping[str, Any] | None:
    identity = frame.get("shader_permutation_identity")
    return identity if isinstance(identity, Mapping) else None


def _same_resource(material_input: Mapping[str, Any], frame: Mapping[str, Any]) -> bool | None:
    provenance = material_input.get("provenance") or {}
    mesh = provenance.get("mesh_entry") if isinstance(provenance, Mapping) else None
    binding = frame.get("vertex_declaration") or frame.get("binding") or {}
    if not isinstance(mesh, Mapping) or not isinstance(binding, Mapping):
        return None
    expected_sha = mesh.get("sha256") or mesh.get("resource_sha256")
    expected_path = mesh.get("path")
    matched, _status = match_resource_identity(
        binding,
        expected_sha256=expected_sha,
        expected_path=expected_path,
    )
    return matched

def _candidate_identity_matches(
    candidate: Mapping[str, Any],
    runtime_identity: Mapping[str, Any],
) -> tuple[int, list[str]]:
    reasons: list[str] = []
    runtime_id = runtime_identity.get("identity_sha256")
    candidate_id = (
        (candidate.get("permutation_identity") or {}).get("identity_sha256")
        if isinstance(candidate.get("permutation_identity"), Mapping)
        else None
    )
    if runtime_id and candidate_id and str(runtime_id) == str(candidate_id):
        reasons.append("identity_sha256")
        return 100, reasons

    runtime_pair = runtime_identity.get("pair_byte_sha256")
    candidate_pair = candidate.get("pair_sha256")
    if runtime_pair and candidate_pair and str(runtime_pair) == str(candidate_pair):
        reasons.append("pair_byte_sha256")
        return 90, reasons

    payload = runtime_identity.get("payload") or {}
    vertex = payload.get("vertex") if isinstance(payload, Mapping) else {}
    pixel = payload.get("pixel") if isinstance(payload, Mapping) else {}
    runtime_vertex = (
        vertex.get("byte_sha256") if isinstance(vertex, Mapping) else None
    )
    runtime_pixel = (
        pixel.get("byte_sha256") if isinstance(pixel, Mapping) else None
    )
    matched = 0
    if runtime_vertex and candidate.get("vertex_sha256") and str(runtime_vertex) == str(candidate.get("vertex_sha256")):
        matched += 1
        reasons.append("vertex_byte_sha256")
    if runtime_pixel and candidate.get("pixel_sha256") and str(runtime_pixel) == str(candidate.get("pixel_sha256")):
        matched += 1
        reasons.append("pixel_byte_sha256")
    if matched == 2:
        return 80, reasons
    if matched == 1:
        return 40, reasons
    return 0, reasons



def _expected_external_stages(material_input: Mapping[str, Any]) -> list[int]:
    binding = material_input.get("material_binding")
    rows = (
        binding.get("bindings")
        if isinstance(binding, Mapping)
        else material_input.get("bindings")
    )
    stages: set[int] = set()
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        if row.get("binding") != "external-or-specialised":
            continue
        register = row.get("d3d9_sampler_register")
        if register is None:
            continue
        try:
            stages.add(int(register))
        except (TypeError, ValueError):
            continue
    return sorted(stages)


def _texture_stage_status(
    frame: Mapping[str, Any],
    stages: list[int],
) -> tuple[bool, list[int]]:
    if not stages:
        return True, []
    latest: dict[int, Any] = {}
    for row in (frame.get("active_texture_bindings") or frame.get("texture_bindings") or []):
        if not isinstance(row, Mapping):
            continue
        try:
            stage = int(row.get("stage"))
        except (TypeError, ValueError):
            continue
        latest[stage] = row.get("texture_ptr")
    missing = [stage for stage in stages if not latest.get(stage)]
    return not missing, missing




def _texture_stage_contract(
    frame: Mapping[str, Any],
    stages: list[int],
    expected_types: Mapping[int, str],
) -> tuple[bool, list[str]]:
    if not stages:
        return True, []
    latest: dict[int, Mapping[str, Any]] = {}
    for row in (frame.get("active_texture_bindings") or frame.get("texture_bindings") or []):
        if not isinstance(row, Mapping):
            continue
        try:
            stage = int(row.get("stage"))
        except (TypeError, ValueError):
            continue
        latest[stage] = row
    reasons: list[str] = []
    for stage in stages:
        row = latest.get(stage)
        if not row or not row.get("texture_ptr"):
            reasons.append(f"runtime:texture-stage-{stage}:missing")
            continue
        wanted = expected_types.get(stage)
        descriptor = row.get("resource_descriptor")
        observed = (
            descriptor.get("resource_type_name")
            if isinstance(descriptor, Mapping)
            else row.get("resource_type_name")
        )
        if wanted and observed and str(observed).lower() != str(wanted).lower():
            reasons.append(
                f"runtime:texture-stage-{stage}:type-mismatch:{observed}:{wanted}"
            )
    return not reasons, reasons

def select_runtime_shader(
    material_input: Mapping[str, Any],
    runtime_report: Mapping[str, Any],
    *,
    require_same_resource: bool = True,
) -> dict[str, Any]:
    if runtime_report.get("format") != "SHIFT.D3D9RuntimeBindingEvidence/1":
        raise ValueError("input is not SHIFT.D3D9RuntimeBindingEvidence/1")

    candidates = _candidate_rows(material_input)
    expected_external_stages = _expected_external_stages(material_input)
    expected_external_types: dict[int, str] = {}
    binding = material_input.get("material_binding")
    binding_rows = (
        binding.get("bindings")
        if isinstance(binding, Mapping)
        else material_input.get("bindings")
    )
    for row in binding_rows or []:
        if not isinstance(row, Mapping) or row.get("binding") != "external-or-specialised":
            continue
        try:
            register = int(row.get("d3d9_sampler_register"))
        except (TypeError, ValueError):
            continue
        sampler_type = str(row.get("sampler_type") or "").lower()
        if sampler_type == "samplercube":
            expected_external_types[register] = "cube_texture"
        elif sampler_type == "sampler2d":
            expected_external_types[register] = "texture2d"
    if not candidates:
        return {
            "format": FORMAT,
            "status": "not-found",
            "ready": False,
            "blocking_reasons": ["material:fxo-candidates-missing"],
            "candidate_count": 0,
            "runtime_frame_count": len(runtime_report.get("frames") or []),
            "matches": [],
            "required_external_texture_stages": expected_external_stages,
        }

    matches: list[dict[str, Any]] = []
    for frame, state, state_source in _runtime_draw_states(runtime_report):
        identity = _runtime_identity(state)
        if identity is None and state_source == 'frame-aggregate':
            identity = _runtime_identity(frame)
        if identity is None:
            continue
        same_resource = _same_resource(material_input, state)
        if require_same_resource and same_resource is not True:
            continue
        texture_ok, _missing_texture_stages = _texture_stage_status(
            state, expected_external_stages
        )
        type_ok, _texture_type_reasons = _texture_stage_contract(
            state, expected_external_stages, expected_external_types
        )
        if not texture_ok or not type_ok:
            continue
        for candidate_index, candidate in enumerate(candidates):
            score, evidence = _candidate_identity_matches(candidate, identity)
            if score <= 0:
                continue
            matches.append({
                "frame": frame.get("frame"),
                "draw_index": state.get("draw_index") if state_source == "draw-snapshot" else None,
                "source": state_source,
                "candidate_index": candidate_index,
                "candidate_file": candidate.get("file"),
                "candidate_program_offset": candidate.get("program_offset"),
                "score": score,
                "evidence": evidence,
                "same_meb_resource": same_resource,
                "external_texture_stages": expected_external_stages,
                "external_texture_types": expected_external_types,
                "identity_sha256": identity.get("identity_sha256"),
                "pair_byte_sha256": identity.get("pair_byte_sha256"),
                "vertex_byte_sha256": (
                    (identity.get("payload") or {}).get("vertex", {}).get("byte_sha256")
                    if isinstance(identity.get("payload"), Mapping)
                    else None
                ),
                "pixel_byte_sha256": (
                    (identity.get("payload") or {}).get("pixel", {}).get("byte_sha256")
                    if isinstance(identity.get("payload"), Mapping)
                    else None
                ),
            })

    if not matches:
        reason = (
            "runtime:exact-shader-and-resource-instance-not-found"
            if require_same_resource
            else "runtime:exact-shader-instance-not-found"
        )
        return {
            "format": FORMAT,
            "status": "not-found",
            "ready": False,
            "blocking_reasons": [reason],
            "candidate_count": len(candidates),
            "runtime_frame_count": len(runtime_report.get("frames") or []),
            "matches": [],
        }

    best_score = max(int(row["score"]) for row in matches)
    best = [row for row in matches if int(row["score"]) == best_score]
    unique_keys = {
        (row.get("candidate_file"), row.get("candidate_program_offset"))
        for row in best
    }
    if len(unique_keys) != 1:
        return {
            "format": FORMAT,
            "status": "ambiguous",
            "ready": False,
            "blocking_reasons": ["runtime:multiple-exact-shader-candidates"],
            "candidate_count": len(candidates),
            "runtime_frame_count": len(runtime_report.get("frames") or []),
            "best_score": best_score,
            "matches": best,
        }

    selected = best[0]
    return {
        "format": FORMAT,
        "status": "match",
        "ready": True,
        "blocking_reasons": [],
        "candidate_count": len(candidates),
        "runtime_frame_count": len(runtime_report.get("frames") or []),
        "best_score": best_score,
        "selected": selected,
        "matches": best,
    }


def validate_files(
    material_input_path: str | Path,
    runtime_report_path: str | Path,
    *,
    require_same_resource: bool = True,
) -> dict[str, Any]:
    material = json.loads(Path(material_input_path).read_text(encoding="utf-8"))
    runtime = json.loads(Path(runtime_report_path).read_text(encoding="utf-8"))
    return select_runtime_shader(
        material,
        runtime,
        require_same_resource=require_same_resource,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Select an exact BMW shader permutation from runtime D3D9 identity"
    )
    parser.add_argument("material_input")
    parser.add_argument("runtime_report")
    parser.add_argument("output")
    parser.add_argument(
        "--allow-resource-mismatch",
        action="store_true",
        help="diagnostic mode; do not require the same MEB resource identity",
    )
    args = parser.parse_args()
    report = validate_files(
        args.material_input,
        args.runtime_report,
        require_same_resource=not args.allow_resource_mismatch,
    )
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "selected": report.get("selected"),
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
