"""One-command Linux bridge from RenderBinding/1 to the Vulkan geometry backend.

This runner keeps Python responsible for resource/IR interpretation and delegates
native submission to shift_vulkan_render_geometry. It supports a prepare-only mode
so CI and machines without Vulkan can still validate the exact handoff packet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from vulkan_geometry_packet import export_vulkan_geometry_packet

FORMAT = "SHIFT.VulkanRenderCommandRunner/1"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _select_command(binding: dict[str, Any], index: int) -> dict[str, Any]:
    if binding.get("format") != "SHIFT.RenderBinding/1":
        raise ValueError("input is not SHIFT.RenderBinding/1")
    commands = binding.get("render_commands") or []
    if not isinstance(commands, list) or not commands:
        raise ValueError("RenderBinding contains no render_commands")
    if index < 0 or index >= len(commands):
        raise ValueError(f"render command index out of range: {index}")
    command = commands[index]
    if not isinstance(command, dict):
        raise ValueError(f"render command {index} is not an object")
    return command


def run_vulkan_render_command(
    binding: str | Path | dict[str, Any],
    mesh: str | Path | dict[str, Any],
    packet_output: str | Path,
    render_output: str | Path,
    *,
    command_index: int = 0,
    submesh_index: int = 0,
    executable: str | Path = "native_vulkan/build/shift_vulkan_render_geometry",
    shader_dir: str | Path = "native_vulkan/build/shaders",
    prepare_only: bool = False,
) -> dict[str, Any]:
    render_binding = _load(binding) if isinstance(binding, (str, Path)) else dict(binding)
    mesh_data = _load(mesh) if isinstance(mesh, (str, Path)) else dict(mesh)
    command = _select_command(render_binding, command_index)

    packet_report = export_vulkan_geometry_packet(
        command,
        mesh_data,
        packet_output,
        submesh_index=submesh_index,
    )
    packet_path = Path(packet_output)
    packet_sha = hashlib.sha256(packet_path.read_bytes()).hexdigest()

    result: dict[str, Any] = {
        "format": FORMAT,
        "status": "prepared",
        "command_index": command_index,
        "submesh_index": submesh_index,
        "command": {
            "format": command.get("format"),
            "ready": bool(command.get("ready")),
            "blocking_reasons": list(command.get("blocking_reasons", []) or []),
            "mesh_ref": (command.get("mesh") or {}).get("ref"),
            "vertex_count": (command.get("mesh") or {}).get("vertex_count"),
            "triangle_count": (command.get("mesh") or {}).get("triangle_count"),
        },
        "packet": {
            "format": packet_report.get("format"),
            "version": packet_report.get("version"),
            "path": str(packet_path),
            "sha256": packet_sha,
            "vertex_count": packet_report.get("vertex_count"),
            "index_count": packet_report.get("index_count"),
            "attribute_count": len(packet_report.get("attributes") or []),
            "deferred_properties": packet_report.get("deferred_properties") or [],
        },
        "render": {
            "status": "not-run",
            "output": str(render_output),
            "executable": str(executable),
            "shader_dir": str(shader_dir),
        },
    }

    if prepare_only:
        return result

    exe = Path(executable)
    if not exe.exists():
        result["status"] = "blocked"
        result["render"]["status"] = "executable-missing"
        result["blocking_reasons"] = ["vulkan-runner:executable-missing"]
        return result

    output_path = Path(render_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [str(exe), str(packet_path), str(output_path), str(shader_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    result["render"].update({
        "status": "ok" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    })
    if proc.returncode != 0:
        result["status"] = "failed"
        result["blocking_reasons"] = ["vulkan-runner:native-render-failed"]
        return result

    if not output_path.exists() or output_path.stat().st_size == 0:
        result["status"] = "failed"
        result["render"]["status"] = "missing-output"
        result["blocking_reasons"] = ["vulkan-runner:output-missing"]
        return result

    result["status"] = "rendered"
    result["render"]["output_sha256"] = hashlib.sha256(output_path.read_bytes()).hexdigest()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one SHIFT RenderCommand through the Linux Vulkan geometry backend")
    parser.add_argument("render_binding")
    parser.add_argument("mesh")
    parser.add_argument("packet")
    parser.add_argument("output")
    parser.add_argument("--command-index", type=int, default=0)
    parser.add_argument("--submesh-index", type=int, default=0)
    parser.add_argument("--executable", default="native_vulkan/build/shift_vulkan_render_geometry")
    parser.add_argument("--shader-dir", default="native_vulkan/build/shaders")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args(argv)

    result = run_vulkan_render_command(
        args.render_binding,
        args.mesh,
        args.packet,
        args.output,
        command_index=args.command_index,
        submesh_index=args.submesh_index,
        executable=args.executable,
        shader_dir=args.shader_dir,
        prepare_only=args.prepare_only,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"prepared", "rendered"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
