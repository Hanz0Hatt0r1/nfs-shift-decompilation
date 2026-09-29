"""Bridge an existing real BMW material-slice report into the Vulkan bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping, Iterable, Sequence

from bmw_vulkan_bundle import TARGET_MEB, build_bmw_vulkan_bundle
from bmw_vulkan_bundle_set import index_bmw_vulkan_bundle_set
from draw_packets import norm_ref
from shift_importer import BFF
from vulkan_dds_bridge import bridge_bmw_dds_resources

FORMAT = "SHIFT.BMWMaterialSliceVulkan/1"
SET_FORMAT = "SHIFT.BMWMaterialSliceVulkanSet/1"


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


def _validate_vulkan_shader_sources(
    command: Mapping[str, Any],
    submesh_indices: Sequence[int] | None = None,
) -> list[str]:
    blockers: list[str] = []
    submeshes = command.get("submeshes", []) or []
    indices = (
        list(range(len(submeshes)))
        if submesh_indices is None
        else [int(index) for index in submesh_indices]
    )
    for index in indices:
        if index < 0 or index >= len(submeshes):
            blockers.append(
                f"bmw-material-vulkan:submesh-index-out-of-range:{index}"
            )
            continue
        submesh = submeshes[index]
        shader = submesh.get("shader") if isinstance(submesh, Mapping) else None
        if not isinstance(shader, Mapping):
            blockers.append(f"bmw-material-vulkan:shader-missing:{index}")
            continue
        for stage in ("vertex", "pixel"):
            if not shader.get(f"vulkan_{stage}_glsl"):
                blockers.append(
                    f"bmw-material-vulkan:vulkan-{stage}-source-missing:{index}"
                )
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


def _sanitize_dds_bridge_provenance(
    dds_bridge: Mapping[str, Any],
    bundle_dir: Path,
    *,
    texture_provenance: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    sanitized = json.loads(json.dumps(dds_bridge))
    by_register = {
        int(row["register"]): str(row["reference"])
        for row in texture_provenance
        if row.get("register") is not None and row.get("reference")
    }
    for row in sanitized.get("decoded_sources") or []:
        register = row.get("register")
        if row.get("kind") == "2d" and register is not None:
            row["source_path"] = by_register.get(int(register), f"material-sampler:s{register}")
        elif row.get("kind") == "cube":
            row["source_path"] = "environment-cube:s3"
    provenance = sanitized.get("provenance") or {}
    provenance_file = provenance.get("path")
    if provenance_file:
        path = bundle_dir / str(provenance_file)
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            for row in data.get("sources") or []:
                register = row.get("register")
                if row.get("kind") == "2d" and register is not None:
                    row["source_path"] = by_register.get(int(register), f"material-sampler:s{register}")
                elif row.get("kind") == "cube":
                    row["source_path"] = "environment-cube:s3"
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            provenance["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    sanitized["provenance"] = provenance
    return sanitized

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

    external = []
    for row in merged.get("external_samplers") or []:
        normalized = dict(row)
        if (
            cube_packet
            and int(normalized.get("d3d9_sampler_register", -1)) == 3
            and str(normalized.get("sampler_type") or "") == "samplerCube"
        ):
            normalized["status"] = "provided-via-dds-bridge"
        external.append(normalized)
    merged["external_samplers"] = external

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
    merged["ready"] = not merged["blocking_reasons"]
    merged["status"] = "ready" if merged["ready"] else "partial"

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

    shader_blockers = _validate_vulkan_shader_sources(command, [submesh_index])
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
        if source_dds_map or dds_blockers or environment_cube_dds is not None:
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
                    dds_bridge = _sanitize_dds_bridge_provenance(
                        dds_bridge,
                        bundle_dir,
                        texture_provenance=dds_provenance,
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
        "dds_source_bffs": [path.name for path in source_bff_list],
    }
    source_path = Path(output_dir) / "material_slice_source.json"
    source_path.write_text(
        json.dumps(source_record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result["source"] = source_record
    artifacts = dict(result.get("artifacts") or {})
    result["artifacts"] = artifacts
    artifacts["material_slice_source"] = {
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
        "dds_bridge": result.get("dds_bridge"),
    }



def _normalize_set_submesh_indices(
    command: Mapping[str, Any],
    submesh_indices: Sequence[int] | None,
) -> list[int]:
    submeshes = command.get("submeshes") or []
    if not submeshes:
        raise ValueError("BMW material slice render command contains no submeshes")
    indices = (
        list(range(len(submeshes)))
        if submesh_indices is None
        else [int(index) for index in submesh_indices]
    )
    if not indices:
        raise ValueError("BMW material Vulkan set requires at least one submesh")
    if len(indices) != len(set(indices)):
        raise ValueError("BMW material Vulkan set submesh indices must be unique")
    for index in indices:
        _find_selected_submesh(command, index)
    return indices


def build_bmw_vulkan_set_from_material_slice(
    material_slice: str | Path | Mapping[str, Any],
    output_dir: str | Path,
    *,
    textures: str | Path | Mapping[str, Any] | None = None,
    environment_cube: str | Path | Mapping[str, Any] | None = None,
    source_bffs: Iterable[str | Path] = (),
    environment_cube_dds: str | Path | None = None,
    submesh_indices: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Build one independently bridged child bundle for every selected submesh."""
    payload = _load(material_slice)
    command = _find_render_command(payload)
    _find_mesh(payload, command)

    mesh_ref = (command.get("mesh") or {}).get("ref")
    if mesh_ref != TARGET_MEB:
        raise ValueError(
            "BMW material slice is not the exact KIT00 body MEB required by Vulkan bundle"
        )

    indices = _normalize_set_submesh_indices(command, submesh_indices)
    shader_blockers = _validate_vulkan_shader_sources(command, indices)
    source_bff_list = [Path(path) for path in source_bffs]
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    child_results: list[dict[str, Any]] = []
    adapter_blockers: list[str] = []

    if not shader_blockers:
        for draw_order, submesh_index in enumerate(indices):
            child = out / "draws" / f"submesh_{submesh_index:03d}"
            result = build_bmw_vulkan_from_material_slice(
                payload,
                child,
                textures=textures,
                environment_cube=environment_cube,
                source_bffs=source_bff_list,
                environment_cube_dds=environment_cube_dds,
                submesh_index=submesh_index,
            )
            child_reasons = [
                str(reason)
                for reason in result.get("blocking_reasons") or []
            ]
            if result.get("ready") is not True:
                adapter_blockers.extend(
                    f"bmw-material-vulkan-set:submesh-{submesh_index}:{reason}"
                    for reason in (
                        child_reasons
                        or ["material-adapter-not-ready"]
                    )
                )
            child_results.append({
                "draw_order": draw_order,
                "source_submesh_index": submesh_index,
                "bundle_path": str(child.relative_to(out)),
                "format": result.get("format"),
                "status": result.get("status"),
                "ready": result.get("ready") is True,
                "blocking_reasons": child_reasons,
                "source": result.get("source"),
                "dds_bridge": result.get("dds_bridge"),
            })
    else:
        adapter_blockers.extend(shader_blockers)
        for draw_order, submesh_index in enumerate(indices):
            child_results.append({
                "draw_order": draw_order,
                "source_submesh_index": submesh_index,
                "bundle_path": f"draws/submesh_{submesh_index:03d}",
                "format": FORMAT,
                "status": "blocked",
                "ready": False,
                "blocking_reasons": [
                    reason
                    for reason in shader_blockers
                    if reason.endswith(f":{submesh_index}")
                ],
                "source": None,
                "dds_bridge": None,
            })

    bundle_set = index_bmw_vulkan_bundle_set(
        command,
        out,
        submesh_indices=indices,
    )
    blockers = list(adapter_blockers)
    blockers.extend(
        str(reason)
        for reason in bundle_set.get("blocking_reasons") or []
    )
    blockers = list(dict.fromkeys(blockers))

    source_record = {
        "format": SET_FORMAT,
        "material_slice_format": payload.get("format"),
        "material_slice_path": payload.get("_source_path"),
        "material_slice_sha256": payload.get("_source_sha256"),
        "render_command_format": command.get("format"),
        "render_command_identity": command.get("identity"),
        "mesh_ref": mesh_ref,
        "target_meb": TARGET_MEB,
        "selected_submesh_indices": indices,
        "dds_source_bffs": [path.name for path in source_bff_list],
    }
    source_path = out / "material_slice_set_source.json"
    source_path.write_text(
        json.dumps(source_record, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    ready = not blockers and bundle_set.get("ready") is True
    return {
        "format": SET_FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "bundle_set": bundle_set,
        "draw_count": len(child_results),
        "draws": child_results,
        "source": source_record,
        "artifacts": {
            "bundle_set_manifest": {
                "path": "bundle_set_manifest.json",
                "sha256": hashlib.sha256(
                    (out / "bundle_set_manifest.json").read_bytes()
                ).hexdigest(),
            },
            "draw_order": bundle_set.get("artifacts", {}).get("draw_order"),
            "material_slice_set_source": {
                "path": source_path.name,
                "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            },
        },
    }

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Bridge a BMW material-slice JSON into one Vulkan bundle "
            "or an ordered multi-submesh bundle set"
        )
    )
    parser.add_argument("material_slice")
    parser.add_argument("output_dir")
    parser.add_argument("--textures")
    parser.add_argument("--environment-cube")
    parser.add_argument("--source-bff", action="append", default=[])
    parser.add_argument("--environment-cube-dds")
    parser.add_argument("--submesh-index", type=int, default=0)
    parser.add_argument("--all-submeshes", action="store_true")
    args = parser.parse_args(argv)

    common = {
        "textures": args.textures,
        "environment_cube": args.environment_cube,
        "source_bffs": args.source_bff,
        "environment_cube_dds": args.environment_cube_dds,
    }
    if args.all_submeshes:
        result = build_bmw_vulkan_set_from_material_slice(
            args.material_slice,
            args.output_dir,
            **common,
        )
    else:
        result = build_bmw_vulkan_from_material_slice(
            args.material_slice,
            args.output_dir,
            submesh_index=args.submesh_index,
            **common,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
