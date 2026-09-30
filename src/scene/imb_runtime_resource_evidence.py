"""Build runtime resource-identity envelopes from IMB shader targets.

The output groups primitive bindings by exact IMB resource identity and carries
the declaration descriptors and draw ranges required by the existing D3D9
runtime evidence path. It does not relabel IMB as MEB.
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


def _valid_draw_range(value: Any) -> dict[str, int] | None:
    if not isinstance(value, Mapping):
        return None
    try:
        first_index = int(value.get("first_index"))
        index_count = int(value.get("index_count"))
        primitive_count = int(value.get("primitive_count"))
        primitive_type = int(value.get("primitive_type"))
    except (TypeError, ValueError):
        return None
    if first_index < 0 or index_count <= 0 or primitive_count <= 0:
        return None
    if primitive_count * 3 != index_count:
        return None
    return {
        "first_index": first_index,
        "index_count": index_count,
        "primitive_count": primitive_count,
        "primitive_type": primitive_type,
    }


def _valid_descriptors(value: Any) -> list[dict[str, Any]] | None:
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
        draw_range = _valid_draw_range(row.get("draw_range"))
        descriptors = _valid_descriptors(row.get("property_descriptors"))

        reasons: list[str] = []
        if not archive:
            reasons.append("archive-missing")
        if not path:
            reasons.append("imb-path-missing")
        if sha is None:
            reasons.append("imb-sha256-missing-or-invalid")
        if draw_range is None:
            reasons.append("draw-range-missing-or-invalid")
        if descriptors is None:
            reasons.append("property-descriptors-missing-or-invalid")
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
            "draw_range": draw_range,
            "material_reference": row.get("material_reference"),
            "shader": row.get("shader"),
            "shader_family": row.get("shader_family"),
            "hash_target_count": int(
                row.get("hash_target_count") or 0
            ),
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
                    "resource/declaration identity input for the existing "
                    "D3D9 runtime evidence builder"
                ),
            },
        }

    ready = (
        target_set.get("capture_ready") is True
        and bool(resources)
        and not blockers
        and sum(len(row["binding_indices"]) for row in resources)
        == len(bindings)
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "binding_target_count": len(bindings),
        "resource_count": len(resources),
        "multi_primitive_resource_count": sum(
            len(row["primitive_bindings"]) > 1 for row in resources
        ),
        "resources": resources,
        "boundary": {
            "groups_by": [
                "archive", "imb_path", "imb_sha256"
            ],
            "requires_exact_resource_sha256": True,
            "requires_exact_draw_range": True,
            "requires_property_descriptors": True,
            "meb_equivalence": False,
            "selects_shader_permutation": False,
            "next_stage": (
                "D3D9RuntimeBindingEvidence/1 per candidate resource, "
                "then same-instance primitive shader attribution"
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
