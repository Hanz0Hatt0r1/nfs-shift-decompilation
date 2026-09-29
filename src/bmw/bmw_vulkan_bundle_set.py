"""Compose an ordered multi-submesh BMW Vulkan draw set from validated sub-bundles.

The existing SHIFT.BMWVulkanBundle/1 remains the atomic ABI.  This layer does
not merge shader/material state across submeshes; it preserves each submesh as
an independently gated bundle and records deterministic draw order.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from bmw_vulkan_bundle import build_bmw_vulkan_bundle

FORMAT = "SHIFT.BMWVulkanBundleSet/1"


def _load(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    payload = json.loads(Path(value).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {value}")
    return payload


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _selected_command(source: Mapping[str, Any], command_index: int) -> dict[str, Any]:
    fmt = source.get("format")
    if fmt == "SHIFT.RenderCommand/1":
        if command_index != 0:
            raise ValueError("RenderCommand input only supports command index 0")
        return dict(source)
    if fmt != "SHIFT.RenderBinding/1":
        raise ValueError("input must be SHIFT.RenderBinding/1 or SHIFT.RenderCommand/1")
    commands = source.get("render_commands") or []
    if command_index < 0 or command_index >= len(commands):
        raise ValueError(f"command index out of range: {command_index}")
    command = commands[command_index]
    if not isinstance(command, Mapping):
        raise ValueError(f"render command {command_index} is not an object")
    return dict(command)


def _normalize_indices(
    command: Mapping[str, Any],
    submesh_indices: Sequence[int] | None,
) -> list[int]:
    submeshes = command.get("submeshes") or []
    if not submeshes:
        raise ValueError("render command contains no submeshes")
    if submesh_indices is None:
        indices = list(range(len(submeshes)))
    else:
        indices = [int(index) for index in submesh_indices]
    if not indices:
        raise ValueError("bundle set requires at least one submesh")
    if len(indices) != len(set(indices)):
        raise ValueError("bundle set submesh indices must be unique")
    for index in indices:
        if index < 0 or index >= len(submeshes):
            raise ValueError(f"submesh index out of range: {index}")
        if not isinstance(submeshes[index], Mapping):
            raise ValueError(f"submesh {index} is not an object")
    return indices


def index_bmw_vulkan_bundle_set(
    render_command: str | Path | Mapping[str, Any],
    output_dir: str | Path,
    *,
    command_index: int = 0,
    submesh_indices: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Index already-built canonical child bundles into one ordered draw set.

    This is intentionally separate from child construction so adapters that
    attach per-submesh resources/provenance can finalize those child manifests
    before the top-level set is hashed and admitted.
    """
    command_source = _load(render_command)
    command = _selected_command(command_source, command_index)
    indices = _normalize_indices(command, submesh_indices)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    draws: list[dict[str, Any]] = []
    blockers: list[str] = []
    submeshes = command.get("submeshes") or []

    for draw_order, source_index in enumerate(indices):
        submesh = dict(submeshes[source_index])
        child = out / "draws" / f"submesh_{source_index:03d}"
        manifest = child / "bundle_manifest.json"

        child_report: dict[str, Any] = {}
        child_reasons: list[str] = []
        child_status = "missing"
        child_ready = False
        manifest_sha256 = None

        if not manifest.is_file():
            child_reasons.append("manifest-missing")
        else:
            manifest_sha256 = hashlib.sha256(manifest.read_bytes()).hexdigest()
            try:
                child_report = _load(manifest)
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
                child_reasons.append(
                    f"manifest-invalid:{type(error).__name__}"
                )
            else:
                child_status = str(child_report.get("status") or "unknown")
                if child_report.get("format") != "SHIFT.BMWVulkanBundle/1":
                    child_reasons.append("invalid-bundle-format")
                child_reasons.extend(
                    str(reason)
                    for reason in child_report.get("blocking_reasons") or []
                )
                child_ready = (
                    child_report.get("format") == "SHIFT.BMWVulkanBundle/1"
                    and child_report.get("ready") is True
                    and not child_reasons
                )
                if not child_ready and not child_reasons:
                    child_reasons.append("not-ready")

        if not child_ready:
            blockers.extend(
                f"bundle-set:submesh-{source_index}:{reason}"
                for reason in child_reasons
            )

        shader = submesh.get("shader") or {}
        permutation = (
            shader.get("permutation_identity")
            if isinstance(shader, Mapping)
            else None
        ) or {}
        draws.append({
            "draw_order": draw_order,
            "source_submesh_index": source_index,
            "first_index": int(submesh.get("first_index", 0)),
            "index_count": int(submesh.get("index_count", 0)),
            "bundle_path": str(child.relative_to(out)),
            "manifest_path": str(manifest.relative_to(out)),
            "manifest_sha256": manifest_sha256,
            "status": child_status,
            "ready": child_ready,
            "blocking_reasons": child_reasons,
            "shader_permutation_identity_sha256": (
                permutation.get("identity_sha256")
                if isinstance(permutation, Mapping) else None
            ),
        })

    draw_order_path = out / "bundle_set.paths"
    draw_order_path.write_text(
        "".join(f"{row['bundle_path']}\n" for row in draws),
        encoding="utf-8",
    )

    report: dict[str, Any] = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "source": {
            "render_command_format": command_source.get("format"),
            "command_index": command_index,
            "mesh_ref": (command.get("mesh") or {}).get("ref"),
            "selected_submesh_indices": indices,
        },
        "draw_count": len(draws),
        "draws": draws,
        "artifacts": {
            "draw_order": {
                "path": str(draw_order_path.relative_to(out)),
                "sha256": hashlib.sha256(draw_order_path.read_bytes()).hexdigest(),
                "entry_count": len(draws),
            },
        },
        "execution": {
            "status": "prepared",
            "contract": (
                "ordered atomic SHIFT.BMWVulkanBundle/1 draws; "
                "native multi-draw execution is a separate gate"
            ),
        },
    }
    manifest_path = out / "bundle_set_manifest.json"
    _write(manifest_path, report)
    report["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return report


def build_bmw_vulkan_bundle_set(
    render_command: str | Path | Mapping[str, Any],
    mesh: str | Path | Mapping[str, Any],
    output_dir: str | Path,
    *,
    textures: str | Path | Mapping[str, Any] | None = None,
    environment_cube: str | Path | Mapping[str, Any] | None = None,
    command_index: int = 0,
    submesh_indices: Sequence[int] | None = None,
) -> dict[str, Any]:
    command_source = _load(render_command)
    mesh_source = _load(mesh)
    command = _selected_command(command_source, command_index)
    indices = _normalize_indices(command, submesh_indices)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for source_index in indices:
        child = out / "draws" / f"submesh_{source_index:03d}"
        build_bmw_vulkan_bundle(
            command_source,
            mesh_source,
            child,
            textures=textures,
            environment_cube=environment_cube,
            command_index=command_index,
            submesh_index=source_index,
        )

    return index_bmw_vulkan_bundle_set(
        command_source,
        out,
        command_index=command_index,
        submesh_indices=indices,
    )

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare SHIFT.BMWVulkanBundleSet/1 from one RenderCommand"
    )
    parser.add_argument("render_command")
    parser.add_argument("mesh")
    parser.add_argument("output_dir")
    parser.add_argument("--textures")
    parser.add_argument("--environment-cube")
    parser.add_argument("--command-index", type=int, default=0)
    parser.add_argument("--submesh-index", action="append", type=int, dest="submesh_indices")
    args = parser.parse_args(argv)

    result = build_bmw_vulkan_bundle_set(
        args.render_command,
        args.mesh,
        args.output_dir,
        textures=args.textures,
        environment_cube=args.environment_cube,
        command_index=args.command_index,
        submesh_indices=args.submesh_indices,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
