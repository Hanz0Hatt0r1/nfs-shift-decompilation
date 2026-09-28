"""Serialize RenderCommand D3D9 float constants into a Vulkan descriptor packet."""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.VulkanConstantPacket/1"
MAGIC = b"SVCP"
VERSION = 1
MAX_REGISTERS = 256
REGISTER_BYTES = 16
HEADER = struct.Struct("<4sIIIIII")


def build_vulkan_constant_packet(
    render_command: Mapping[str, Any] | str | Path,
    output: str | Path,
) -> dict[str, Any]:
    command = (
        json.loads(Path(render_command).read_text(encoding="utf-8"))
        if isinstance(render_command, (str, Path))
        else dict(render_command)
    )
    if command.get("format") != "SHIFT.RenderCommand/1":
        raise ValueError("input is not SHIFT.RenderCommand/1")

    banks = {
        "vertex": [[0.0, 0.0, 0.0, 0.0] for _ in range(MAX_REGISTERS)],
        "pixel": [[0.0, 0.0, 0.0, 0.0] for _ in range(MAX_REGISTERS)],
    }
    populated: dict[str, set[int]] = {"vertex": set(), "pixel": set()}
    blockers: list[str] = []

    for submesh in command.get("submeshes", []) or []:
        payload = submesh.get("constant_payload") or {}
        command_stage_by_register: dict[int, set[str]] = {}
        for command_row in submesh.get("constant_commands", []) or []:
            try:
                register = int(command_row.get("register_index"))
            except (TypeError, ValueError):
                continue
            stage = str(command_row.get("stage") or "").lower()
            command_stage_by_register.setdefault(register, set()).add(stage)

        for row in payload.get("registers", []) or []:
            try:
                register = int(row.get("register_index"))
                values = [float(v) for v in row.get("values")]
            except (TypeError, ValueError):
                blockers.append("constant-packet:invalid-register")
                continue
            stages = {
                stage for stage in command_stage_by_register.get(register, set())
                if stage in banks
            }
            invalid_stages = command_stage_by_register.get(register, set()) - banks.keys()
            if invalid_stages:
                blockers.append(
                    f"constant-packet:unsupported-stage:{sorted(invalid_stages)[0]}"
                )
                continue
            if len(stages) != 1:
                blockers.append(
                    f"constant-packet:stage-ambiguous:{register}"
                    if stages
                    else f"constant-packet:stage-missing:{register}"
                )
                continue
            stage = next(iter(stages))
            if register < 0 or register >= MAX_REGISTERS or len(values) != 4:
                blockers.append(f"constant-packet:invalid-register:{stage}:{register}")
                continue
            banks[stage][register] = values
            populated[stage].add(register)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blob = bytearray()
    blob.extend(HEADER.pack(
        MAGIC, VERSION, MAX_REGISTERS, REGISTER_BYTES,
        len(populated["vertex"]), len(populated["pixel"]), 0,
    ))
    for stage in ("vertex", "pixel"):
        for values in banks[stage]:
            blob.extend(struct.pack("<4f", *values))
    output_path.write_bytes(blob)

    return {
        "format": FORMAT,
        "version": VERSION,
        "output": str(output_path),
        "ready": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "descriptor_set": 0,
        "banks": {
            "vertex": {"binding": 14, "register_count": MAX_REGISTERS, "populated": sorted(populated["vertex"])},
            "pixel": {"binding": 15, "register_count": MAX_REGISTERS, "populated": sorted(populated["pixel"])},
        },
        "byte_size": len(blob),
        "header_bytes": HEADER.size,
        "bank_bytes": MAX_REGISTERS * REGISTER_BYTES,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Build SHIFT.VulkanConstantPacket/1")
    parser.add_argument("render_command")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    report = build_vulkan_constant_packet(args.render_command, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
