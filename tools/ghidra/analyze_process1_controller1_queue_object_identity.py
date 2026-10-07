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
EXPECTED_DIRECT_CALLERS = [
    "FUN_0057e5b0",
    "FUN_0057e820",
    "FUN_006333f0",
    "FUN_00649b10",
    "FUN_006503d0",
    "FUN_00655220",
    "FUN_00662ee0",
    "FUN_006880c0",
]
EXPLICIT_CONTROLLER_QUEUE_CALLERS = ["FUN_00649b10", "FUN_00662ee0"]
SPANS = {
    "thread_entry_self_enqueue": (0x00649C30, 0x00649C42),
    "controller_enqueue_wrapper": (0x00662EE0, 0x00662F16),
    "generic_queue_enqueue": (0x00650350, 0x00650390),
    "teardown_direct_controller_enqueue": (0x00649A20, 0x00649A3E),
}


def digest(path: Path, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_index(text: str):
    lines = text.splitlines()
    call_pattern = re.compile(r"\b(FUN_[0-9A-Za-z_]+)\s*\(")
    definitions: list[tuple[int, str]] = []
    for index, line in enumerate(lines[:-1]):
        stripped = line.strip()
        if not stripped.endswith(")") or ";" in stripped or "=" in stripped:
            continue
        next_line = index + 1
        while next_line < len(lines) and not lines[next_line].strip():
            next_line += 1
        if next_line < len(lines) and lines[next_line].strip() == "{":
            match = call_pattern.search(stripped)
            if match:
                definitions.append((index, match.group(1)))
    positions = {name: i for i, (_, name) in enumerate(definitions)}

    def body(name: str) -> str:
        pos = positions[name]
        start = definitions[pos][0] + 1
        end = definitions[pos + 1][0] if pos + 1 < len(definitions) else len(lines)
        return "\n".join(lines[start:end])

    return positions, body


def pe_sections(data: bytes) -> list[tuple[int, int, int]]:
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    table = pe + 24 + optional_size
    result = []
    for index in range(count):
        off = table + index * 40
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from("<IIII", data, off + 8)
        result.append((virtual_address, max(virtual_size, raw_size), raw_offset))
    return result


def va_bytes(data: bytes, start: int, end: int) -> bytes:
    rva = start - IMAGE_BASE
    size = end - start
    for section_rva, section_size, raw_offset in pe_sections(data):
        if section_rva <= rva and rva + size <= section_rva + section_size:
            file_offset = raw_offset + rva - section_rva
            return data[file_offset : file_offset + size]
    raise ValueError(f"VA outside mapped PE sections: 0x{start:08x}")


def build_payload(source: Path, executable: Path) -> dict[str, object]:
    if digest(source) != SOURCE_SHA256:
        raise ValueError("SHIFT.exe.c hash mismatch")
    if digest(executable, "md5") != EXE_MD5 or digest(executable) != EXE_SHA256:
        raise ValueError("SHIFT.exe hash mismatch")

    text = source.read_text(encoding="utf-8", errors="replace")
    positions, body = build_index(text)
    callers = sorted(
        name for name in positions
        if name != "FUN_00650350" and "FUN_00650350(" in body(name)
    )
    if callers != EXPECTED_DIRECT_CALLERS:
        raise ValueError(f"generic queue direct caller surface drift: {callers!r}")

    explicit = sorted(name for name in callers if "+ 0x5c" in body(name))
    if explicit != EXPLICIT_CONTROLLER_QUEUE_CALLERS:
        raise ValueError(f"explicit controller queue identity surface drift: {explicit!r}")
    if "FUN_00650350(*(int *)(pcVar1 + 0x5c)" not in body("FUN_00649b10"):
        raise ValueError("thread-entry Controller queue self-enqueue drift")
    if "iVar1 = *(int *)(param_1 + 0x5c);" not in body("FUN_00662ee0"):
        raise ValueError("Controller enqueue wrapper queue identity drift")
    if len(re.findall(r"\bFUN_00662ee0\s*\(", text)) != 2:
        raise ValueError("Controller enqueue direct caller count drift")
    if "FUN_00662ee0(iVar2,0);" not in body("FUN_006499e8"):
        raise ValueError("teardown Controller enqueue callsite drift")

    image = executable.read_bytes()
    spans = {}
    for name, (start, end) in SPANS.items():
        raw = va_bytes(image, start, end)
        spans[name] = {
            "start": f"0x{start:08x}",
            "end_exclusive": f"0x{end:08x}",
            "sha256": hashlib.sha256(raw).hexdigest(),
        }

    return {
        "format": "SHIFT.Process1Controller1QueueObjectIdentity/1",
        "ready": True,
        "source": {
            "authority": "PC retail 1.02",
            "retail_executable_md5": EXE_MD5,
            "retail_executable_sha256": EXE_SHA256,
            "retail_source_sha256": SOURCE_SHA256,
        },
        "generic_enqueue": {
            "function": "FUN_00650350",
            "direct_caller_count": len(callers),
            "direct_callers": callers,
        },
        "explicit_controller_queue_identity": {
            "queue_field": "+0x5c",
            "callers": explicit,
            "thread_entry_self_seed": "FUN_00649b10",
            "external_wrapper": "FUN_00662ee0",
            "external_wrapper_only_direct_caller": "FUN_006499e8",
            "external_wrapper_only_direct_context": "thread teardown/shutdown",
        },
        "generic_alias_frontier": {
            "callers_without_explicit_controller_queue_identity": [
                name for name in callers if name not in explicit
            ],
            "generic_pointer_alias_to_controller1_ruled_out": False,
        },
        "adjudication": {
            "source_visible_explicit_controller_queue_producers_classified": True,
            "thread_entry_self_seed_is_external_wake_source": False,
            "direct_non_teardown_external_controller_enqueue_producer_proven": False,
            "render_or_present_direct_controller_queue_producer_proven": False,
            "generic_queue_pointer_aliases_ruled_out": False,
        },
        "machine_spans": spans,
        "next_blocker": {
            "process": 1,
            "description": "resolve whether any of the six generic queue-pointer callers can alias Controller #1 queue+0x5c, prioritizing render/presentation reachable producers",
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
