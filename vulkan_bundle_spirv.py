"""Compile Vulkan shader sources from a prepared BMW Vulkan bundle.

Compilation is optional on developer machines without glslangValidator. When the
compiler exists, every copied bundle shader must compile to SPIR-V or the bundle
compile gate fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VulkanBundleSPIRV/1"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def compile_bmw_vulkan_bundle(
    bundle_dir: str | Path,
    *,
    validator: str | None = None,
) -> dict[str, Any]:
    root = Path(bundle_dir)
    manifest_path = root / "bundle_manifest.json"
    if not manifest_path.is_file():
        raise ValueError("bundle manifest is missing")
    manifest = _load(manifest_path)
    if manifest.get("format") != "SHIFT.BMWVulkanBundle/1":
        raise ValueError("input is not SHIFT.BMWVulkanBundle/1")

    compiler = validator or shutil.which("glslangValidator")
    shader_rows = manifest.get("artifacts", {}).get("shaders") or []
    results: list[dict[str, Any]] = []

    if compiler is None:
        return {
            "format": FORMAT,
            "status": "unavailable",
            "ready": False,
            "validator": None,
            "shader_results": [],
            "blocking_reasons": ["vulkan-bundle-spirv:validator-unavailable"],
        }

    blockers: list[str] = []
    for row in shader_rows:
        relative = str(row.get("path") or "")
        stage = str(row.get("stage") or "").lower()
        source = root / relative
        if not source.is_file():
            blockers.append(f"vulkan-bundle-spirv:source-missing:{relative}")
            results.append({
                "path": relative,
                "stage": stage,
                "status": "missing",
            })
            continue
        if stage not in {"vertex", "pixel"}:
            blockers.append(f"vulkan-bundle-spirv:unsupported-stage:{stage or 'missing'}")
            results.append({
                "path": relative,
                "stage": stage,
                "status": "unsupported",
            })
            continue
        output = root / "spirv" / (source.name + ".spv")
        output.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [compiler, "-V", "-S", "vert" if stage == "vertex" else "frag",
             str(source), "-o", str(output)],
            capture_output=True,
            text=True,
            check=False,
        )
        ok = proc.returncode == 0 and output.is_file() and output.stat().st_size > 0
        results.append({
            "path": relative,
            "stage": stage,
            "status": "compiled" if ok else "failed",
            "spirv_path": str(output.relative_to(root)) if ok else None,
            "spirv_sha256": hashlib.sha256(output.read_bytes()).hexdigest() if ok else None,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        })
        if not ok:
            blockers.append(f"vulkan-bundle-spirv:compile-failed:{relative}")

    return {
        "format": FORMAT,
        "status": "ready" if not blockers else "invalid",
        "ready": not blockers,
        "validator": compiler,
        "shader_results": results,
        "blocking_reasons": list(dict.fromkeys(blockers)),
    }


def write_compile_report(
    bundle_dir: str | Path,
    output: str | Path,
    *,
    validator: str | None = None,
) -> dict[str, Any]:
    report = compile_bmw_vulkan_bundle(bundle_dir, validator=validator)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile Vulkan shaders from SHIFT.BMWVulkanBundle/1")
    parser.add_argument("bundle_dir")
    parser.add_argument("output")
    parser.add_argument("--validator")
    args = parser.parse_args(argv)
    result = write_compile_report(args.bundle_dir, args.output, validator=args.validator)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
