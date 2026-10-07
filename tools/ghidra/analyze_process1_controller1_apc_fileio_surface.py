from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
EXE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
EXE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
IMAGE_BASE = 0x00400000

SPANS = {
    "async_file_base_vtable_store": (0x0065226F, 0x00652275),
    "controller_ctor_base_and_vtable_store": (0x006624A5, 0x006624B5),
    "read_completion_routine": (0x006553E0, 0x00655403),
    "write_completion_routine": (0x00655410, 0x00655433),
    "shutdown_direct_controller_enqueue_call": (0x00649A20, 0x00649A3E),
    "controller_enqueue_wrapper": (0x00662EE0, 0x00662F16),
    "controller_vtable_prefix": (0x00AF0568, 0x00AF0594),
    "async_file_vtable_prefix": (0x00AEF430, 0x00AEF470),
}


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
    optional_header_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    section_table = pe_offset + 24 + optional_header_size
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
            file_offset = raw_offset + (rva - section_rva)
            return data[file_offset : file_offset + size]
    raise ValueError(f"VA range is outside mapped PE sections: 0x{start:08x}")


def extract_function(text: str, name: str) -> str:
    match = re.search(
        r"(?m)^[^\n]*\b" + re.escape(name) + r"\([^\n]*\)\s*\n\s*\{",
        text,
    )
    if match is None:
        raise ValueError(f"missing function {name}")
    brace = text.find("{", match.start())
    depth = 0
    for index in range(brace, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : index + 1]
    raise ValueError(f"unterminated function {name}")


def line_number(text: str, needle: str) -> int:
    offset = text.find(needle)
    if offset < 0:
        raise ValueError(f"missing source token: {needle}")
    return text.count("\n", 0, offset) + 1


