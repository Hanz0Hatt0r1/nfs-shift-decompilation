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
LOBBY_VTABLE = 0x00AE3B00
LOBBY_QUEUE_VTABLE_SLOT = 0x88
LOBBY_QUEUE_ACCESSOR = 0x005AA4E0
LOBBY_QUEUE_OFFSET = 0x2180
SPANS = {
    "lobby_constructor": (0x005AA390, 0x005AA477, "ec57d35157c4875474707f21ed68add1936444c76a98f688d2cef0b6ebf5b599"),
    "lobby_queue_init_tail": (0x005AA456, 0x005AA470, "3b6764e649251bd9e4b6c3b316ac43a0307c66daf4b29451952f9c672587dc6d"),
    "lobby_queue_accessor": (0x005AA4E0, 0x005AA4E7, "5dd1f86c0c4905503bb9356b2237508931587870c27385f4755724c0ab40c134"),
    "lobby_vtable_queue_slot": (0x00AE3B88, 0x00AE3B8C, "c77c37cf7f5c224258a25b2c8754827abc9e34cdd433b7537d3b94de54d3fbb5"),
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
    singleton = function_body(text, "FUN_0057d9b0")
    base_ctor = function_body(text, "FUN_005fa3f0")
    ctor = function_body(text, "FUN_005aa390")
    ctor_tail = function_body(text, "FUN_005aa3a9")
    destructor = function_body(text, "FUN_005fa4a0")
    send_a = function_body(text, "FUN_0057e5b0")
    send_b = function_body(text, "FUN_0057e820")
    wrapper = function_body(text, "FUN_006503d0")
    wrapper_a = function_body(text, "FUN_0057e1c0")
    wrapper_b = function_body(text, "FUN_0057e2a0")
    wrapper_c = function_body(text, "FUN_005a8b90")

    need(singleton, "FUN_005aa390(&DAT_00be4800);", "return &DAT_00be4800;")
    need(base_ctor, "*param_1 = &PTR_FUN_00ae3b00;")
    need(ctor, "FUN_005fa3f0(param_1);", "FUN_0047f69c();")
    need(ctor_tail, '"Plasma_Online"', 'unaff_ESI + 0x2180', '"LobbyClient Output Message Queue"')
    need(destructor, "FUN_00650310((int)(param_1 + 0x2180));")
    need(send_a, "FUN_005aa390(&DAT_00be4800);", "(**(code **)(DAT_00be4800 + 0x88))()", "FUN_00650350(iVar1,uVar2,uVar3,iStack_4);")
    need(send_b, "FUN_005aa390(&DAT_00be4800);", "(**(code **)(DAT_00be4800 + 0x88))()", "FUN_00650350(iVar1,0xb,param_1,iStack_4);")
    need(wrapper, "FUN_00650350(param_1,param_2,0,0);")
    need(wrapper_a, "(**(code **)(DAT_00be4800 + 0x88))()", "FUN_006503d0(iVar1,10);")
    need(wrapper_b, "FUN_0057d9b0();", "(**(code **)(*piVar1 + 0x88))()", "FUN_006503d0(iVar2,0x4b);")
    need(wrapper_c, "FUN_006503d0((int)this + 0x2180,4);")

    wrapper_refs = len(re.findall(r"\bFUN_006503d0\s*\(", text))
    if wrapper_refs != 4:
        raise ValueError(f"FUN_006503d0 reference surface drift: {wrapper_refs}")

    image = executable.read_bytes()
    spans = {}
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

    vtable_entry = struct.unpack("<I", va_bytes(image, LOBBY_VTABLE + LOBBY_QUEUE_VTABLE_SLOT, LOBBY_VTABLE + LOBBY_QUEUE_VTABLE_SLOT + 4))[0]
    if vtable_entry != LOBBY_QUEUE_ACCESSOR:
        raise ValueError(f"LobbyClient queue accessor vtable slot drift: 0x{vtable_entry:08x}")
    accessor = va_bytes(image, LOBBY_QUEUE_ACCESSOR, LOBBY_QUEUE_ACCESSOR + 7)
    if accessor != bytes.fromhex("8d8180210000c3"):
        raise ValueError("LobbyClient queue accessor machine semantics drift")

    return {
        "format": "SHIFT.Process1LobbyClientQueueAliases/1",
        "ready": True,
        "source": {
            "authority": "PC retail 1.02",
            "retail_executable_md5": EXE_MD5,
            "retail_executable_sha256": EXE_SHA256,
            "retail_source_sha256": SOURCE_SHA256,
            "xbox_recomp_required": False,
        },
        "lobby_client": {
            "singleton_storage": "DAT_00be4800",
            "owner_name": "Plasma_Online",
            "queue_name": "LobbyClient Output Message Queue",
            "queue_offset": "+0x2180",
            "base_vtable": "0x00ae3b00",
            "queue_accessor_vtable_slot": "+0x88",
            "queue_accessor": "0x005aa4e0",
            "queue_accessor_machine_semantics": "return this + 0x2180",
        },
        "resolved_generic_enqueue_callers": {
            "FUN_0057e5b0": {
                "queue_owner": "Plasma_Online/LobbyClient",
                "controller1_alias_ruled_out_by_object_identity": True,
            },
            "FUN_0057e820": {
                "queue_owner": "Plasma_Online/LobbyClient",
                "controller1_alias_ruled_out_by_object_identity": True,
            },
        },
        "fun_006503d0_direct_callers": {
            "direct_callsite_count": 3,
            "lobby_client_global_queue_calls": ["FUN_0057e1c0", "FUN_0057e2a0"],
            "embedded_plus_0x2180_call": "FUN_005a8b90",
            "embedded_plus_0x2180_exact_owner_promoted": False,
            "wrapper_fully_ruled_out_as_controller1_alias": False,
        },
        "adjudication": {
            "fun_0057e5b0_controller1_queue_alias_ruled_out": True,
            "fun_0057e820_controller1_queue_alias_ruled_out": True,
            "fun_006503d0_two_of_three_direct_calls_joined_to_lobby_client": True,
            "fun_006503d0_all_possible_controller1_aliases_ruled_out": False,
            "indirect_or_native_apc_injection_ruled_out": False,
            "render_or_present_phase_lock_proven": False,
        },
        "machine_spans": spans,
        "next_blocker": {
            "process": 1,
            "remaining_generic_queue_pointer_callers": ["FUN_006333f0", "FUN_006503d0", "FUN_006880c0"],
            "description": "classify FUN_006333f0, the remaining FUN_006503d0 +0x2180 owner, and FUN_006880c0 by exact queue-object identity; keep indirect/native APC injection and render/presentation phase locking fail-closed",
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
