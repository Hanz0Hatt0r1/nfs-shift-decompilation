from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

EXE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
EXE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED_APC_IMPORTS = {
    "SetWaitableTimer": "0x00aa6108",
    "WriteFileEx": "0x00aa6234",
    "ReadFileEx": "0x00aa6240",
    "WSARecvFrom": "0x00aa64e8",
    "WSARecv": "0x00aa64ec",
    "WSAIoctl": "0x00aa6524",
}
FORBIDDEN_DIRECT_APC_IMPORTS = {
    "QueueUserAPC",
    "NtQueueApcThread",
    "ZwQueueApcThread",
    "SetWaitableTimerEx",
    "WSASend",
    "WSASendTo",
}


def digest(path: Path, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def pe_sections(data: bytes) -> list[tuple[int, int, int]]:
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise ValueError("input is not a PE image")
    section_count = struct.unpack_from("<H", data, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    section_table = pe_offset + 24 + optional_size
    result: list[tuple[int, int, int]] = []
    for index in range(section_count):
        offset = section_table + index * 40
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", data, offset + 8
        )
        result.append((virtual_address, max(virtual_size, raw_size), raw_offset))
    return result


def parse_imports(data: bytes) -> dict[str, dict[str, object]]:
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    optional_offset = pe_offset + 24
    magic = struct.unpack_from("<H", data, optional_offset)[0]
    if magic == 0x10B:
        data_directory_offset = optional_offset + 96
        thunk_size = 4
        ordinal_mask = 0x80000000
    elif magic == 0x20B:
        data_directory_offset = optional_offset + 112
        thunk_size = 8
        ordinal_mask = 0x8000000000000000
    else:
        raise ValueError("unsupported PE optional-header magic")

    import_rva, _ = struct.unpack_from("<II", data, data_directory_offset + 8)
    sections = pe_sections(data)

    def rva_to_offset(rva: int) -> int:
        for section_rva, section_size, raw_offset in sections:
            if section_rva <= rva < section_rva + section_size:
                return raw_offset + rva - section_rva
        raise ValueError(f"RVA outside mapped sections: 0x{rva:08x}")

    def c_string(offset: int) -> str:
        end = data.index(b"\0", offset)
        return data[offset:end].decode("ascii", "strict")

    imports: dict[str, dict[str, object]] = {}
    descriptor = rva_to_offset(import_rva)
    while True:
        original_first_thunk, timestamp, forwarder_chain, name_rva, first_thunk = (
            struct.unpack_from("<IIIII", data, descriptor)
        )
        if not any((original_first_thunk, timestamp, forwarder_chain, name_rva, first_thunk)):
            break
        dll = c_string(rva_to_offset(name_rva))
        thunk_rva = original_first_thunk or first_thunk
        thunk_offset = rva_to_offset(thunk_rva)
        index = 0
        while True:
            if thunk_size == 4:
                value = struct.unpack_from("<I", data, thunk_offset + index * 4)[0]
            else:
                value = struct.unpack_from("<Q", data, thunk_offset + index * 8)[0]
            if value == 0:
                break
            if value & ordinal_mask:
                name = f"ordinal:{value & 0xffff}"
            else:
                name_offset = rva_to_offset(value)
                name = c_string(name_offset + 2)
            imports[name] = {
                "dll": dll,
                "iat_va": f"0x{0x00400000 + first_thunk + index * thunk_size:08x}",
            }
            index += 1
        descriptor += 20
    return imports


def load_ready(path: Path, expected_format: str) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != expected_format or payload.get("ready") is not True:
        raise ValueError(f"invalid prerequisite evidence: {path}")
    return payload


def build_payload(
    executable: Path,
    async_file_evidence: Path,
    timer_winsock_evidence: Path,
    manager_evidence: Path,
) -> dict[str, object]:
    if digest(executable, "md5") != EXE_MD5 or digest(executable) != EXE_SHA256:
        raise ValueError("SHIFT.exe hash mismatch")

    async_file = load_ready(async_file_evidence, "SHIFT.Process1AsyncFileApcOwnership/1")
    timer_winsock = load_ready(timer_winsock_evidence, "SHIFT.Process1TimerWinsockApcSurface/1")
    managers = load_ready(manager_evidence, "SHIFT.Process1Controller1ManagerApcReachability/1")

    imports = parse_imports(executable.read_bytes())
    recovered = {name: imports[name]["iat_va"] for name in EXPECTED_APC_IMPORTS if name in imports}
    if recovered != EXPECTED_APC_IMPORTS:
        raise ValueError(f"APC-capable import surface drift: {recovered!r}")
    forbidden_hits = sorted(name for name in FORBIDDEN_DIRECT_APC_IMPORTS if name in imports)
    if forbidden_hits:
        raise ValueError(f"new direct APC-capable import appeared: {forbidden_hits!r}")

    async_adj = async_file["adjudication"]
    timer_adj = timer_winsock["adjudication"]
    manager_adj = managers["adjudication"]
    if async_adj["identified_read_write_file_ex_surface_owned_by_base_file_async_thread_proven"] is not True:
        raise ValueError("async-file thread ownership proof missing")
    if async_adj["identified_read_write_file_ex_surface_owned_by_controller1_proven"] is not False:
        raise ValueError("ReadFileEx/WriteFileEx unexpectedly attributed to Controller #1")
    if timer_adj["timer_and_winsock_completion_callbacks_are_not_controller1_wake_sources"] is not True:
        raise ValueError("timer/Winsock negative APC proof missing")
    if manager_adj["direct_named_path_to_readfileex_or_writefileex_proven"] is not False:
        raise ValueError("Controller #1 manager direct file-I/O path appeared")

    return {
        "format": "SHIFT.Process1Controller1ApcSourceInventory/1",
        "ready": True,
        "source": {
            "authority": "PC retail 1.02",
            "retail_executable_md5": EXE_MD5,
            "retail_executable_sha256": EXE_SHA256,
        },
        "imported_completion_apc_surface": {
            "imports": EXPECTED_APC_IMPORTS,
            "direct_apc_injection_imports_present": [],
        },
        "ownership_join": {
            "ReadFileEx": "Base File: Async Thread",
            "WriteFileEx": "Base File: Async Thread",
            "SetWaitableTimer": "completion routine NULL at both physical callsites",
            "WSARecv": "completion routine NULL",
            "WSARecvFrom": "completion routine NULL",
            "WSAIoctl": "lpOverlapped NULL and completion routine NULL",
        },
        "controller1": {
            "worker": "FUN_00662880",
            "alertable_sleep": "SleepEx(10, TRUE)",
            "concrete_imported_completion_source_joined_to_controller1": False,
            "direct_named_manager_path_to_readfileex_or_writefileex": False,
        },
        "adjudication": {
            "known_imported_completion_apc_sources_accounted_for": True,
            "known_imported_completion_apc_source_targets_controller1_proven": False,
            "controller1_alertable_sleep_has_concrete_recovered_apc_wake_source_proven": False,
            "indirect_or_native_apc_injection_ruled_out": False,
            "render_or_present_phase_lock_proven": False,
        },
        "prerequisites": {
            "async_file": async_file["format"],
            "timer_winsock": timer_winsock["format"],
            "manager_reachability": managers["format"],
        },
        "next_blocker": {
            "process": 1,
            "description": (
                "resolve indirect/native APC injection or prove none is joined to Controller #1; "
                "in parallel classify generic queue producers by Controller #1 queue-object identity"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True, type=Path)
    parser.add_argument("--async-file-evidence", required=True, type=Path)
    parser.add_argument("--timer-winsock-evidence", required=True, type=Path)
    parser.add_argument("--manager-evidence", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build_payload(
        args.exe,
        args.async_file_evidence,
        args.timer_winsock_evidence,
        args.manager_evidence,
    )
    rendered = json.dumps(payload, indent=2) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