def build_payload(source: Path, executable: Path) -> dict[str, object]:
    if digest(source) != SOURCE_SHA256:
        raise ValueError("SHIFT.exe.c hash mismatch")
    if digest(executable, "md5") != EXE_MD5 or digest(executable) != EXE_SHA256:
        raise ValueError("SHIFT.exe hash mismatch")

    text = source.read_text(encoding="utf-8", errors="replace")
    worker = extract_function(text, "FUN_00662880")
    controller_ctor = extract_function(text, "FUN_006624a0")
    read_completion = extract_function(text, "lpCompletionRoutine_006553e0")
    write_completion = extract_function(text, "lpCompletionRoutine_00655410")
    async_file_base = extract_function(text, "FUN_00652260")
    shutdown = extract_function(text, "FUN_006499e8")
    enqueue = extract_function(text, "FUN_00662ee0")

    forbidden_worker_tokens = (
        "ReadFileEx",
        "WriteFileEx",
        "lpCompletionRoutine_006553e0",
        "lpCompletionRoutine_00655410",
        "FUN_006557a0",
        "FUN_00655900",
        "FUN_00655ab0",
        "FUN_00655c80",
    )
    if any(token in worker for token in forbidden_worker_tokens):
        raise ValueError("Controller #1 worker unexpectedly reaches direct async-file token")
    if "FUN_006551b0(param_1);" not in controller_ctor or "&PTR_FUN_00af0568" not in controller_ctor:
        raise ValueError("Controller #1 constructor identity drift")
    if "&PTR_FUN_00aef430" not in async_file_base:
        raise ValueError("async-file base vtable identity drift")
    if "*(void **)(param_3 + 0x10)" not in read_completion or "FUN_00652710" not in read_completion:
        raise ValueError("ReadFileEx completion owner/continuation drift")
    if "*(void **)(param_3 + 0x10)" not in write_completion or "FUN_006529f0" not in write_completion:
        raise ValueError("WriteFileEx completion owner/continuation drift")
    if "FUN_00662ee0(iVar2,0);" not in shutdown:
        raise ValueError("known direct Controller #1 enqueue callsite drift")
    if "FUN_00650350" not in enqueue:
        raise ValueError("Controller #1 enqueue wrapper no longer joins generic queue")
    if len(re.findall(r"\bFUN_00662ee0\s*\(", text)) != 2:
        raise ValueError("direct Controller #1 enqueue callsite count drift")

    image = executable.read_bytes()
    machine_spans: dict[str, dict[str, str]] = {}
    for key, (start, end_exclusive) in SPANS.items():
        raw = va_bytes(image, start, end_exclusive)
        machine_spans[key] = {
            "start": f"0x{start:08x}",
            "end_exclusive": f"0x{end_exclusive:08x}",
            "sha256": hashlib.sha256(raw).hexdigest(),
        }

    def pointer_cells(start: int, end_exclusive: int) -> list[str]:
        raw = va_bytes(image, start, end_exclusive)
        return [
            f"0x{value:08x}"
            for value in struct.unpack("<" + "I" * (len(raw) // 4), raw)
        ]

    return {
        "format": "SHIFT.Process1Controller1ApcFileIoSurface/1",
        "ready": True,
        "source": {
            "authority": "PC retail 1.02",
            "retail_executable_md5": EXE_MD5,
            "retail_executable_sha256": EXE_SHA256,
            "retail_source_sha256": SOURCE_SHA256,
            "xbox_recomp_required": False,
        },
        "controller1": {
            "constructor": "FUN_006624a0",
            "base_constructor": "FUN_006551b0",
            "vtable": "0x00af0568",
            "worker": "FUN_00662880",
            "worker_direct_async_file_tokens_present": False,
            "source_lines": {
                "constructor": line_number(text, "undefined4 * __fastcall FUN_006624a0"),
                "worker": line_number(text, "undefined4 __cdecl FUN_00662880"),
                "enqueue_wrapper": line_number(text, "void __fastcall FUN_00662ee0"),
            },
            "vtable_prefix": pointer_cells(*SPANS["controller_vtable_prefix"]),
        },
        "async_file_apc": {
            "base_constructor": "FUN_00652260",
            "base_vtable": "0x00aef430",
            "read_completion": "lpCompletionRoutine_006553e0",
            "write_completion": "lpCompletionRoutine_00655410",
            "read_continuation": "FUN_00652710",
            "write_continuation": "FUN_006529f0",
            "completion_owner_expression": "*(void **)(OVERLAPPED + 0x10)",
            "readfileex_call_count": text.count("ReadFileEx("),
            "writefileex_call_count": text.count("WriteFileEx("),
            "source_lines": {
                "base_constructor": line_number(text, "undefined4 * __fastcall FUN_00652260"),
                "read_completion": line_number(text, "void lpCompletionRoutine_006553e0"),
                "write_completion": line_number(text, "void lpCompletionRoutine_00655410"),
            },
            "vtable_prefix": pointer_cells(*SPANS["async_file_vtable_prefix"]),
        },
        "queue_surface": {
            "controller_enqueue": "FUN_00662ee0",
            "queue_enqueue": "FUN_00650350",
            "direct_controller_enqueue_callsite_count": 1,
            "only_direct_controller_enqueue_caller": "FUN_006499e8",
            "only_direct_call_context": "thread shutdown/teardown enumeration, followed by 100 ms wait",
            "render_or_present_direct_controller_enqueue_caller_proven": False,
        },
        "adjudication": {
            "controller1_and_async_file_object_families_distinct": True,
            "controller1_worker_directly_initiates_readfileex_proven": False,
            "controller1_worker_directly_initiates_writefileex_proven": False,
            "file_completion_directly_targets_controller1_proven": False,
            "file_completion_returns_to_overlapped_owner_object_proven": True,
            "direct_render_or_present_to_controller_enqueue_proven": False,
            "indirect_controller1_apc_initiator_alias_ruled_out": False,
            "generic_queue_alias_from_render_ruled_out": False,
        },
        "machine_spans": machine_spans,
        "next_blocker": {
            "process": 1,
            "description": (
                "trace indirect call/alias ownership from Controller #1 manager updates into "
                "the generic async-file initiators and search render/presentation producers for "
                "aliases of Controller #1 queue+0x5c; direct file-APC and direct enqueue paths "
                "are now negative"
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
