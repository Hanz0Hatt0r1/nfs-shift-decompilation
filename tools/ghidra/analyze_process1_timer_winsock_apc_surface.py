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
    "winsock_recv_completion_null": (0x005FDC98, 0x005FDD26),
    "wsaioctl_overlapped_and_completion_null": (0x005FF443, 0x005FF473),
    "fmod_record_timer_completion_null": (0x0099880F, 0x00998831),
    "fmod_output_timer_completion_null": (0x00998DF7, 0x00998E19),
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


def function_body(text: str, name: str) -> str:
    for match in re.finditer(re.escape(name) + r"\s*\(", text):
        brace = text.find("{", match.end())
        if brace < 0:
            continue
        line_start = text.rfind("\n", 0, match.start()) + 1
        prefix = text[line_start : match.start()]
        if line_start > 0 and prefix.startswith(" "):
            continue
        depth = 0
        for index in range(brace, len(text)):
            char = text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[line_start : index + 1]
    raise ValueError(f"missing function definition {name}")


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
    recv = function_body(text, "FUN_005fdc90")
    ioctl = function_body(text, "FUN_005ff390")
    timer_record = function_body(text, "FUN_009983fe")
    timer_output = function_body(text, "FUN_00998936")

    if "WSARecv(*(undefined4 *)(in_EAX + 0x18),&local_8,1,piVar1,puVar2,in_EAX + 0x54,0)" not in recv:
        raise ValueError("WSARecv null completion routine drift")
    if "WSARecvFrom" not in recv:
        raise ValueError("WSARecvFrom callsite missing")
    if "WSAIoctl(iVar1,0xc8000014,param_3,param_4,&stack0xfffffee0,0x10,auStack_4,0,0)" not in ioctl:
        raise ValueError("WSAIoctl null overlapped/completion arguments drift")
    if "pfnCompletionRoutine = (PTIMERAPCROUTINE)0x0;" not in timer_record:
        raise ValueError("record timer completion routine is no longer null")
    if "lpArgToCompletionRoutine = (LPVOID)0x0;" not in timer_record:
        raise ValueError("record timer completion argument is no longer null")
    if "pfnCompletionRoutine = (PTIMERAPCROUTINE)0x0;" not in timer_output:
        raise ValueError("output timer completion routine is no longer null")
    if "lpArgToCompletionRoutine = (LPVOID)0x0;" not in timer_output:
        raise ValueError("output timer completion argument is no longer null")

    if "QueueUserAPC" in text or "NtQueueApcThread" in text or "ZwQueueApcThread" in text:
        raise ValueError("new direct APC injection token appeared in pinned source")

    image = executable.read_bytes()
    machine_spans: dict[str, dict[str, object]] = {}
    for key, (start, end_exclusive) in SPANS.items():
        raw = va_bytes(image, start, end_exclusive)
        machine_spans[key] = {
            "start": f"0x{start:08x}",
            "end_exclusive": f"0x{end_exclusive:08x}",
            "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }

    recv_raw = va_bytes(image, *SPANS["winsock_recv_completion_null"])
    if not recv_raw.startswith(bytes.fromhex("33ed")):
        raise ValueError("FUN_005fdc90 no longer zeroes EBP before shared completion argument")
    ioctl_raw = va_bytes(image, *SPANS["wsaioctl_overlapped_and_completion_null"])
    if not ioctl_raw.startswith(bytes.fromhex("33c05050")):
        raise ValueError("WSAIoctl null overlapped/completion push pattern drift")
    timer_record_raw = va_bytes(image, *SPANS["fmod_record_timer_completion_null"])
    timer_output_raw = va_bytes(image, *SPANS["fmod_output_timer_completion_null"])
    if not timer_record_raw.startswith(bytes.fromhex("53535353")):
        raise ValueError("record timer zero-argument push pattern drift")
    if not timer_output_raw.startswith(bytes.fromhex("53535353")):
        raise ValueError("output timer zero-argument push pattern drift")

    return {
        "format": "SHIFT.Process1TimerWinsockApcSurface/1",
        "ready": True,
        "source": {
            "authority": "PC retail 1.02",
            "retail_executable_md5": EXE_MD5,
            "retail_executable_sha256": EXE_SHA256,
            "retail_source_sha256": SOURCE_SHA256,
            "xbox_recomp_required": False,
        },
        "timer_completion_surface": {
            "api": "SetWaitableTimer",
            "physical_machine_callsite_count": 2,
            "ghidra_source_rendered_call_count": text.count("SetWaitableTimer("),
            "completion_routine_nonnull_callsite_count": 0,
            "completion_argument_nonnull_callsite_count": 0,
            "callsites": [
                {
                    "owner": "FUN_009983fe",
                    "subsystem": "FMOD record thread setup",
                    "pfnCompletionRoutine": "NULL",
                    "lpArgToCompletionRoutine": "NULL",
                    "fResume": False,
                    "source_line": line_number(text, "BVar9 = SetWaitableTimer"),
                },
                {
                    "owner": "FUN_00998936",
                    "subsystem": "FMOD WASAPI output setup",
                    "pfnCompletionRoutine": "NULL",
                    "lpArgToCompletionRoutine": "NULL",
                    "fResume": False,
                    "source_line": line_number(text, "BVar10 = SetWaitableTimer"),
                },
            ],
            "note": (
                "Ghidra renders the FUN_009983fe machine callsite twice along an overlapping "
                "stack-recovery path; the pinned machine image contains one physical import call there"
            ),
        },
        "winsock_completion_surface": {
            "owner_recv": "FUN_005fdc90",
            "owner_ioctl": "FUN_005ff390",
            "wsarecv_completion_routine": "NULL",
            "wsarecvfrom_completion_routine": "NULL (machine ABI ninth argument)",
            "wsaioctl_overlapped": "NULL",
            "wsaioctl_completion_routine": "NULL",
            "source_lines": {
                "recv_function": line_number(text, "int FUN_005fdc90(void)"),
                "wsarecvfrom": line_number(text, "iVar3 = WSARecvFrom"),
                "wsarecv": line_number(text, "iVar3 = WSARecv("),
                "ioctl_function": line_number(text, "undefined4 __cdecl FUN_005ff390"),
                "wsaioctl": line_number(text, "iVar2 = WSAIoctl"),
            },
        },
        "direct_manual_apc_tokens": {
            "QueueUserAPC": 0,
            "NtQueueApcThread": 0,
            "ZwQueueApcThread": 0,
        },
        "adjudication": {
            "source_visible_waitable_timer_completion_can_apc_controller1": False,
            "source_visible_winsock_completion_can_apc_controller1": False,
            "timer_and_winsock_completion_callbacks_are_not_controller1_wake_sources": True,
            "readfileex_writefileex_surface_adjudicated_here": False,
            "indirect_or_native_apc_sources_ruled_out": False,
            "render_or_present_phase_lock_proven": False,
        },
        "machine_spans": machine_spans,
        "next_blocker": {
            "process": 1,
            "description": (
                "join the separately recovered ReadFileEx/WriteFileEx APC owner to the remaining "
                "Controller #1 manager indirect-call surface; timer and Winsock completion-routine "
                "APCs are now negative in the pinned PC retail build"
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
