from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from collections import deque
from pathlib import Path

SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
EXE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
EXE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
IMAGE_BASE = 0x00400000

SPANS = {
    "controller1_three_manager_attach_block": (0x00D3604A, 0x00D360DA),
    "physics_manager_vtable_prefix": (0x00B04524, 0x00B04544),
    "camera_manager_vtable_prefix": (0x00B157D8, 0x00B157F8),
    "camera_script_manager_vtable_prefix": (0x00AC5670, 0x00AC5690),
    "camera_manager_update_thunk": (0x0080C990, 0x0080C995),
}
KNOWN_ASYNC_FILE_TARGETS = {
    "FUN_006557a0",
    "FUN_00655900",
    "FUN_00655ab0",
    "FUN_00655c80",
    "lpCompletionRoutine_006553e0",
    "lpCompletionRoutine_00655410",
}
ASYNC_APIS = ("ReadFileEx(", "WriteFileEx(")


def digest(path: Path, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def pe_sections(data: bytes) -> list[tuple[str, int, int, int]]:
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise ValueError("input is not a PE image")
    section_count = struct.unpack_from("<H", data, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    section_table = pe_offset + 24 + optional_size
    result: list[tuple[str, int, int, int]] = []
    for index in range(section_count):
        offset = section_table + index * 40
        name = data[offset : offset + 8].rstrip(b"\0").decode("ascii", "replace")
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", data, offset + 8
        )
        result.append((name, virtual_address, max(virtual_size, raw_size), raw_offset))
    return result


def va_bytes(data: bytes, start: int, end_exclusive: int) -> bytes:
    rva = start - IMAGE_BASE
    size = end_exclusive - start
    for _, section_rva, section_size, raw_offset in pe_sections(data):
        if (
            section_rva <= rva < section_rva + section_size
            and rva + size <= section_rva + section_size
        ):
            file_offset = raw_offset + rva - section_rva
            return data[file_offset : file_offset + size]
    raise ValueError(f"VA range outside mapped PE sections: 0x{start:08x}")


def build_source_index(text: str):
    lines = text.splitlines()
    call_pattern = re.compile(
        r"\b((?:FUN_|thunk_FUN_|lpCompletionRoutine_)[0-9A-Za-z_]+)\s*\("
    )
    definitions: list[tuple[int, str]] = []
    for index, line in enumerate(lines[:-1]):
        stripped = line.strip()
        if not stripped.endswith(")") or ";" in stripped or "=" in stripped:
            continue
        next_line = index + 1
        while next_line < len(lines) and not lines[next_line].strip():
            next_line += 1
        if next_line >= len(lines) or lines[next_line].strip() != "{":
            continue
        match = call_pattern.search(stripped)
        if match is not None:
            definitions.append((index, match.group(1)))

    function_index = {name: position for position, (_, name) in enumerate(definitions)}

    def body(name: str) -> str:
        position = function_index[name]
        start = definitions[position][0] + 1
        end = definitions[position + 1][0] if position + 1 < len(definitions) else len(lines)
        return "\n".join(lines[start:end])

    def calls(name: str) -> set[str]:
        return {
            match.group(1)
            for match in call_pattern.finditer(body(name))
            if match.group(1) != name
        }

    return function_index, body, calls


def direct_named_closure(root: str, function_index, body, calls) -> dict[str, object]:
    seen = {root}
    queue = deque([root])
    target_hits: set[str] = set()
    api_body_hits: list[str] = []
    while queue:
        function = queue.popleft()
        function_body = body(function)
        if any(api in function_body for api in ASYNC_APIS):
            api_body_hits.append(function)
        for callee in calls(function):
            if callee in KNOWN_ASYNC_FILE_TARGETS:
                target_hits.add(callee)
            if callee in function_index and callee not in seen:
                seen.add(callee)
                queue.append(callee)
    return {
        "root": root,
        "reachable_named_function_count": len(seen),
        "known_async_file_target_hits": sorted(target_hits),
        "read_write_file_ex_body_hits": sorted(api_body_hits),
    }


def build_payload(source: Path, executable: Path) -> dict[str, object]:
    if digest(source) != SOURCE_SHA256:
        raise ValueError("SHIFT.exe.c hash mismatch")
    if digest(executable, "md5") != EXE_MD5 or digest(executable) != EXE_SHA256:
        raise ValueError("SHIFT.exe hash mismatch")

    text = source.read_text(encoding="utf-8", errors="replace")
    image = executable.read_bytes()

    for token in ("FUN_0070fe90()", "FUN_0080bfb0()", "thunk_FUN_0048993b()"):
        if token not in text:
            raise ValueError(f"missing Controller #1 startup manager: {token}")
    for manager_name in ("Physics Manager", "Camera Manager", "CameraScriptManager"):
        if f'"{manager_name}"' not in text:
            raise ValueError(f"missing registered manager name: {manager_name}")

    function_index, body, calls = build_source_index(text)
    roots = ("FUN_00711b50", "FUN_0080c920", "FUN_0050b5d0")
    closures = {
        root: direct_named_closure(root, function_index, body, calls) for root in roots
    }
    expected_counts = {
        "FUN_00711b50": 2896,
        "FUN_0080c920": 428,
        "FUN_0050b5d0": 452,
    }
    for root, result in closures.items():
        if result["reachable_named_function_count"] != expected_counts[root]:
            raise ValueError(f"direct call closure drift for {root}")
        if result["known_async_file_target_hits"] or result["read_write_file_ex_body_hits"]:
            raise ValueError(f"direct APC/file-I/O reachability appeared for {root}")

    machine_spans: dict[str, dict[str, str]] = {}
    for name, (start, end_exclusive) in SPANS.items():
        raw = va_bytes(image, start, end_exclusive)
        machine_spans[name] = {
            "start": f"0x{start:08x}",
            "end_exclusive": f"0x{end_exclusive:08x}",
            "sha256": hashlib.sha256(raw).hexdigest(),
        }

    def u32(va: int) -> int:
        return struct.unpack("<I", va_bytes(image, va, va + 4))[0]

    return {
        "format": "SHIFT.Process1Controller1ManagerApcReachability/1",
        "ready": True,
        "source": {
            "authority": "PC retail 1.02",
            "retail_executable_md5": EXE_MD5,
            "retail_executable_sha256": EXE_SHA256,
            "retail_source_sha256": SOURCE_SHA256,
            "xbox_recomp_required": False,
        },
        "controller1_manager_attachments": {
            "startup_function": "thunk_FUN_00d36000",
            "attach_function": "FUN_006485b0",
            "direct_attached_manager_count": 3,
            "managers": ["Physics Manager", "Camera Manager", "CameraScriptManager"],
            "controller2_managers_excluded": ["FUN_008695a0()", "FUN_006984f0()"],
        },
        "default_update_slots": {
            "Physics Manager": {
                "vtable": "0x00b04524",
                "slot_0x18_target": f"0x{u32(0x00B0453C):08x}",
                "normalized_source_root": "FUN_00711b50",
            },
            "Camera Manager": {
                "vtable": "0x00b157d8",
                "slot_0x18_target": f"0x{u32(0x00B157F0):08x}",
                "normalized_source_root": "FUN_0080c920",
                "slot_target_is_jump_thunk": True,
            },
            "CameraScriptManager": {
                "vtable": "0x00ac5670",
                "slot_0x18_target": f"0x{u32(0x00AC5688):08x}",
                "normalized_source_root": "FUN_0050b5d0",
            },
        },
        "direct_named_call_closure": closures,
        "adjudication": {
            "all_three_controller1_default_manager_updates_checked": True,
            "direct_named_path_to_known_async_file_initiators_proven": False,
            "direct_named_path_to_readfileex_or_writefileex_proven": False,
            "indirect_virtual_or_function_pointer_path_ruled_out": False,
            "render_frame_equivalence_proven": False,
        },
        "machine_spans": machine_spans,
        "next_blocker": {
            "process": 1,
            "description": (
                "resolve indirect/virtual callsites in the three Controller #1 manager update "
                "closures and prove whether any can alias the async-file worker/file objects; "
                "separately trace generic queue producers by queue-object identity rather than API name"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--exe", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build_payload(args.source, args.exe)
    rendered = json.dumps(payload, indent=2) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
