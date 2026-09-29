"""Build a compact runtime shader target set from BMW body admission evidence.

The target set is capture-oriented, not render admission.  It preserves every
statically tied top-rank candidate identity instead of selecting one.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from material_linker import _selection_evidence_key

FORMAT = "SHIFT.BMWRuntimeShaderTargetSet/1"
ADMISSION_FORMAT = "SHIFT.BMWBodyMaterialAdmission/1"


def _valid_sha(value: Any) -> str | None:
    text = str(value or "").lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _candidate_target(candidate: Mapping[str, Any]) -> dict[str, Any] | None:
    permutation = candidate.get("permutation_identity") or {}
    permutation_sha = (
        _valid_sha(permutation.get("identity_sha256"))
        if isinstance(permutation, Mapping)
        else None
    )
    pair_sha = _valid_sha(candidate.get("pair_sha256"))
    vertex_sha = _valid_sha(candidate.get("vertex_sha256"))
    pixel_sha = _valid_sha(candidate.get("pixel_sha256"))
    pair_unique = candidate.get("vertex_pair_selection_status") == "unique"

    if pair_unique and permutation_sha:
        identity_kind = "permutation"
        identity_value = permutation_sha
        strength = "exact-pair"
    elif pair_unique and pair_sha:
        identity_kind = "pair"
        identity_value = pair_sha
        strength = "exact-pair"
    elif pixel_sha:
        identity_kind = "pixel"
        identity_value = pixel_sha
        strength = "prefilter-only"
    elif vertex_sha:
        identity_kind = "vertex"
        identity_value = vertex_sha
        strength = "prefilter-only"
    else:
        return None

    return {
        "identity_kind": identity_kind,
        "identity_value": identity_value,
        "strength": strength,
        "permutation_identity_sha256": permutation_sha,
        "pair_byte_sha256": pair_sha,
        "vertex_byte_sha256": vertex_sha,
        "pixel_byte_sha256": pixel_sha,
        "candidate_file": candidate.get("file"),
        "candidate_program_offset": candidate.get("program_offset"),
        "vertex_pair_selection_status": candidate.get(
            "vertex_pair_selection_status"
        ),
        "exact": candidate.get("exact") is True,
        "static_rank": list(_selection_evidence_key(dict(candidate))),
    }


def _top_candidates(binding: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = [
        row
        for row in (binding.get("fxo_candidates") or [])
        if isinstance(row, Mapping)
    ]
    if not rows:
        return []
    best_rank = _selection_evidence_key(dict(rows[0]))
    return [
        row
        for row in rows
        if _selection_evidence_key(dict(row)) == best_rank
    ]


def _mesh_identity(material_slice: Mapping[str, Any]) -> dict[str, Any]:
    provenance = material_slice.get("provenance") or {}
    mesh = (
        provenance.get("mesh_entry")
        if isinstance(provenance, Mapping)
        else {}
    ) or {}
    golden = material_slice.get("golden_identity") or {}
    return {
        "path": (
            mesh.get("path")
            or golden.get("resource")
            or "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
        ),
        "sha256": (
            mesh.get("sha256")
            or mesh.get("resource_sha256")
            or golden.get("resource_sha256")
        ),
    }


def build_bmw_runtime_shader_target_set(
    admission: Mapping[str, Any],
) -> dict[str, Any]:
    if admission.get("format") != ADMISSION_FORMAT:
        raise ValueError(
            "input must be SHIFT.BMWBodyMaterialAdmission/1"
        )

    primitive_rows = [
        row
        for row in (admission.get("primitive_results") or [])
        if isinstance(row, Mapping)
    ]
    selected = [
        int(value)
        for value in (
            (admission.get("selection") or {}).get("primitive_indices") or []
        )
    ]
    if not selected:
        selected = sorted(
            int(row.get("primitive_index"))
            for row in primitive_rows
            if row.get("primitive_index") is not None
        )

    blockers: list[str] = []
    primitive_targets: list[dict[str, Any]] = []
    global_targets: dict[tuple[str, str], dict[str, Any]] = {}
    mesh_identity: dict[str, Any] | None = None

    by_index = {
        int(row.get("primitive_index")): row
        for row in primitive_rows
        if row.get("primitive_index") is not None
    }

    for primitive_index in selected:
        row = by_index.get(primitive_index)
        material_slice = row.get("slice") if isinstance(row, Mapping) else None
        if not isinstance(material_slice, Mapping):
            blockers.append(
                f"shader-target:primitive-{primitive_index}:slice-missing"
            )
            primitive_targets.append({
                "primitive_index": primitive_index,
                "capture_ready": False,
                "attribution_ready": False,
                "targets": [],
            })
            continue

        current_mesh = _mesh_identity(material_slice)
        if mesh_identity is None:
            mesh_identity = current_mesh
        elif current_mesh != mesh_identity:
            blockers.append(
                f"shader-target:primitive-{primitive_index}:mesh-identity-mismatch"
            )

        binding = material_slice.get("material_binding") or {}
        top = _top_candidates(binding) if isinstance(binding, Mapping) else []
        targets: list[dict[str, Any]] = []
        dropped = 0
        for candidate in top:
            target = _candidate_target(candidate)
            if target is None:
                dropped += 1
                continue
            targets.append(target)

        # Deduplicate byte-identical target identities but retain every static
        # source location as provenance.
        dedup: dict[tuple[str, str], dict[str, Any]] = {}
        for target in targets:
            key = (target["identity_kind"], target["identity_value"])
            if key not in dedup:
                dedup[key] = {
                    **target,
                    "candidate_locations": [],
                }
            dedup[key]["candidate_locations"].append({
                "file": target.get("candidate_file"),
                "program_offset": target.get("candidate_program_offset"),
            })
        targets = list(dedup.values())

        capture_ready = bool(targets)
        attribution_ready = (
            bool(targets)
            and dropped == 0
            and all(
                target.get("strength") == "exact-pair"
                and target.get("exact") is True
                for target in targets
            )
        )
        if not capture_ready:
            blockers.append(
                f"shader-target:primitive-{primitive_index}:no-hash-targets"
            )

        material_ref = material_slice.get("material_ref")
        material_bmt = material_slice.get("material_bmt")
        primitive_targets.append({
            "primitive_index": primitive_index,
            "material_ref": material_ref,
            "material_bmt": material_bmt,
            "material_status": material_slice.get("status"),
            "material_ready": material_slice.get("ready") is True,
            "material_blocking_reasons": list(
                material_slice.get("blocking_reasons") or []
            ),
            "top_rank_candidate_count": len(top),
            "hash_target_count": len(targets),
            "dropped_unhashed_top_candidates": dropped,
            "capture_ready": capture_ready,
            "attribution_ready": attribution_ready,
            "targets": targets,
        })

        for target in targets:
            key = (target["identity_kind"], target["identity_value"])
            aggregate = global_targets.setdefault(key, {
                "identity_kind": target["identity_kind"],
                "identity_value": target["identity_value"],
                "strength": target["strength"],
                "permutation_identity_sha256": target.get(
                    "permutation_identity_sha256"
                ),
                "pair_byte_sha256": target.get("pair_byte_sha256"),
                "vertex_byte_sha256": target.get("vertex_byte_sha256"),
                "pixel_byte_sha256": target.get("pixel_byte_sha256"),
                "primitive_indices": [],
                "material_refs": [],
            })
            if primitive_index not in aggregate["primitive_indices"]:
                aggregate["primitive_indices"].append(primitive_index)
            if material_ref and material_ref not in aggregate["material_refs"]:
                aggregate["material_refs"].append(material_ref)

    capture_ready = (
        bool(primitive_targets)
        and all(row.get("capture_ready") for row in primitive_targets)
        and not any(
            reason.endswith(":slice-missing")
            or reason.endswith(":mesh-identity-mismatch")
            for reason in blockers
        )
    )
    attribution_ready = (
        capture_ready
        and all(row.get("attribution_ready") for row in primitive_targets)
    )

    unique_targets = sorted(
        global_targets.values(),
        key=lambda row: (
            str(row["identity_kind"]),
            str(row["identity_value"]),
        ),
    )
    for row in unique_targets:
        row["primitive_indices"].sort()
        row["material_refs"].sort()

    return {
        "format": FORMAT,
        "version": 1,
        "status": "capture-ready" if capture_ready else "blocked",
        "capture_ready": capture_ready,
        "attribution_ready": attribution_ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "target_resource": mesh_identity,
        "selected_primitive_indices": selected,
        "primitive_target_count": len(primitive_targets),
        "unique_hash_target_count": len(unique_targets),
        "strong_hash_target_count": sum(
            row["strength"] == "exact-pair"
            for row in unique_targets
        ),
        "prefilter_only_target_count": sum(
            row["strength"] == "prefilter-only"
            for row in unique_targets
        ),
        "primitive_targets": primitive_targets,
        "unique_targets": unique_targets,
        "boundary": {
            "render_admission": False,
            "selects_permutation": False,
            "purpose": (
                "prefilter runtime shader objects and constrain exact "
                "same-instance attribution"
            ),
        },
    }


def validate_files(
    admission_path: str | Path,
) -> dict[str, Any]:
    admission = json.loads(
        Path(admission_path).read_text(encoding="utf-8")
    )
    if not isinstance(admission, Mapping):
        raise ValueError("BMW admission input must be a JSON object")
    return build_bmw_runtime_shader_target_set(admission)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build capture-oriented BMW shader hash targets from "
            "body-material admission"
        )
    )
    parser.add_argument("admission")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_files(args.admission)
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "capture_ready": report["capture_ready"],
        "attribution_ready": report["attribution_ready"],
        "unique_hash_target_count": report["unique_hash_target_count"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["capture_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
