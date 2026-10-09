#!/usr/bin/env python3
"""Bound the plain-name dynamic APC resolution surface in PC retail SHIFT.exe.

This tool deliberately does not claim a universal no-APC theorem. It inventories
resolver imports plus embedded ASCII/UTF-16 API names that could participate in
plain-name dynamic resolution, while leaving hashed/generated names, manual
syscalls and undocumented/native injection fail-closed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

FORMAT = "SHIFT.P1D.Controller1DynamicApcNameSurface/1"
EXE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

RESOLVER_NAMES = (
    "GetProcAddress",
    "LdrGetProcedureAddress",
)

APC_NAMES = (
    "QueueUserAPC",
    "NtQueueApcThread",
    "NtQueueApcThreadEx",
    "ZwQueueApcThread",
    "RtlQueueApcWow64Thread",
    "SetWaitableTimerEx",
)


def load_base_module():
    path = Path(__file__).with_name("analyze_process1_controller1_apc_source_inventory.py")
    spec = importlib.util.spec_from_file_location("process1_apc_source_inventory", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load APC source inventory helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_embedded_names(data: bytes, names: tuple[str, ...]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for name in names:
        encodings: list[str] = []
        ascii_needle = name.encode("ascii") + b"\0"
        utf16_needle = name.encode("utf-16le") + b"\0\0"
        if ascii_needle in data:
            encodings.append("ascii-nul")
        if utf16_needle in data:
            encodings.append("utf16le-nul")
        if encodings:
            found[name] = encodings
    return found


def build_payload(*, imports: dict[str, dict], embedded_names: dict[str, list[str]]) -> dict:
    resolvers_present = sorted(name for name in RESOLVER_NAMES if name in imports)
    apc_imports_present = sorted(name for name in APC_NAMES if name in imports)
    apc_names_present = {
        name: embedded_names[name] for name in APC_NAMES if name in embedded_names
    }

    plain_name_surface_empty = not resolvers_present or not apc_names_present

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "scope": "Controller #1 indirect/native APC timing",
        "dynamic_resolver_imports_present": resolvers_present,
        "direct_apc_injection_imports_present": apc_imports_present,
        "embedded_apc_api_names": apc_names_present,
        "adjudication": {
            "plain_name_dynamic_resolution_surface_empty": plain_name_surface_empty,
            "plain_name_dynamic_resolution_surface_is_universal_no_apc_proof": False,
            "hashed_or_generated_api_name_resolution_ruled_out": False,
            "manual_syscall_or_native_injection_ruled_out": False,
            "indirect_or_native_apc_injection_ruled_out": False,
            "controller1_timing_exhaustive": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "A missing embedded API name does not rule out runtime-generated, encrypted or hashed resolution.",
            "A missing resolver import does not rule out manual export walking or native/syscall injection.",
            "API-name presence does not prove a call path reaches Controller #1.",
            "This surface is narrower than the existing imported-completion inventory and cannot by itself close APC timing.",
        ],
        "next_step": (
            "If the plain-name surface is non-empty, trace exact resolver/name callsites to thread identity. "
            "Regardless of the result, separately bound manual export walking, native APC/syscall paths and "
            "any indirect function-pointer injection before declaring Controller #1 timing exhaustive."
        ),
    }


def analyze(executable: Path) -> dict:
    helper = load_base_module()
    if helper.digest(executable) != EXE_SHA256:
        raise ValueError("SHIFT.exe hash mismatch")
    data = executable.read_bytes()
    imports = helper.parse_imports(data)
    embedded = find_embedded_names(data, tuple(sorted(set(RESOLVER_NAMES + APC_NAMES))))
    payload = build_payload(imports=imports, embedded_names=embedded)
    payload["authority"] = {
        "platform": "PC retail 1.02",
        "retail_executable_sha256": EXE_SHA256,
        "machine_import_table_and_bytes_adjudicate": True,
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.exe)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
