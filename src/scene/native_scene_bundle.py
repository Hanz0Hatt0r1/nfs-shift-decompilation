"""Build a compact native-scene manifest from runtime-proven SGB draws.

The bundle contains only RenderCommand submeshes carrying a validated
SHIFT.RuntimeProvenDraw/1 contract. It does not build backend/Vulkan artifacts;
that remains a separate downstream gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from render_command import validate_render_command

FORMAT = "SHIFT.NativeSceneBundle/1"
BRIDGE_FORMAT = "SHIFT.SGBRenderBindingBridge/1"
PROVENANCE_FORMAT = "SHIFT.RuntimeProvenDraw/1"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha_json(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _world_matrix(value: Any) -> list[float] | None:
    rows: list[Any]
    if isinstance(value, list) and len(value) == 16:
        rows = value
    elif (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(row, list) and len(row) == 4 for row in value)
    ):
        rows = [item for row in value for item in row]
    else:
        return None
    out: list[float] = []
    for item in rows:
        if not isinstance(item, (int, float)):
            return None
        out.append(float(item))
    return out


def _draw_range(value: Any) -> dict[str, int] | None:
    if not isinstance(value, Mapping):
        return None
    try:
        first_index = int(value.get("first_index"))
        index_count = int(value.get("index_count"))
        primitive_count = int(value.get("primitive_count"))
    except (TypeError, ValueError):
        return None
    if first_index < 0 or index_count <= 0 or index_count % 3:
        return None
    if primitive_count != index_count // 3:
        return None
    return {
        "first_index": first_index,
        "index_count": index_count,
        "primitive_count": primitive_count,
    }


def _shader_identity(
    submesh: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    shader = submesh.get("shader") or {}
    if not isinstance(shader, Mapping):
        return None, ["shader-identity:missing"]

    reasons: list[str] = []
    fields: dict[str, str] = {}
    for field in (
        "source_payload_sha256",
        "pair_sha256",
        "vertex_sha256",
        "pixel_sha256",
    ):
        digest = _sha256(shader.get(field))
        if digest is None:
            reasons.append(f"shader-identity:{field}:missing-or-invalid")
        else:
            fields[field] = digest

    permutation = shader.get("permutation_identity") or {}
    permutation_sha = (
        _sha256(permutation.get("identity_sha256"))
        if isinstance(permutation, Mapping)
        else None
    )
    if (
        not isinstance(permutation, Mapping)
        or permutation.get("format") != "SHIFT.ShaderPermutationIdentity/1"
        or permutation_sha is None
    ):
        reasons.append("shader-identity:permutation:missing-or-invalid")

    if reasons:
        return None, reasons

    return {
        **fields,
        "permutation_identity_sha256": permutation_sha,
    }, []


def _validate_runtime_provenance(
    submesh: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    provenance = submesh.get("runtime_provenance")
    if not isinstance(provenance, Mapping):
        return None, ["runtime-provenance:missing"]
    reasons: list[str] = []

    if provenance.get("format") != PROVENANCE_FORMAT:
        reasons.append("runtime-provenance:invalid-format")
    if provenance.get("status") != "proven":
        reasons.append("runtime-provenance:not-proven")

    try:
        binding_index = int(provenance.get("binding_index"))
    except (TypeError, ValueError):
        binding_index = -1
        reasons.append("runtime-provenance:binding-index-invalid")
    if binding_index < 0 and "runtime-provenance:binding-index-invalid" not in reasons:
        reasons.append("runtime-provenance:binding-index-invalid")

    try:
        primitive_index = int(provenance.get("primitive_index"))
    except (TypeError, ValueError):
        primitive_index = -1
        reasons.append("runtime-provenance:primitive-index-invalid")
    if primitive_index < 0 and "runtime-provenance:primitive-index-invalid" not in reasons:
        reasons.append("runtime-provenance:primitive-index-invalid")

    resource = provenance.get("resource") or {}
    resource_sha = (
        _sha256(resource.get("sha256"))
        if isinstance(resource, Mapping)
        else None
    )
    if not isinstance(resource, Mapping) or resource.get("source_kind") != "IMB":
        reasons.append("runtime-provenance:resource-kind-invalid")
    if not isinstance(resource, Mapping) or not resource.get("path"):
        reasons.append("runtime-provenance:resource-path-missing")
    if resource_sha is None:
        reasons.append("runtime-provenance:resource-sha256-invalid")

    provenance_range = _draw_range(provenance.get("draw_range"))
    command_range = _draw_range({
        "first_index": submesh.get("first_index"),
        "index_count": submesh.get("index_count"),
        "primitive_count": (
            int(submesh.get("index_count")) // 3
            if isinstance(submesh.get("index_count"), int)
            and int(submesh.get("index_count")) % 3 == 0
            else None
        ),
    })
    if provenance_range is None:
        reasons.append("runtime-provenance:draw-range-invalid")
    elif command_range is None or provenance_range != command_range:
        reasons.append("runtime-provenance:draw-range-mismatch")

    selection = provenance.get("shader_selection") or {}
    if not isinstance(selection, Mapping):
        reasons.append("runtime-provenance:selection-missing")
    else:
        if selection.get("selection_status") != "unique":
            reasons.append("runtime-provenance:selection-not-unique")
        if selection.get("selection_source") != "runtime-admission":
            reasons.append("runtime-provenance:selection-source-invalid")
        if selection.get("runtime_selection_ready") is not True:
            reasons.append("runtime-provenance:runtime-selection-not-ready")

    if reasons:
        return None, list(dict.fromkeys(reasons))

    normalized = json.loads(json.dumps(provenance))
    normalized["binding_index"] = binding_index
    normalized["primitive_index"] = primitive_index
    normalized["resource"]["sha256"] = resource_sha
    normalized["draw_range"] = provenance_range
    return normalized, []


def build_native_scene_bundle(
    bridge: Mapping[str, Any],
) -> dict[str, Any]:
    if bridge.get("format") != BRIDGE_FORMAT:
        raise ValueError("input must be SHIFT.SGBRenderBindingBridge/1")

    blockers: list[str] = []
    if bridge.get("ready") is not True:
        blockers.append("scene-bridge:not-ready")

    render_binding = bridge.get("render_binding")
    if not isinstance(render_binding, Mapping):
        render_binding = {}
        blockers.append("render-binding:missing")
    elif render_binding.get("format") != "SHIFT.RenderBinding/1":
        blockers.append("render-binding:invalid-format")

    runtime_join = bridge.get("runtime_shader_join")
    if not isinstance(runtime_join, Mapping):
        runtime_join = render_binding.get("runtime_shader_join") or {}
    if not isinstance(runtime_join, Mapping):
        runtime_join = {}
    if runtime_join.get("format") != "SHIFT.IMBRuntimeRenderBindingJoin/1":
        blockers.append("runtime-shader-join:invalid-format")
    elif runtime_join.get("ready") is not True:
        blockers.append("runtime-shader-join:not-ready")

    commands = [
        row
        for row in (render_binding.get("render_commands") or [])
        if isinstance(row, Mapping)
    ]
    packets = [
        row
        for row in (render_binding.get("packets") or [])
        if isinstance(row, Mapping)
    ]
    if len(commands) != len(packets):
        blockers.append("scene-command-packet-count-mismatch")

    draws: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    total_submeshes = 0
    proven_submeshes = 0
    ready_proven_submeshes = 0

    for command_index, command in enumerate(commands):
        command_validation = validate_render_command(dict(command))
        command_ready = (
            command.get("format") == "SHIFT.RenderCommand/1"
            and command.get("ready") is True
            and command_validation.get("valid") is True
        )
        command_hash = _sha_json(command)
        packet = packets[command_index] if command_index < len(packets) else {}
        world = _world_matrix(command.get("world_matrix"))

        for submesh_index, submesh in enumerate(command.get("submeshes") or []):
            if not isinstance(submesh, Mapping):
                continue
            total_submeshes += 1

            provenance, provenance_reasons = _validate_runtime_provenance(
                submesh
            )
            if provenance is None:
                exclusions.append({
                    "command_index": command_index,
                    "submesh_index": submesh_index,
                    "reason": (
                        "not-runtime-proven"
                        if provenance_reasons == ["runtime-provenance:missing"]
                        else "runtime-provenance-invalid"
                    ),
                    "blocking_reasons": provenance_reasons,
                })
                continue
            proven_submeshes += 1

            reasons: list[str] = []
            if not command_ready:
                reasons.append("render-command:not-ready")
                reasons.extend(
                    str(reason)
                    for reason in (command.get("blocking_reasons") or [])
                )
                reasons.extend(
                    str(reason)
                    for reason in (
                        command_validation.get("blocking_reasons") or []
                    )
                )
            if world is None:
                reasons.append("world-matrix:missing-or-invalid")

            shader_identity, shader_reasons = _shader_identity(submesh)
            reasons.extend(shader_reasons)

            if reasons:
                exclusions.append({
                    "command_index": command_index,
                    "submesh_index": submesh_index,
                    "binding_index": provenance.get("binding_index"),
                    "reason": "runtime-proven-draw-not-native-packable",
                    "blocking_reasons": list(dict.fromkeys(reasons)),
                })
                continue

            ready_proven_submeshes += 1
            draw_order = len(draws)
            submesh_hash = _sha_json(submesh)
            provenance_hash = _sha_json(provenance)
            world_hash = _sha_json(world)
            scene_binding = (
                packet.get("scene_binding")
                if isinstance(packet.get("scene_binding"), Mapping)
                else {}
            )
            draw_identity = {
                "resource": provenance["resource"],
                "primitive_index": provenance["primitive_index"],
                "draw_range": provenance["draw_range"],
                "shader_identity": shader_identity,
                "world_matrix": world,
            }
            draws.append({
                "draw_order": draw_order,
                "command_index": command_index,
                "submesh_index": submesh_index,
                "binding_index": provenance["binding_index"],
                "primitive_index": provenance["primitive_index"],
                "scene": {
                    "archive": scene_binding.get("archive"),
                    "path": scene_binding.get("scene"),
                    "node": scene_binding.get("node"),
                    "node_type": scene_binding.get("node_type"),
                    "scene_binding_index": scene_binding.get("binding_index"),
                },
                "resource": dict(provenance["resource"]),
                "draw_range": dict(provenance["draw_range"]),
                "world_matrix": world,
                "shader_identity": shader_identity,
                "runtime_provenance": provenance,
                "hashes": {
                    "render_command_sha256": command_hash,
                    "submesh_sha256": submesh_hash,
                    "runtime_provenance_sha256": provenance_hash,
                    "world_matrix_sha256": world_hash,
                    "draw_identity_sha256": _sha_json(draw_identity),
                },
            })

    blockers = list(dict.fromkeys(blockers))
    ready = bool(draws) and not blockers
    coverage_complete = (
        ready
        and total_submeshes > 0
        and ready_proven_submeshes == total_submeshes
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "draw_count": len(draws),
        "draws": draws,
        "coverage": {
            "total_render_submeshes": total_submeshes,
            "runtime_proven_submeshes": proven_submeshes,
            "native_packable_proven_submeshes": ready_proven_submeshes,
            "excluded_submeshes": len(exclusions),
            "complete_scene_coverage": coverage_complete,
        },
        "excluded_draws": exclusions,
        "source": {
            "scene_bridge_format": bridge.get("format"),
            "scene_bridge_ready": bridge.get("ready") is True,
            "render_binding_format": render_binding.get("format"),
            "runtime_shader_join_format": runtime_join.get("format"),
            "runtime_shader_join_ready": runtime_join.get("ready") is True,
        },
        "boundary": {
            "requires_runtime_proven_draw": True,
            "requires_ready_render_command": True,
            "requires_exact_world_matrix": True,
            "requires_complete_shader_identity": True,
            "unproven_draws_promoted": False,
            "partial_scene_coverage_allowed": True,
            "builds_backend_artifacts": False,
            "next_stage": (
                "map each manifest draw to one canonical child Vulkan bundle "
                "and index the ordered set for native_runtime"
            ),
        },
    }


def validate_file(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("scene bridge JSON must be an object")
    return build_native_scene_bundle(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_bridge")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_file(args.scene_bridge)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "draw_count": report["draw_count"],
        "coverage": report["coverage"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
