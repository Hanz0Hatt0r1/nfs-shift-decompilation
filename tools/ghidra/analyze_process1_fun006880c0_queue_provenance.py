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
    "caller_queue_load_and_call": (0x0066BAE7, 0x0066BAF5, "be717492d4a5f4c8c8d82dcb67332d6596c23e8523851e422b0fbbfe39aee57c"),
    "initializer_param4_store": (0x0066BB59, 0x0066BB6A, "110a99db72078d0d9860f9d5899543e1b7ae0daa96f88ef70e11df383dcf72b5"),
    "thin_wrapper": (0x006880C0, 0x006880DB, "62843e0d0bd7c20e5fcf3cbc1b3f7a47a944e36c27e4334cdc724779bef95255"),
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
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from("<IIII", data, offset + 8)
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
    wrapper = function_body(text, "FUN_006880c0")
    caller = function_body(text, "FUN_0066bab0")
    initializer = function_body(text, "FUN_0066bb50")
    c980 = function_body(text, "FUN_0066c980")
    cc00 = function_body(text, "FUN_0066cc00")
    fff90 = function_body(text, "FUN_0065ff90")
    ff970 = function_body(text, "FUN_0065f970")
    ffa60 = function_body(text, "FUN_0065fa60")
    api_a = function_body(text, "FUN_00634ed0")
    api_b = function_body(text, "FUN_00634f00")
    api_c = function_body(text, "FUN_00634f50")

    need(wrapper, "FUN_00650350(param_1,param_2,param_3,local_8);")
    need(caller, "FUN_006880c0(*(int *)(unaff_ESI + 8),unaff_EDI,*(undefined4 *)(unaff_EBP + 8));")
    need(initializer, "param_1[2] = param_4;")
    need(c980, "FUN_0066bb50((int *)(param_1 + 8),param_2,param_3,param_4,param_5,0,0);")
    need(cc00, "FUN_0066bb50((int *)(param_1 + 8),param_2,param_3,param_4,param_5,1,param_6);")
    need(fff90, "FUN_0066c980(iVar1,local_10,param_1,param_3,param_4,pLVar6);")
    need(ff970, "FUN_0066cc00(param_1 + 0x200,param_2,param_1,param_3,param_4,0);")
    need(ffa60, "FUN_0066cc00(param_1 + 0x200,param_2,param_1,param_3,param_4,1);")
    need(api_a, "FUN_0065ebb0(*param_1,param_2,param_3);")
    need(api_b, "FUN_0065ec00(*param_1,param_2,param_3);")
    need(api_c, "FUN_0065ec50(*param_1,param_2,param_3);")

    if len(re.findall(r"\bFUN_006880c0\s*\(", text)) != 2:
        raise ValueError("FUN_006880c0 reference surface drift")
    if len(re.findall(r"\bFUN_0066bb50\s*\(", text)) != 3:
        raise ValueError("FUN_0066bb50 reference surface drift")

    image = executable.read_bytes()
    spans = {}
    for name, (start, end, expected) in SPANS.items():
        actual = hashlib.sha256(va_bytes(image, start, end)).hexdigest()
        if actual != expected:
            raise ValueError(f"machine drift: {name}")
        spans[name] = {"start": f"0x{start:08x}", "end_exclusive": f"0x{end:08x}", "sha256": actual}

    return {
        "format": "SHIFT.Process1Fun006880c0QueueProvenance/1",
        "ready": True,
        "source": {
            "authority": "PC retail 1.02",
            "retail_executable_md5": EXE_MD5,
            "retail_executable_sha256": EXE_SHA256,
            "retail_source_sha256": SOURCE_SHA256,
            "xbox_recomp_required": False,
        },
        "dataflow": {
            "wrapper": "FUN_006880c0",
            "single_source_visible_caller": "FUN_0066bab0",
            "queue_pointer_expression": "embedded_state+0x8",
            "initializer": "FUN_0066bb50",
            "initializer_assignment": "embedded_state+0x8 = param_4",
            "initializer_wrappers": ["FUN_0066c980", "FUN_0066cc00"],
            "producer_chain": ["FUN_0065ff90", "FUN_0065f970", "FUN_0065fa60"],
            "api_wrappers": ["FUN_00634ed0", "FUN_00634f00", "FUN_00634f50"],
            "fixed_global_owner_proven": False,
            "caller_supplied_operation_object": True,
        },
        "adjudication": {
            "fun_006880c0_fixed_queue_owner_claim_rejected": True,
            "fun_006880c0_controller1_alias_ruled_out": False,
            "fun_006333f0_controller1_alias_ruled_out": False,
            "indirect_or_native_apc_injection_ruled_out": False,
            "render_or_present_phase_lock_proven": False,
        },
        "machine_spans": spans,
        "next_blocker": {
            "process": 1,
            "description": "classify the operation-object producer identities feeding FUN_00634ed0/FUN_00634f00/FUN_00634f50, plus FUN_006333f0; do not treat FUN_006880c0 as a fixed queue owner",
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
