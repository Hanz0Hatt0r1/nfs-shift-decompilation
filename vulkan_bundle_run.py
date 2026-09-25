"""Run one prepared BMW Vulkan bundle through compile, interface and native execution gates."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from vulkan_bundle_interface_gate import validate_bmw_vulkan_interface
from vulkan_bundle_spirv import compile_bmw_vulkan_bundle, write_compile_report

FORMAT = "SHIFT.BMWVulkanRunner/1"


def run_bmw_vulkan_bundle(
    bundle_dir: str | Path,
    *,
    executable: str | Path = "native_vulkan/build/shift_vulkan_bundle_execute",
    validator: str | None = None,
    output: str | Path | None = None,
    prepare_only: bool = False,
) -> dict[str, Any]:
    root = Path(bundle_dir)
    if not (root / "bundle_manifest.json").is_file():
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": ["vulkan-runner:bundle-manifest-missing"],
        }

    spirv_report_path = root / "spirv_report.json"
    compile_report = compile_bmw_vulkan_bundle(root, validator=validator)
    spirv_report_path.write_text(
        json.dumps(compile_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result: dict[str, Any] = {
        "format": FORMAT,
        "status": "compiled" if compile_report.get("ready") else "blocked",
        "ready": False,
        "gates": {
            "spirv": compile_report,
            "interface": None,
        },
        "native": {
            "status": "not-run",
            "executable": str(executable),
            "output": str(output or root / "vulkan_render.ppm"),
        },
        "artifacts": {
            "spirv_report": {
                "path": str(spirv_report_path),
                "sha256": hashlib.sha256(spirv_report_path.read_bytes()).hexdigest(),
            }
        },
    }

    if not compile_report.get("ready"):
        result["blocking_reasons"] = list(
            compile_report.get("blocking_reasons") or
            ["vulkan-runner:spirv-not-ready"]
        )
        return result

    interface = validate_bmw_vulkan_interface(root, compile_report)
    interface_path = root / "vulkan_interface.json"
    interface_path.write_text(
        json.dumps(interface, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result["gates"]["interface"] = interface
    result["artifacts"]["interface"] = {
        "path": str(interface_path),
        "sha256": hashlib.sha256(interface_path.read_bytes()).hexdigest(),
    }

    if not interface.get("ready"):
        result["status"] = "blocked"
        result["blocking_reasons"] = list(
            interface.get("blocking_reasons") or
            ["vulkan-runner:interface-not-ready"]
        )
        return result

    result["ready"] = True
    if prepare_only:
        result["status"] = "ready"
        return result

    exe = Path(executable)
    if not exe.is_file():
        result["status"] = "blocked"
        result["ready"] = False
        result["blocking_reasons"] = ["vulkan-runner:executable-missing"]
        result["native"]["status"] = "executable-missing"
        return result

    output_path = Path(output) if output is not None else root / "vulkan_render.ppm"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [str(exe), str(root), str(output_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    result["native"].update({
        "status": "rendered" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    })
    if proc.returncode != 0:
        result["status"] = "failed"
        result["ready"] = False
        result["blocking_reasons"] = ["vulkan-runner:native-execution-failed"]
        return result
    if not output_path.is_file() or output_path.stat().st_size == 0:
        result["status"] = "failed"
        result["ready"] = False
        result["native"]["status"] = "missing-output"
        result["blocking_reasons"] = ["vulkan-runner:output-missing"]
        return result

    result["status"] = "rendered"
    result["native"]["output_sha256"] = hashlib.sha256(
        output_path.read_bytes()
    ).hexdigest()
    result["native"]["output"] = str(output_path)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run SHIFT.BMWVulkanBundle/1 through Vulkan gates and native execution"
    )
    parser.add_argument("bundle_dir")
    parser.add_argument("--executable", default="native_vulkan/build/shift_vulkan_bundle_execute")
    parser.add_argument("--validator")
    parser.add_argument("--output")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args(argv)

    result = run_bmw_vulkan_bundle(
        args.bundle_dir,
        executable=args.executable,
        validator=args.validator,
        output=args.output,
        prepare_only=args.prepare_only,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"ready", "rendered"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
