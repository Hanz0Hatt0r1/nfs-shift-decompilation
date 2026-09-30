"""Adapt one IMB runtime target binding into D3D9 resource-probe evidence.

The output intentionally matches the resource fields already consumed by
build_runtime_binding_evidence(..., meb_resource=...).  The legacy parameter
name is MEB-specific, but the underlying contract is resource path/hash plus
Type/Usage/Channel property descriptors and is equally applicable to IMB.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.IMBRuntimeResourceProbe/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"


def _descriptor_from_property(value: Any) -> dict[str, Any] | None:
    text = str(value or "")
    if len(text) != 3 or not text.isdigit():
        return None
    return {
        "id": text,
        "words": [
            int(text[0]),
            int(text[1]),
            int(text[2]),
        ],
    }


def _binding_rows(
    target_set: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    return [
        row
        for row in (target_set.get("binding_targets") or [])
        if isinstance(row, Mapping)
    ]


def build_imb_runtime_resource_probe(
    target_set: Mapping[str, Any],
    binding_index: int,
) -> dict[str, Any]:
    if target_set.get("format") != TARGET_FORMAT:
        raise ValueError(
            "input must be SHIFT.IMBRuntimeShaderTargetSet/1"
        )

    try:
        binding_index = int(binding_index)
    except (TypeError, ValueError) as exc:
        raise ValueError("binding_index must be an integer") from exc
    if binding_index < 0:
        raise ValueError("binding_index must be non-negative")

    matches = [
        row
        for row in _binding_rows(target_set)
        if row.get("binding_index") is not None
        and int(row.get("binding_index")) == binding_index
    ]
    if len(matches) != 1:
        raise ValueError(
            f"binding_index {binding_index} resolves to "
            f"{len(matches)} rows"
        )
    binding = matches[0]

    blockers: list[str] = []
    if binding.get("capture_ready") is not True:
        blockers.append("shader-targets:not-capture-ready")
    if binding.get("resource_identity_ready") is not True:
        blockers.append("resource-identity:not-ready")
    if binding.get("draw_range_ready") is not True:
        blockers.append("draw-range:not-ready")
    if binding.get("same_instance_match_ready") is not True:
        blockers.append("same-instance-target:not-ready")

    resource = str(binding.get("imb_path") or "").replace("\\", "/")
    resource_sha256 = str(binding.get("imb_sha256") or "").lower()
    if not resource.lower().endswith(".imb"):
        blockers.append("resource-path:not-imb")
    if len(resource_sha256) != 64:
        blockers.append("resource-sha256:invalid")
    else:
        try:
            int(resource_sha256, 16)
        except ValueError:
            blockers.append("resource-sha256:invalid")

    properties = list(binding.get("vertex_properties") or [])
    descriptors: list[dict[str, Any]] = []
    invalid_properties: list[str] = []
    for value in properties:
        descriptor = _descriptor_from_property(value)
        if descriptor is None:
            invalid_properties.append(str(value))
        else:
            descriptors.append(descriptor)

    if not descriptors:
        blockers.append("property-descriptors:empty")
    if invalid_properties:
        blockers.append(
            "property-descriptors:invalid:"
            + ",".join(invalid_properties)
        )

    draw_range = binding.get("draw_range")
    if not isinstance(draw_range, Mapping):
        blockers.append("draw-range:missing")

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "binding_index": binding_index,
        "archive": binding.get("archive"),
        "resource": resource or None,
        "resource_sha256": resource_sha256 or None,
        "imb_entry_index": binding.get("imb_entry_index"),
        "primitive_index": binding.get("primitive_index"),
        "draw_range": dict(draw_range) if isinstance(
            draw_range, Mapping
        ) else None,
        "property_descriptors": descriptors,
        "shader_family": binding.get("shader_family"),
        "hash_target_count": binding.get("hash_target_count"),
        "boundary": {
            "resource_identity": (
                "archive-local IMB path + decoded payload SHA-256"
            ),
            "property_descriptor_source": (
                "source-backed IMB Type/Usage/Channel property ids"
            ),
            "runtime_trace_adapter": (
                "compatible with the existing legacy "
                "build_runtime_binding_evidence meb_resource input"
            ),
            "usage_ordinal_map_still_required": True,
            "draw_range_used_by_runtime_trace_gate": False,
            "draw_range_reserved_for_target_match": True,
            "selects_permutation": False,
        },
    }


def validate_file(
    target_set_path: str | Path,
    binding_index: int,
) -> dict[str, Any]:
    value = json.loads(
        Path(target_set_path).read_text(encoding="utf-8")
    )
    if not isinstance(value, Mapping):
        raise ValueError("target input must be a JSON object")
    return build_imb_runtime_resource_probe(value, binding_index)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build D3D9 runtime resource-probe evidence for one "
            "IMB target binding"
        )
    )
    parser.add_argument("target_set")
    parser.add_argument("binding_index", type=int)
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_file(
        args.target_set,
        args.binding_index,
    )
    Path(args.output).write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "binding_index": report["binding_index"],
        "resource": report["resource"],
        "property_descriptor_count": len(
            report["property_descriptors"]
        ),
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
