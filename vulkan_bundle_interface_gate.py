"""Validate the descriptor/resource interface of a prepared BMW Vulkan bundle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.BMWVulkanInterfaceGate/1"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _descriptor_rows(compile_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for shader in compile_report.get("shader_results", []) or []:
        reflection = shader.get("reflection") or {}
        for descriptor in reflection.get("descriptors", []) or []:
            row = dict(descriptor)
            row["shader_stage"] = shader.get("stage")
            row["shader_path"] = shader.get("path")
            rows.append(row)
    return rows


def validate_bmw_vulkan_interface(
    bundle_dir: str | Path,
    compile_report: str | Path | dict[str, Any],
) -> dict[str, Any]:
    root = Path(bundle_dir)
    manifest = _load(root / "bundle_manifest.json")
    report = (
        _load(compile_report)
        if isinstance(compile_report, (str, Path))
        else dict(compile_report)
    )

    blockers: list[str] = []
    if manifest.get("format") != "SHIFT.BMWVulkanBundle/1":
        blockers.append("vulkan-interface:invalid-bundle-format")
    if report.get("format") != "SHIFT.VulkanBundleSPIRV/1":
        blockers.append("vulkan-interface:invalid-spirv-report")
    if report.get("ready") is not True:
        blockers.extend(report.get("blocking_reasons") or ["vulkan-interface:spirv-not-ready"])

    descriptors = _descriptor_rows(report)
    descriptor_keys = [
        (int(row.get("set", -1)), int(row.get("binding", -1)), str(row.get("shader_stage") or ""))
        for row in descriptors
    ]
    if len(descriptor_keys) != len(set(descriptor_keys)):
        blockers.append("vulkan-interface:duplicate-reflected-descriptor")
    provided_2d: set[int] = set()
    texture_packet = root / "textures.svtp"
    if texture_packet.is_file():
        data = texture_packet.read_bytes()
        if len(data) >= 20 and data[:4] == b"SVTP":
            count = int.from_bytes(data[8:12], "little")
            record_offset = 20
            for index in range(count):
                pos = record_offset + index * 24
                if pos + 24 <= len(data):
                    provided_2d.add(int.from_bytes(data[pos:pos + 4], "little"))

    provided_cube: set[int] = set()
    cube_packet = root / "environment_cube.svcp"
    if cube_packet.is_file():
        data = cube_packet.read_bytes()
        if len(data) >= 28 and data[:4] == b"SVCP":
            provided_cube.add(int.from_bytes(data[8:12], "little"))

    descriptor_checks: list[dict[str, Any]] = []
    for descriptor in descriptors:
        set_index = int(descriptor.get("set", -1))
        binding = int(descriptor.get("binding", -1))
        descriptor_type = str(descriptor.get("descriptor_type") or "")
        resource_type = str(descriptor.get("resource_type") or "")
        status = "observed"
        if set_index == 0:
            if descriptor_type != "uniform-buffer" or binding not in {14, 15}:
                status = "mismatch"
                blockers.append(
                    f"vulkan-interface:unsupported-set0-descriptor:{binding}"
                )
        elif set_index == 1:
            if resource_type == "samplerCube":
                if binding not in provided_cube:
                    status = "blocked"
                    blockers.append(
                        f"vulkan-interface:missing-cube-resource:s{binding}"
                    )
            elif resource_type == "sampler2D":
                if binding not in provided_2d:
                    status = "blocked"
                    blockers.append(
                        f"vulkan-interface:missing-2d-resource:s{binding}"
                    )
            else:
                status = "mismatch"
                blockers.append(
                    f"vulkan-interface:unsupported-resource-type:s{binding}:{resource_type}"
                )
        else:
            status = "mismatch"
            blockers.append(
                f"vulkan-interface:unsupported-descriptor-set:{set_index}"
            )
        shader_stage = str(descriptor.get("stage") or "")
        if set_index == 0:
            expected_stage = {14: "vertex", 15: "fragment"}.get(binding)
            if expected_stage is not None and shader_stage != expected_stage:
                status = "mismatch"
                blockers.append(
                    f"vulkan-interface:set0-stage-mismatch:{binding}:{shader_stage or 'missing'}"
                )
        elif set_index == 1 and shader_stage != "fragment":
            status = "mismatch"
            blockers.append(
                f"vulkan-interface:set1-stage-unsupported:{binding}:{shader_stage or 'missing'}"
            )

        descriptor_checks.append({
            "set": set_index,
            "binding": binding,
            "descriptor_type": descriptor_type,
            "resource_type": resource_type,
            "shader_stage": shader_stage,
            "shader_path": descriptor.get("shader_path"),
            "status": status,
        })

    return {
        "format": FORMAT,
        "version": 1,
        "ready": not blockers,
        "status": "ready" if not blockers else "blocked",
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "descriptors": descriptor_checks,
        "provided_resources": {
            "2d_sampler_registers": sorted(provided_2d),
            "cube_sampler_registers": sorted(provided_cube),
        },
        "policy": {
            "constants": "set0 bindings 14/15",
            "textures": "set1 D3D9 sampler register preserved as Vulkan binding",
            "cube": "set1 D3D9 sampler register preserved as Vulkan binding",
            "extra_resources_allowed": True,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate BMW Vulkan descriptor/resource interface")
    parser.add_argument("bundle_dir")
    parser.add_argument("spirv_report")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    result = validate_bmw_vulkan_interface(args.bundle_dir, args.spirv_report)
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": result["format"],
        "status": result["status"],
        "ready": result["ready"],
        "blocking_reasons": result["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
