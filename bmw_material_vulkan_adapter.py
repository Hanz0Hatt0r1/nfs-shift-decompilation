"""Bridge an existing real BMW material-slice report into the Vulkan bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping, Iterable

from bmw_vulkan_bundle import TARGET_MEB, build_bmw_vulkan_bundle
from draw_packets import norm_ref
from shift_importer import BFF
from vulkan_dds_bridge import bridge_bmw_dds_resources

FORMAT = "SHIFT.BMWMaterialSliceVulkan/1"


def _load(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    path = Path(value)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    payload["_source_path"] = str(path)
    payload["_source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return payload


def _find_render_command(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("format") == "SHIFT.RenderCommand/1":
        return dict(payload)

    candidates = [
        payload.get("render_command"),
        payload.get("command"),
        payload.get("render"),
        payload.get("packet"),
    ]
    for candidate in candidates:
        if isinstance(candidate, Mapping):
            found = _find_render_command(candidate)
            if found:
                return found

    for value in payload.values():
        if isinstance(value, Mapping) and value.get("format") == "SHIFT.RenderCommand/1":
            return dict(value)

    raise ValueError("BMW material slice does not contain SHIFT.RenderCommand/1")


def _find_mesh(payload: Mapping[str, Any], command: Mapping[str, Any]) -> dict[str, Any]:
    mesh = command.get("neutral_mesh")
    if isinstance(mesh, Mapping):
        return dict(mesh)
    mesh = command.get("mesh_data")
    if isinstance(mesh, Mapping):
        return dict(mesh)

    for candidate in (
        command.get("mesh"),
        payload.get("mesh"),
        payload.get("neutral_mesh"),
        payload.get("mesh_json"),
    ):
        if isinstance(candidate, Mapping) and "vertices" in candidate and "indices" in candidate:
            return dict(candidate)

    for value in payload.values():
        if isinstance(value, Mapping) and "vertices" in value and "indices" in value:
            return dict(value)

    raise ValueError("BMW material slice does not contain a neutral mesh JSON payload")


def _validate_vulkan_shader_sources(command: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    for index, submesh in enumerate(command.get("submeshes", []) or []):
        shader = submesh.get("shader") or {}
        if not isinstance(shader, Mapping):
            blockers.append(f"bmw-material-vulkan:shader-missing:{index}")
            continue
        for stage in ("vertex", "pixel"):
            if not shader.get(f"vulkan_{stage}_glsl"):
                blockers.append(f"bmw-material-vulkan:vulkan-{stage}-source-missing:{index}")
    return blockers


def _find_selected_submesh(command: Mapping[str, Any], submesh_index: int) -> dict[str, Any]:
    submeshes = command.get("submeshes") or []
    if submesh_index < 0 or submesh_index >= len(submeshes):
        raise ValueError(f"submesh index out of range: {submesh_index}")
    value = submeshes[submesh_index]
    if not isinstance(value, Mapping):
        raise ValueError(f"submesh {submesh_index} is not an object")
    return dict(value)


def _extract_exact_material_dds(
    payload: Mapping[str, Any],
    command: Mapping[str, Any],
    source_bffs: Iterable[str | Path],
    temp_root: Path,
    *,
    submesh_index: int,
) -> tuple[dict[str, str], list[dict[str, Any]], list[str]]:
    sources = payload.get("texture_sources") or (payload.get("provenance") or {}).get("dds_sources") or []
    source_rows = [dict(row) for row in sources if isinstance(row, Mapping)]
    submesh = _find_selected_submesh(command, submesh_index)
    dds_map: dict[str, str] = {}
    provenance: list[dict[str, Any]] = []
    blockers: list[str] = []

    source_bff_list = [Path(path) for path in source_bffs]
    archives: list[tuple[Path, Any]] = []
    for path in source_bff_list:
        try:
            archives.append((path, BFF(path)))
        except Exception as error:
            blockers.append(f"bmw-material-vulkan:source-bff-open-failed:{path.name}:{type(error).__name__}")

    try:
        for texture_index, binding in enumerate(submesh.get("textures", []) or []):
            if not isinstance(binding, Mapping):
                blockers.append(f"bmw-material-vulkan:texture-binding-invalid:{texture_index}")
                continue
            register = binding.get("d3d9_sampler_register")
            ref = norm_ref(binding.get("ref"))
            if register is None or not ref:
                blockers.append(f"bmw-material-vulkan:texture-binding-missing-ref-or-register:{texture_index}")
                continue
            register = int(register)

            matches = [
                row for row in source_rows
                if norm_ref(row.get("path")) == ref
            ]
            if len(matches) != 1:
                blockers.append(
                    f"bmw-material-vulkan:dds-source-provenance-{('missing' if not matches else 'ambiguous')}:{ref}"
                )
                continue
            source = matches[0]
            archive_name = str(source.get("archive") or "")
            candidates = [
                (archive_path, archive)
                for archive_path, archive in archives
                if archive_path.name == archive_name
            ]
            if len(candidates) != 1:
                blockers.append(
                    f"bmw-material-vulkan:dds-source-archive-{('missing' if not candidates else 'ambiguous')}:{archive_name}"
                )
                continue

            archive_path, archive = candidates[0]
            entry_hits = [
                entry for entry in archive.entries
                if norm_ref(getattr(entry, "path", "")) == ref
            ]
            if len(entry_hits) != 1:
                blockers.append(
                    f"bmw-material-vulkan:dds-entry-{('missing' if not entry_hits else 'ambiguous')}:{ref}"
                )
                continue

            entry = entry_hits[0]
            data = archive.extract_entry(entry)
            digest = hashlib.sha256(data).hexdigest()
            expected = str(source.get("sha256") or "")
            if expected and digest != expected:
                blockers.append(
                    f"bmw-material-vulkan:dds-source-sha256-mismatch:{ref}"
                )
                continue

            target = temp_root / f"s{register}_{texture_index}.dds"
            target.write_bytes(data)
            dds_map[str(register)] = str(target)
            provenance.append({
                "register": register,
                "reference": ref,
                "archive": archive_path.name,
                "path": getattr(entry, "path", ref),
                "source_sha256": digest,
                "expected_sha256": expected,
            })
    finally:
        for _, archive in archives:
            archive.close()

    return dds_map, provenance, blockers


def _merge_dds_bridge_into_bundle(
    bundle: dict[str, Any],
    dds_bridge: Mapping[str, Any],
    bundle_dir: Path,
) -> dict[str, Any]:
    merged = dict(bundle)
    blockers = list(bundle.get("blocking_reasons") or [])
    for reason in dds_bridge.get("blocking_reasons") or []:
        blockers.append(str(reason))

    artifacts = dict(merged.get("artifacts") or {})
    packets = dds_bridge.get("packets") or {}
    tex_packet = packets.get("textures")
    cube_packet = packets.get("environment_cube")

    if tex_packet:
        artifacts["textures"] = {
            "path": tex_packet["path"],
            "sha256": hashlib.sha256((bundle_dir / tex_packet["path"]).read_bytes()).hexdigest(),
            "ready": bool(dds_bridge.get("ready")) and not any(
                str(reason).startswith("dds-bridge:missing-2d-ds:")
                or str(reason).startswith("dds-bridge:cubemap-supplied-to-2d-register:")
                for reason in dds_bridge.get("blocking_reasons") or []
            ),
            "texture_count": len(dds_bridge.get("material_2d_registers") or []),
        }
    if cube_packet:
        artifacts["environment_cube"] = {
            "path": cube_packet["path"],
            "sha256": hashlib.sha256((bundle_dir / cube_packet["path"]).read_bytes()).hexdigest(),
            "ready": True,
            "register": 3,
        }

    artifacts["dds_bridge"] = {
        "format": dds_bridge.get("format"),
        "ready": dds_bridge.get("ready"),
        "provenance": dds_bridge.get("provenance"),
    }
    merged["artifacts"] = artifacts
    merged["dds_bridge"] = dds_bridge

    # The base bundle emits these blockers when its resources were intentionally
    # deferred. The DDS bridge becomes authoritative for the supplied material
    # textures/cube, while any remaining bridge blockers stay fail-closed.
    base_blockers = []
    for reason in blockers:
        if reason == "bmw-vulkan-bundle:material-textures-not-supplied" and tex_packet:
            continue
        if reason == "bmw-vulkan-bundle:environment-cube-not-supplied" and cube_packet:
            continue
        base_blockers.append(reason)
    merged["blocking_reasons"] = list(dict.fromkeys(base_blockers))
    merged["status"] = "ready" if not merged["blocking_reasons"] else "partial"

    manifest = bundle_dir / "bundle_manifest.json"
    manifest.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    merged["manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    return merged


def build_bmw_vulkan_from_material_slice(
    material_slice: str | Path | Mapping[str, Any],
    output_dir: str | Path,
    *,
    textures: str | Path | Mapping[str, Any] | None = None,
    environment_cube: str | Path | Mapping[str, Any] | None = None,
    source_bffs: Iterable[str | Path] = (),
    environment_cube_dds: str | Path | None = None,
    submesh_index: int = 0,
) -> dict[str, Any]:
    payload = _load(material_slice)
    command = _find_render_command(payload)
    mesh = _find_mesh(payload, command)

    mesh_ref = (command.get("mesh") or {}).get("ref")
    if mesh_ref != TARGET_MEB:
        raise ValueError(
            "BMW material slice is not the exact KIT00 body MEB required by Vulkan bundle"
        )

    shader_blockers = _validate_vulkan_shader_sources(command)
    if shader_blockers:
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": shader_blockers,
            "source": {
                "material_slice_path": payload.get("_source_path"),
                "material_slice_sha256": payload.get("_source_sha256"),
                "mesh_ref": mesh_ref,
            },
        }

    binding = {
        "format": "SHIFT.RenderBinding/1",
        "render_commands": [command],
    }

    bundle_dir = Path(output_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    source_bff_list = [Path(path) for path in source_bffs]
    source_dds_map: dict[str, str] = {}
    dds_provenance: list[dict[str, Any]] = []
    dds_blockers: list[str] = []

    with TemporaryDirectory(prefix="shift_bmw_dds_") as temp_dir:
        if source_bff_list:
            source_dds_map, dds_provenance, dds_blockers = _extract_exact_material_dds(
                payload,
                command,
                source_bff_list,
                Path(temp_dir),
                submesh_index=submesh_index,
            )

        result = build_bmw_vulkan_bundle(
            binding,
            mesh,
            output_dir,
            textures=textures,
            environment_cube=environment_cube,
            command_index=0,
            submesh_index=submesh_index,
        )

        dds_bridge = None
        if source_dds_map or environment_cube_dds is not None:
            if dds_blockers:
                dds_bridge = {
                    "format": "SHIFT.VulkanDDSResourceBridge/1",
                    "status": "blocked",
                    "ready": False,
                    "blocking_reasons": list(dict.fromkeys(dds_blockers)),
                    "packets": {"textures": None, "environment_cube": None},
                    "material_2d_registers": sorted(int(x) for x in source_dds_map),
                    "provenance": None,
                }
            else:
                try:
                    dds_bridge = bridge_bmw_dds_resources(
                        command,
                        source_dds_map,
                        bundle_dir,
                        environment_cube_dds=environment_cube_dds,
                    )
                except (OSError, ValueError, TypeError) as error:
                    dds_bridge = {
                        "format": "SHIFT.VulkanDDSResourceBridge/1",
                        "status": "blocked",
                        "ready": False,
                        "blocking_reasons": [
                            f"bmw-material-vulkan:dds-bridge-failed:{type(error).__name__}"
                        ],
                        "packets": {"textures": None, "environment_cube": None},
                        "provenance": None,
                    }

        if dds_bridge is not None:
            result = _merge_dds_bridge_into_bundle(result, dds_bridge, bundle_dir)

        source_record = {
        "format": FORMAT,
        "material_slice_format": payload.get("format"),
        "material_slice_path": payload.get("_source_path"),
        "material_slice_sha256": payload.get("_source_sha256"),
        "render_command_format": command.get("format"),
        "render_command_identity": command.get("identity"),
        "mesh_ref": mesh_ref,
        "target_meb": TARGET_MEB,
        "submesh_index": submesh_index,
        "dds_sources": dds_provenance,
        "dds_source_bffs": [str(path) for path in source_bff_list],
    }
    source_path = Path(output_dir) / "material_slice_source.json"
    source_path.write_text(
        json.dumps(source_record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result["source"] = source_record
    result["artifacts"]["material_slice_source"] = {
        "path": str(source_path.relative_to(Path(output_dir))),
        "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
    }
    bundle_result = dict(result)
    bundle_result.pop("format", None)
    return {
        "format": FORMAT,
        "status": result["status"],
        "ready": result["ready"],
        "blocking_reasons": result["blocking_reasons"],
        "bundle": bundle_result,
        "source": source_record,
        "artifacts": result.get("artifacts", {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bridge a BMW material-slice JSON into SHIFT.BMWVulkanBundle/1"
    )
    parser.add_argument("material_slice")
    parser.add_argument("output_dir")
    parser.add_argument("--textures")
    parser.add_argument("--environment-cube")
    parser.add_argument("--source-bff", action="append", default=[])
    parser.add_argument("--environment-cube-dds")
    parser.add_argument("--submesh-index", type=int, default=0)
    args = parser.parse_args(argv)
    result = build_bmw_vulkan_from_material_slice(
        args.material_slice,
        args.output_dir,
        textures=args.textures,
        environment_cube=args.environment_cube,
        source_bffs=args.source_bff,
        environment_cube_dds=args.environment_cube_dds,
        submesh_index=args.submesh_index,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
