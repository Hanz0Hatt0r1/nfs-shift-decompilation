"""Filter retail BMW FXO permutations with draw-local runtime c-register witnesses.

The filter is intentionally narrower than raw shader-byte matching. It compares
only constant names whose register locations were observed at the exact BMW draw
boundary and keeps ambiguity explicit when more than one compiled permutation
has the same witnessed register layout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from material_linker import _candidate_identity, _selection_evidence_key

FORMAT = "SHIFT.BMWRuntimeRegisterPermutationFilter/1"
BODY_FORMAT = "SHIFT.BMWBodyRuntimeRegisterPermutationFilter/1"
ADMISSION_FORMAT = "SHIFT.BMWBodyMaterialAdmission/1"
WITNESS_FORMAT = "SHIFT.BMWM3RuntimeMaterialWitness/1"


def _binding(value: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = value.get("material_binding")
    return nested if isinstance(nested, Mapping) else value


def _mesh_sha(value: Mapping[str, Any]) -> str | None:
    provenance = value.get("provenance")
    if isinstance(provenance, Mapping):
        mesh = provenance.get("mesh_entry")
        if isinstance(mesh, Mapping):
            digest = mesh.get("sha256") or mesh.get("resource_sha256")
            if digest:
                return str(digest)
    golden = value.get("golden_identity")
    if isinstance(golden, Mapping) and golden.get("resource_sha256"):
        return str(golden["resource_sha256"])
    return None


def _runtime_registers(
    witness: Mapping[str, Any],
    material_name: str,
) -> tuple[dict[str, dict[str, int]], list[str]]:
    reasons: list[str] = []
    merged = {"vertex": {}, "pixel": {}}
    rows = [
        row for row in witness.get("draws") or []
        if isinstance(row, Mapping)
        and str(row.get("material") or "") == material_name
    ]
    if not rows:
        return merged, [f"runtime-registers:material-witness-missing:{material_name}"]

    for row in rows:
        for name, raw in (row.get("witness_registers") or {}).items():
            if not isinstance(raw, Mapping):
                continue
            stage = str(raw.get("stage") or "").lower()
            if stage not in merged:
                reasons.append(
                    f"runtime-registers:unsupported-stage:{stage}:{name}"
                )
                continue
            try:
                register = int(raw.get("register"))
            except (TypeError, ValueError):
                reasons.append(
                    f"runtime-registers:invalid-register:{stage}:{name}"
                )
                continue
            previous = merged[stage].get(str(name))
            if previous is not None and previous != register:
                reasons.append(
                    f"runtime-registers:conflict:{stage}:{name}:{previous}:{register}"
                )
                continue
            merged[stage][str(name)] = register

    if not merged["vertex"] and not merged["pixel"]:
        reasons.append(
            f"runtime-registers:material-witness-empty:{material_name}"
        )
    return merged, list(dict.fromkeys(reasons))


def _top_representatives(
    binding: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    rows = [
        row for row in binding.get("fxo_candidates") or []
        if isinstance(row, Mapping)
    ]
    if not rows:
        return []
    best_key = _selection_evidence_key(dict(rows[0]))
    top = [
        row for row in rows
        if _selection_evidence_key(dict(row)) == best_key
    ]
    representatives: dict[tuple, Mapping[str, Any]] = {}
    for row in top:
        representatives.setdefault(_candidate_identity(dict(row)), row)
    return list(representatives.values())


def _candidate_matches(
    candidate: Mapping[str, Any],
    registers: Mapping[str, Mapping[str, int]],
) -> tuple[bool, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    ready = True
    for stage, field in (
        ("vertex", "vertex_constant_registers"),
        ("pixel", "pixel_constant_registers"),
    ):
        observed = candidate.get(field)
        if not isinstance(observed, Mapping):
            observed = {}
        for name, expected in (registers.get(stage) or {}).items():
            actual = observed.get(name)
            ok = actual is not None and int(actual) == int(expected)
            ready = ready and ok
            checks.append({
                "stage": stage,
                "name": name,
                "expected_register": int(expected),
                "candidate_register": (
                    int(actual) if actual is not None else None
                ),
                "match": ok,
            })
    return ready, checks


def _candidate_summary(
    candidate: Mapping[str, Any],
    *,
    checks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    permutation = candidate.get("permutation_identity")
    identity = (
        permutation.get("identity_sha256")
        if isinstance(permutation, Mapping) else None
    )
    return {
        "file": candidate.get("file"),
        "program_offset": candidate.get("program_offset"),
        "permutation_identity_sha256": identity,
        "pair_sha256": candidate.get("pair_sha256"),
        "vertex_sha256": candidate.get("vertex_sha256"),
        "pixel_sha256": candidate.get("pixel_sha256"),
        "vertex_pair_selection_status": candidate.get(
            "vertex_pair_selection_status"
        ),
        "register_checks": checks or [],
    }


def filter_runtime_register_permutations(
    material_input: Mapping[str, Any],
    runtime_witness: Mapping[str, Any],
) -> dict[str, Any]:
    binding = _binding(material_input)
    material_name = str(binding.get("material") or "")
    reasons: list[str] = []

    if not material_name:
        reasons.append("runtime-registers:material-name-missing")
    if runtime_witness.get("format") != WITNESS_FORMAT:
        reasons.append("runtime-registers:witness-format-invalid")
    validation = runtime_witness.get("validation")
    if isinstance(validation, Mapping) and validation.get("ready") is not True:
        reasons.append("runtime-registers:witness-not-ready")

    expected_mesh_sha = _mesh_sha(material_input)
    runtime_resource = runtime_witness.get("resource")
    runtime_mesh_sha = (
        str(runtime_resource.get("sha256"))
        if isinstance(runtime_resource, Mapping)
        and runtime_resource.get("sha256")
        else None
    )
    if (
        expected_mesh_sha
        and runtime_mesh_sha
        and expected_mesh_sha != runtime_mesh_sha
    ):
        reasons.append("runtime-registers:mesh-resource-sha256-mismatch")

    registers, register_reasons = _runtime_registers(
        runtime_witness, material_name
    )
    reasons.extend(register_reasons)

    top = _top_representatives(binding)
    if not top:
        reasons.append("runtime-registers:top-candidates-missing")

    matches: list[dict[str, Any]] = []
    if not reasons:
        for candidate in top:
            matched, checks = _candidate_matches(candidate, registers)
            if matched:
                matches.append(
                    _candidate_summary(candidate, checks=checks)
                )

    if not reasons:
        if not matches:
            reasons.append("runtime-registers:no-static-permutation-match")
        elif len(matches) > 1:
            reasons.append("runtime-registers:multiple-static-permutations")
        elif matches[0].get("vertex_pair_selection_status") != "unique":
            reasons.append("runtime-registers:vertex-pair-not-unique")

    ready = not reasons and len(matches) == 1
    return {
        "format": FORMAT,
        "version": 1,
        "status": (
            "match" if ready
            else "ambiguous"
            if matches and len(matches) > 1
            else "blocked"
        ),
        "ready": ready,
        "blocking_reasons": list(dict.fromkeys(reasons)),
        "material": material_name or None,
        "resource": {
            "material_mesh_sha256": expected_mesh_sha,
            "runtime_mesh_sha256": runtime_mesh_sha,
            "same_resource": (
                expected_mesh_sha == runtime_mesh_sha
                if expected_mesh_sha and runtime_mesh_sha
                else None
            ),
        },
        "runtime_registers": registers,
        "top_distinct_permutation_count": len(top),
        "register_match_count": len(matches),
        "matches": matches,
        "selected": matches[0] if ready else None,
        "boundary": {
            "draw_local_register_witness": "required",
            "raw_runtime_shader_bytes": "not-required-for-filter",
            "exact_permutation_claim": (
                "selected" if ready else "not-proven"
            ),
        },
    }





def filter_body_admission_runtime_registers(
    admission: Mapping[str, Any],
    runtime_witness: Mapping[str, Any],
) -> dict[str, Any]:
    if admission.get("format") != ADMISSION_FORMAT:
        raise ValueError(
            "input must be SHIFT.BMWBodyMaterialAdmission/1"
        )

    selected = [
        int(value)
        for value in (
            (admission.get("selection") or {}).get("primitive_indices") or []
        )
    ]
    rows = [
        row for row in admission.get("primitive_results") or []
        if isinstance(row, Mapping)
    ]
    by_index = {
        int(row.get("primitive_index")): row
        for row in rows
        if row.get("primitive_index") is not None
    }
    if not selected:
        selected = sorted(by_index)

    blockers: list[str] = []
    results: list[dict[str, Any]] = []
    unique_materials: dict[str, dict[str, Any]] = {}

    for primitive_index in selected:
        row = by_index.get(primitive_index)
        material_slice = (
            row.get("slice") if isinstance(row, Mapping) else None
        )
        if not isinstance(material_slice, Mapping):
            reason = (
                f"runtime-registers:primitive-{primitive_index}:slice-missing"
            )
            blockers.append(reason)
            results.append({
                "primitive_index": primitive_index,
                "ready": False,
                "status": "blocked",
                "blocking_reasons": [reason],
                "filter": None,
            })
            continue

        filtered = filter_runtime_register_permutations(
            material_slice, runtime_witness
        )
        prefixed = [
            f"runtime-registers:primitive-{primitive_index}:{reason}"
            for reason in filtered.get("blocking_reasons") or []
        ]
        blockers.extend(prefixed)
        result = {
            "primitive_index": primitive_index,
            "material": filtered.get("material"),
            "ready": filtered.get("ready") is True,
            "status": filtered.get("status"),
            "top_distinct_permutation_count": filtered.get(
                "top_distinct_permutation_count", 0
            ),
            "register_match_count": filtered.get(
                "register_match_count", 0
            ),
            "blocking_reasons": prefixed,
            "filter": filtered,
        }
        results.append(result)

        material_name = str(filtered.get("material") or "")
        if material_name:
            signature = {
                "runtime_registers": filtered.get("runtime_registers"),
                "matches": [
                    {
                        "permutation_identity_sha256": match.get(
                            "permutation_identity_sha256"
                        ),
                        "pair_sha256": match.get("pair_sha256"),
                    }
                    for match in filtered.get("matches") or []
                ],
            }
            existing = unique_materials.get(material_name)
            if existing is None:
                unique_materials[material_name] = {
                    "material": material_name,
                    "primitive_indices": [primitive_index],
                    "top_distinct_permutation_count": filtered.get(
                        "top_distinct_permutation_count", 0
                    ),
                    "register_match_count": filtered.get(
                        "register_match_count", 0
                    ),
                    "ready": filtered.get("ready") is True,
                    "signature": signature,
                }
            else:
                existing["primitive_indices"].append(primitive_index)
                if existing["signature"] != signature:
                    blockers.append(
                        "runtime-registers:"
                        f"material-{material_name}:primitive-result-conflict"
                    )

    for value in unique_materials.values():
        value["primitive_indices"].sort()
        value.pop("signature", None)

    ready_count = sum(result["ready"] for result in results)
    ready = (
        bool(results)
        and ready_count == len(results)
        and not blockers
    )
    any_ambiguous = any(
        result.get("status") == "ambiguous" for result in results
    )
    return {
        "format": BODY_FORMAT,
        "version": 1,
        "status": (
            "match" if ready
            else "ambiguous" if any_ambiguous
            else "blocked"
        ),
        "ready": ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "selected_primitive_indices": selected,
        "primitive_count": len(results),
        "ready_primitive_count": ready_count,
        "blocked_primitive_count": len(results) - ready_count,
        "unique_material_count": len(unique_materials),
        "primitive_results": results,
        "materials": sorted(
            unique_materials.values(),
            key=lambda row: str(row["material"]),
        ),
        "boundary": {
            "uses_phase538_top_rank_candidates": True,
            "selects_only_on_draw_local_register_evidence": True,
            "render_admission": False,
            "raw_runtime_shader_byte_identity": "not-proven",
        },
    }


def validate_files(
    material_input_path: str | Path,
    runtime_witness_path: str | Path,
) -> dict[str, Any]:
    material = json.loads(
        Path(material_input_path).read_text(encoding="utf-8")
    )
    witness = json.loads(
        Path(runtime_witness_path).read_text(encoding="utf-8")
    )
    if not isinstance(material, dict) or not isinstance(witness, dict):
        raise ValueError("inputs must be JSON objects")
    if material.get("format") == ADMISSION_FORMAT:
        return filter_body_admission_runtime_registers(material, witness)
    return filter_runtime_register_permutations(material, witness)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Filter retail BMW FXO candidates with draw-local runtime "
            "constant-register witnesses"
        )
    )
    parser.add_argument("material_input")
    parser.add_argument("runtime_witness")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    result = validate_files(args.material_input, args.runtime_witness)
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    summary = {
        "format": result["format"],
        "status": result["status"],
        "ready": result["ready"],
        "blocking_reasons": result["blocking_reasons"],
    }
    if result["format"] == BODY_FORMAT:
        summary.update({
            "primitive_count": result["primitive_count"],
            "ready_primitive_count": result["ready_primitive_count"],
            "blocked_primitive_count": result["blocked_primitive_count"],
            "unique_material_count": result["unique_material_count"],
        })
    else:
        summary.update({
            "material": result["material"],
            "top_distinct_permutation_count": result[
                "top_distinct_permutation_count"
            ],
            "register_match_count": result["register_match_count"],
        })
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
