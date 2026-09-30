"""Build D3D9 runtime-resource inputs from IMB shader target evidence.

The handoff groups primitive bindings by exact IMB resource identity and carries
source-backed declaration descriptors plus primitive draw ranges. It reuses the
generic resource fields consumed by the existing D3D9 runtime evidence builder
without asserting serialized IMB/MEB equivalence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.IMBRuntimeResourceEvidenceSet/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"


def _valid_sha(value: Any) -> str | None:
    text = str(value or "").lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _descriptors(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, list) or not value:
        return None
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping):
            return None
        prop = str(item.get("id") or "")
        words = item.get("words")
        if not prop or prop in seen:
            return None
        if not isinstance(words, list) or len(words) < 3:
            return None
        try:
            triple = [int(words[0]), int(words[1]), int(words[2])]
        except (TypeError, ValueError):
            return None
        rows.append({"id": prop, "words": triple})
        seen.add(prop)
    return rows


def build_imb_runtime_resource_evidence_set(
    target_set: Mapping[str, Any],
) -> dict[str, Any]:
    if target_set.get("format") != TARGET_FORMAT:
        raise ValueError(
            "input must be SHIFT.IMBRuntimeShaderTargetSet/1"
        )

    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    blockers: list[str] = []
    bindings = [
        row
        for row in (target_set.get("binding_targets") or [])
        if isinstance(row, Mapping)
    ]

    for ordinal, row in enumerate(bindings):
        binding_index = int(row.get("binding_index", ordinal))
        archive = str(row.get("archive") or "")
        path = str(row.get("imb_path") or "").replace("\\", "/")
        sha = _valid_sha(row.get("imb_sha256"))
        descriptors = _descriptors(row.get("property_descriptors"))
        draw_range = row.get("draw_range")

        reasons: list[str] = []
        if row.get("resource_identity_ready") is not True:
            reasons.append("resource-identity-not-ready")
        if row.get("draw_range_ready") is not True:
            reasons.append("draw-range-not-ready")
        if sha is None:
            reasons.append("imb-sha256-invalid")
        if descriptors is None:
            reasons.append("property-descriptors-missing-or-invalid")
        if not isinstance(draw_range, Mapping):
            reasons.append("draw-range-missing")
        if row.get("capture_ready") is not True:
            reasons.append("shader-target-not-capture-ready")

        if reasons:
            blockers.extend(
                f"binding-{binding_index}:{reason}"
                for reason in reasons
            )
            continue

        key = (archive, path.lower(), sha)
        group = groups.setdefault(key, {
            "archive": archive,
            "resource_path": path,
            "resource_sha256": sha,
            "imb_entry_index": row.get("imb_entry_index"),
            "property_descriptors": descriptors,
            "binding_indices": [],
            "primitive_bindings": [],
        })
        if group["property_descriptors"] != descriptors:
            blockers.append(
                f"binding-{binding_index}:resource-descriptor-mismatch"
            )
            continue

        group["binding_indices"].append(binding_index)
        group["primitive_bindings"].append({
            "binding_index": binding_index,
            "primitive_index": row.get("primitive_index"),
            "draw_range": dict(draw_range),
            "material_reference": row.get("material_reference"),
            "shader": row.get("shader"),
            "shader_family": row.get("shader_family"),
            "hash_target_count": int(row.get("hash_target_count") or 0),
        })

    resources = sorted(
        groups.values(),
        key=lambda row: (
            str(row["archive"]).lower(),
            str(row["resource_path"]).lower(),
        ),
    )
    for resource_index, row in enumerate(resources):
        row["resource_index"] = resource_index
        row["binding_indices"] = sorted(set(row["binding_indices"]))
        row["primitive_bindings"] = sorted(
            row["primitive_bindings"],
            key=lambda item: int(item["binding_index"]),
        )
        row["runtime_binding_input"] = {
            "format": "SHIFT.IMBRuntimeResourceEvidence/1",
            "resource": row["resource_path"],
            "resource_sha256": row["resource_sha256"],
            "property_descriptors": [
                dict(item) for item in row["property_descriptors"]
            ],
            "source": {
                "archive": row["archive"],
                "entry_index": row.get("imb_entry_index"),
                "resource_sha256": row["resource_sha256"],
                "root_relative_path": row["resource_path"],
                "source_kind": "IMB",
            },
            "boundary": {
                "serialized_container": "IMB",
                "meb_equivalence": False,
                "purpose": (
                    "resource/declaration identity input for "
                    "D3D9RuntimeBindingEvidence/1"
                ),
            },
        }

    covered_bindings = sum(
        len(row["binding_indices"]) for row in resources
    )
    ready = (
        target_set.get("same_instance_match_ready") is True
        and bool(resources)
        and not blockers
        and covered_bindings == len(bindings)
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "binding_target_count": len(bindings),
        "covered_binding_count": covered_bindings,
        "resource_count": len(resources),
        "multi_primitive_resource_count": sum(
            len(row["primitive_bindings"]) > 1
            for row in resources
        ),
        "resources": resources,
        "boundary": {
            "groups_by": ["archive", "imb_path", "imb_sha256"],
            "requires_property_descriptors": True,
            "reuses_d3d9_runtime_resource_fields": True,
            "meb_equivalence": False,
            "selects_shader_permutation": False,
            "next_stage": (
                "D3D9RuntimeBindingEvidence/1 per candidate IMB resource, "
                "then same-instance shader-variant attribution"
            ),
        },
    }


def validate_file(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("target input must be a JSON object")
    return build_imb_runtime_resource_evidence_set(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target_set")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_file(args.target_set)
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "binding_target_count": report["binding_target_count"],
        "resource_count": report["resource_count"],
        "multi_primitive_resource_count": report[
            "multi_primitive_resource_count"
        ],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
