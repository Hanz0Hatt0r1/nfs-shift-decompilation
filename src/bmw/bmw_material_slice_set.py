"""Compose independently validated BMW primitive slices into one draw set."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from bmw_vulkan_bundle import TARGET_MEB
from render_command import validate_render_command

FORMAT = "SHIFT.BMWMaterialSliceSet/1"
SLICE_FORMAT = "SHIFT.BMWMaterialSlice/1"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _stable_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    path = Path(value)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    payload["_source_path"] = str(path)
    payload["_source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return payload


def _resource_identity(payload: Mapping[str, Any]) -> tuple[str, str]:
    golden = payload.get("golden_identity") or {}
    packet_mesh = (payload.get("packet") or {}).get("mesh") or {}
    resolved = packet_mesh.get("resolved") or {}
    provenance = payload.get("provenance") or {}
    mesh_entry = provenance.get("mesh_entry") or {}

    resource = _norm(
        golden.get("resource")
        or resolved.get("path")
        or packet_mesh.get("ref")
    )
    digest = str(
        golden.get("resource_sha256")
        or resolved.get("resource_sha256")
        or mesh_entry.get("sha256")
        or ""
    ).lower()
    return resource, digest


def _texture_union(
    rows: Iterable[Mapping[str, Any]],
    blockers: list[str],
) -> list[dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        path = _norm(row.get("path"))
        digest = str(row.get("sha256") or "").lower()
        if not path:
            blockers.append("slice-set:texture-source-path-missing")
            continue
        previous = by_path.get(path)
        if previous is not None:
            previous_digest = str(previous.get("sha256") or "").lower()
            if digest and previous_digest and digest != previous_digest:
                blockers.append(
                    f"slice-set:texture-source-sha-conflict:{path}"
                )
            continue
        by_path[path] = row
    return [by_path[path] for path in sorted(by_path)]


def build_bmw_material_slice_set(
    material_slices: Iterable[str | Path | Mapping[str, Any]],
) -> dict[str, Any]:
    payloads = [_load(value) for value in material_slices]
    if not payloads:
        raise ValueError("BMW material slice set requires at least one slice")

    blockers: list[str] = []
    records: list[dict[str, Any]] = []
    primitive_seen: set[int] = set()

    for input_order, payload in enumerate(payloads):
        if payload.get("format") != SLICE_FORMAT:
            blockers.append(
                f"slice-set:input-{input_order}:invalid-format"
            )

        try:
            primitive_index = int(payload.get("primitive_index"))
        except (TypeError, ValueError):
            blockers.append(
                f"slice-set:input-{input_order}:primitive-index-invalid"
            )
            primitive_index = -1

        if primitive_index in primitive_seen:
            blockers.append(
                f"slice-set:duplicate-primitive-index:{primitive_index}"
            )
        primitive_seen.add(primitive_index)

        slice_reasons = [
            str(reason)
            for reason in payload.get("blocking_reasons") or []
        ]
        if payload.get("ready") is not True:
            blockers.extend(
                f"slice-set:primitive-{primitive_index}:{reason}"
                for reason in (slice_reasons or ["slice-not-ready"])
            )

        generic_gate = payload.get("generic_material_gate") or {}
        if generic_gate.get("ready") is not True:
            blockers.append(
                f"slice-set:primitive-{primitive_index}:generic-material-gate-not-ready"
            )

        golden_gate = payload.get("slice_golden_gate") or {}
        if golden_gate.get("ready") is not True:
            blockers.append(
                f"slice-set:primitive-{primitive_index}:golden-gate-not-ready"
            )

        command = payload.get("render_command") or {}
        submeshes = list(command.get("submeshes") or [])
        if command.get("format") != "SHIFT.RenderCommand/1":
            blockers.append(
                f"slice-set:primitive-{primitive_index}:render-command-invalid"
            )
        if command.get("ready") is not True:
            blockers.append(
                f"slice-set:primitive-{primitive_index}:render-command-not-ready"
            )
        if len(submeshes) != 1:
            blockers.append(
                f"slice-set:primitive-{primitive_index}:expected-one-submesh"
            )

        resource, resource_sha = _resource_identity(payload)
        if resource != _norm(TARGET_MEB):
            blockers.append(
                f"slice-set:primitive-{primitive_index}:mesh-resource-mismatch"
            )
        if len(resource_sha) != 64:
            blockers.append(
                f"slice-set:primitive-{primitive_index}:mesh-sha256-missing"
            )

        neutral_mesh = payload.get("mesh") or {}
        if not isinstance(neutral_mesh, Mapping):
            blockers.append(
                f"slice-set:primitive-{primitive_index}:neutral-mesh-missing"
            )
            neutral_mesh = {}

        records.append({
            "input_order": input_order,
            "primitive_index": primitive_index,
            "material_ref": payload.get("material_ref"),
            "material_bmt": payload.get("material_bmt"),
            "resource": resource,
            "resource_sha256": resource_sha,
            "neutral_mesh_sha256": _stable_sha256(neutral_mesh),
            "command_mesh_sha256": _stable_sha256(command.get("mesh") or {}),
            "world_matrix_sha256": _stable_sha256(command.get("world_matrix")),
            "payload": payload,
            "command": command,
            "submesh": deepcopy(submeshes[0]) if len(submeshes) == 1 else {},
        })

    records.sort(key=lambda row: (row["primitive_index"], row["input_order"]))

    first = records[0]
    for row in records[1:]:
        primitive_index = row["primitive_index"]
        if row["resource"] != first["resource"]:
            blockers.append(
                f"slice-set:primitive-{primitive_index}:mesh-resource-differs"
            )
        if row["resource_sha256"] != first["resource_sha256"]:
            blockers.append(
                f"slice-set:primitive-{primitive_index}:mesh-sha256-differs"
            )
        if row["neutral_mesh_sha256"] != first["neutral_mesh_sha256"]:
            blockers.append(
                f"slice-set:primitive-{primitive_index}:neutral-mesh-differs"
            )
        if row["command_mesh_sha256"] != first["command_mesh_sha256"]:
            blockers.append(
                f"slice-set:primitive-{primitive_index}:command-mesh-differs"
            )
        if row["world_matrix_sha256"] != first["world_matrix_sha256"]:
            blockers.append(
                f"slice-set:primitive-{primitive_index}:world-matrix-differs"
            )

    texture_rows: list[Mapping[str, Any]] = []
    for row in records:
        texture_rows.extend(row["payload"].get("texture_sources") or [])
    texture_sources = _texture_union(texture_rows, blockers)

    commands = [row["command"] for row in records]
    combined = {
        "format": "SHIFT.RenderCommand/1",
        "ready": False,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "mesh": deepcopy(first["command"].get("mesh") or {}),
        "world_matrix": deepcopy(first["command"].get("world_matrix")),
        "submeshes": [deepcopy(row["submesh"]) for row in records],
        "resource_plan": {
            "format": (first["command"].get("resource_plan") or {}).get(
                "format", "SHIFT.RenderResources/1"
            ),
            "texture_count": sum(
                int((command.get("resource_plan") or {}).get("texture_count", 0) or 0)
                for command in commands
            ),
            "sampler_count": sum(
                int((command.get("resource_plan") or {}).get("sampler_count", 0) or 0)
                for command in commands
            ),
            "external_sampler_count": sum(
                len(submesh.get("external_samplers") or [])
                for submesh in [row["submesh"] for row in records]
            ),
            "scope": "draw-local-totals",
        },
    }
    validation = validate_render_command(combined)
    combined["validation"] = validation
    blockers.extend(validation.get("blocking_reasons") or [])
    blockers = list(dict.fromkeys(blockers))
    combined["blocking_reasons"] = blockers
    combined["ready"] = not blockers and validation.get("valid") is True

    draw_rows = [{
        "draw_order": order,
        "primitive_index": row["primitive_index"],
        "material_ref": row["material_ref"],
        "material_bmt": row["material_bmt"],
        "source_path": row["payload"].get("_source_path"),
        "source_sha256": row["payload"].get("_source_sha256"),
        "shader_permutation_identity_sha256": (
            ((row["submesh"].get("shader") or {}).get("permutation_identity") or {})
            .get("identity_sha256")
        ),
    } for order, row in enumerate(records)]

    report = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if combined["ready"] else "blocked",
        "ready": combined["ready"],
        "blocking_reasons": blockers,
        "mesh_identity": {
            "resource": first["resource"],
            "resource_sha256": first["resource_sha256"],
            "neutral_mesh_sha256": first["neutral_mesh_sha256"],
            "command_mesh_sha256": first["command_mesh_sha256"],
        },
        "primitive_indices": [row["primitive_index"] for row in records],
        "draw_count": len(records),
        "draws": draw_rows,
        "render_command": combined,
        "mesh": deepcopy(first["payload"].get("mesh") or {}),
        "golden_identity": deepcopy(
            first["payload"].get("golden_identity") or {}
        ),
        "texture_sources": texture_sources,
        "source_slices": [{
            "primitive_index": row["primitive_index"],
            "material_ref": row["material_ref"],
            "material_bmt": row["material_bmt"],
            "source_path": row["payload"].get("_source_path"),
            "source_sha256": row["payload"].get("_source_sha256"),
        } for row in records],
    }
    report["identity_sha256"] = _stable_sha256({
        "mesh_identity": report["mesh_identity"],
        "draws": report["draws"],
        "texture_sources": report["texture_sources"],
    })
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compose ready BMW primitive material slices into one draw set"
    )
    parser.add_argument("slices", nargs="+")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    result = build_bmw_material_slice_set(args.slices)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
