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
DERIVED_VTABLE = 0x00AD96D8
EMBEDDED_METHOD_SLOT = 0x2A0
EMBEDDED_METHOD = 0x005A8B90
QUEUE_OFFSET = 0x2180
WRAPPER = "FUN_006503d0"

SPANS = {
    "derived_vptr_store_and_tail_jump": (
        0x0047F69C,
        0x0047F6A7,
        "a9cd9b2c902c1da64a66c2df14cb610361bb7122a3f0d7b6d83dba740b014374",
    ),
    "lobby_queue_init_tail": (
        0x005AA456,
        0x005AA470,
        "3b6764e649251bd9e4b6c3b316ac43a0307c66daf4b29451952f9c672587dc6d",
    ),
    "embedded_method_vtable_slot": (
        0x00AD9978,
        0x00AD997C,
        "dfa6af7ba7af45b4b47cae5fd1f057e7b7c5706888f06d7d4400dd1daab4cb0a",
    ),
    "embedded_method_enqueue_call": (
        0x005A8C13,
        0x005A8C23,
        "61bba07942841c730f075e49b7586ca69c547fe105bc0088750bb37ed4da5048",
    ),
}


def digest(path: Path, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def function_body(text: str, name: str) -> str:
    match = re.search(r"(?m)^[^\n]*\b" + re.escape(name) + r"\([^\n]*\)\s*\n\s*\{", text)
    if not match:
        raise ValueError(f"missing {name}")
    start = text.find("{", match.start())
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : index + 1]
    raise ValueError(f"unterminated {name}")


def need(body: str, *tokens: str) -> None:
    missing = [token for token in tokens if token not in body]
    if missing:
        raise ValueError(f"source drift: {missing!r}")


def pe_sections(data: bytes) -> list[tuple[int, int, int]]:
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    table = pe + 24 + optional_size
    result = []
    for index in range(count):
        offset = table + index * 40
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", data, offset + 8
        )
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
    constructor = function_body(text, "FUN_005aa390")
    vptr_tail = function_body(text, "FUN_0047f69c")
    constructor_tail = function_body(text, "FUN_005aa3a9")
    embedded_method = function_body(text, "FUN_005a8b90")
    wrapper = function_body(text, WRAPPER)

    need(constructor, "FUN_005fa3f0(param_1);", "FUN_0047f69c();")
    need(vptr_tail, "*unaff_ESI = &PTR_FUN_00ad96d8;", "FUN_005aa3a9();")
    need(
        constructor_tail,
        '"Plasma_Online"',
        "unaff_ESI + 0x2180",
        '"LobbyClient Output Message Queue"',
    )
    need(embedded_method, "FUN_006503d0((int)this + 0x2180,4);")
    need(wrapper, "FUN_00650350(param_1,param_2,0,0);")

    image = executable.read_bytes()
    spans: dict[str, dict[str, str]] = {}
    for name, (start, end, expected) in SPANS.items():
        raw = va_bytes(image, start, end)
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected:
            raise ValueError(f"machine drift: {name}")
        spans[name] = {
            "start": f"0x{start:08x}",
            "end_exclusive": f"0x{end:08x}",
            "sha256": actual,
        }

    slot_address = DERIVED_VTABLE + EMBEDDED_METHOD_SLOT
    if slot_address != SPANS["embedded_method_vtable_slot"][0]:
        raise ValueError("embedded method slot arithmetic drift")
    slot_target = struct.unpack(
        "<I", va_bytes(image, slot_address, slot_address + 4)
    )[0]
    if slot_target != EMBEDDED_METHOD:
        raise ValueError(
            f"derived LobbyClient vtable slot drift: 0x{slot_target:08x}"
        )

    vptr_store = va_bytes(image, 0x0047F69C, 0x0047F6A2)
    if vptr_store != bytes.fromhex("c706d896ad00"):
        raise ValueError("derived LobbyClient vptr store semantics drift")

    enqueue = va_bytes(image, 0x005A8C13, 0x005A8C23)
    if enqueue[:6] != bytes.fromhex("8d8e80210000"):
        raise ValueError("embedded method queue offset drift")
    if enqueue[6:11] != bytes.fromhex("ba04000000"):
        raise ValueError("embedded method message id drift")

    wrapper_refs = len(re.findall(r"\bFUN_006503d0\s*\(", text))
    if wrapper_refs != 4:
        raise ValueError(f"FUN_006503d0 reference surface drift: {wrapper_refs}")

    return {
        "format": "SHIFT.Process1LobbyClientEmbeddedQueueOwner/1",
        "ready": True,
        "source": {
            "authority": "PC retail 1.02",
            "retail_executable_md5": EXE_MD5,
            "retail_executable_sha256": EXE_SHA256,
            "retail_source_sha256": SOURCE_SHA256,
            "xbox_recomp_required": False,
        },
        "owner": {
            "diagnostic_name": "Plasma_Online",
            "queue_name": "LobbyClient Output Message Queue",
            "queue_offset": "+0x2180",
            "derived_vtable": "0x00ad96d8",
            "embedded_method_vtable_slot": "+0x2a0",
            "embedded_method": "FUN_005a8b90",
        },
        "fun_006503d0": {
            "direct_callsite_count": 3,
            "previously_joined_callers": ["FUN_0057e1c0", "FUN_0057e2a0"],
            "newly_joined_caller": "FUN_005a8b90",
            "newly_joined_queue_expression": "this+0x2180",
            "all_direct_callers_joined_to_lobby_client": True,
            "controller1_queue_alias_ruled_out_for_direct_call_surface": True,
        },
        "adjudication": {
            "fun_006503d0_direct_surface_closed": True,
            "fun_006333f0_controller1_alias_ruled_out": False,
            "fun_006880c0_controller1_alias_ruled_out": False,
            "indirect_or_native_apc_injection_ruled_out": False,
            "render_or_present_phase_lock_proven": False,
        },
        "machine_spans": spans,
        "next_blocker": {
            "process": 1,
            "remaining_generic_queue_pointer_callers": [
                "FUN_006333f0",
                "FUN_006880c0",
            ],
            "description": "classify FUN_006333f0 and FUN_006880c0 by exact queue-object identity; keep indirect/native APC injection and render/presentation phase locking fail-closed",
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
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
