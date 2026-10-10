#!/usr/bin/env python3
"""Close the FUN_00765c40 four-wheel ECX register-alias loop for P1.3D.

Object identity and the callee side-effect classification are consumed from
already-merged contracts. This pass pins the exact PC-retail machine transfer
that materializes HDVehicle+0x400, advances it by the 0xa80 wheel stride, and
therefore reaches selected slot3 HDVehicle+0x2380 on the fourth call.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3Fun00765c40WheelRegisterAliasClosure/1"
HANDOFF_FORMAT = "SHIFT.P1D.Slot3Fun00765c40CarrierHandoff/1"
WHEEL_PROOF_FORMAT = "SHIFT.Fun00752fa0WheelStateMachineProof/1"
PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

CAPTURE_START = 0x00765C5E
CAPTURE_END = 0x00765C64
LOOP_START = 0x00765EAC
LOOP_END = 0x00765ED4
CALLEE_START = 0x00752FA0
CALLEE_END = 0x00752FB9

CAPTURE_ANCHORS = {
    0x00765C5E: "push esi",
    0x00765C5F: "mov esi,ecx",
    0x00765C61: "fstp DWORD PTR [ebp-0x14]",
}
LOOP_ANCHORS = {
    0x00765EAC: "xor edx,edx",
    0x00765EAE: "lea ecx,[esi+0x400]",
    0x00765EB4: "fld QWORD PTR [esi+0x98]",
    0x00765EBA: "sub esp,0x8",
    0x00765EBD: "fstp QWORD PTR [esp]",
    0x00765EC0: "push edx",
    0x00765EC1: "call 0x752fa0",
    0x00765EC6: "add edx,0x1",
    0x00765EC9: "add ecx,0xa80",
    0x00765ECF: "cmp edx,0x4",
    0x00765ED2: "jl 0x765eb4",
}
CALLEE_ANCHORS = {
    0x00752FA0: "push ebp",
    0x00752FA1: "mov ebp,esp",
    0x00752FA3: "mov eax,DWORD PTR [ebp+0x8]",
    0x00752FA6: "fld QWORD PTR [ebp+0xc]",
    0x00752FA9: "fstp QWORD PTR [ecx+0xa00]",
    0x00752FAF: "mov DWORD PTR [ecx+0x9f8],eax",
    0x00752FB5: "pop ebp",
    0x00752FB6: "ret 0xc",
}

INS_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*(.*)$")
CALL_RE = re.compile(r"^call\b", re.I)
ECX_VALUE_STORE_RE = re.compile(r"^(?:mov\s+[^,]*\[[^\]]+\]\s*,\s*ecx|push\s+ecx)$", re.I)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def norm(text: str) -> str:
    return " ".join(text.split()).lower()


def load_contract(path: Path, expected_format: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != expected_format or not payload.get("ready"):
        raise ValueError(f"{path}: unexpected or unready contract")
    return payload


def disassemble(executable: Path, start: int, stop: int, objdump: str) -> dict[int, str]:
    proc = subprocess.run(
        [
            objdump,
            "-d",
            "-Mintel",
            f"--start-address=0x{start:x}",
            f"--stop-address=0x{stop:x}",
            str(executable),
        ],
        text=True,
        capture_output=True,
        errors="replace",
    )
    if proc.returncode:
        raise ValueError(f"objdump failed: {proc.stderr.strip()}")
    instructions: dict[int, str] = {}
    for line in proc.stdout.splitlines():
        match = INS_RE.match(line)
        if match:
            instructions[int(match.group(1), 16)] = match.group(2).strip()
    return instructions


def require_surface(actual: dict[int, str], expected: dict[int, str], label: str) -> None:
    if set(actual) != set(expected):
        raise ValueError(
            f"{label} instruction-address surface drift: "
            f"actual={[hex(x) for x in actual]} expected={[hex(x) for x in expected]}"
        )
    for address, expected_text in expected.items():
        if norm(actual[address]) != norm(expected_text):
            raise ValueError(
                f"{label} instruction drift at 0x{address:08x}: "
                f"{actual[address]!r} != {expected_text!r}"
            )


def analyze(
    executable: Path,
    handoff_path: Path,
    wheel_proof_path: Path,
    objdump: str = "objdump",
) -> dict:
    handoff = load_contract(handoff_path, HANDOFF_FORMAT)
    wheel_proof = load_contract(wheel_proof_path, WHEEL_PROOF_FORMAT)

    authority = handoff.get("authority", {})
    carrier = handoff.get("carrier", {})
    selected = handoff.get("selected_slot3", {})
    if authority.get("retail_executable_sha256") != PE_SHA256:
        raise ValueError("carrier-handoff retail identity drift")
    if (
        carrier.get("function") != "FUN_00765c40"
        or carrier.get("entry") != "0x00765c40"
        or carrier.get("receiver_domain") != "HDVehicle"
    ):
        raise ValueError("FUN_00765c40 HDVehicle identity drift")
    if selected.get("absolute_target") != "HDVehicle+0x28b8":
        raise ValueError("selected slot3 target drift")
    if handoff.get("adjudication", {}).get("fun00765c40_exact_hdvehicle_carrier_handoff_complete") is not True:
        raise ValueError("FUN_00765c40 exact-HDVehicle handoff is not complete")

    wheel_authority = wheel_proof.get("authority", {})
    caller_join = wheel_proof.get("caller_join", {})
    if wheel_authority.get("retail_executable_sha256") != PE_SHA256:
        raise ValueError("FUN_00752fa0 wheel-proof retail identity drift")
    if (
        wheel_authority.get("callee_entry") != "0x00752fa0"
        or caller_join.get("caller") != "FUN_00765c40"
        or caller_join.get("call_site") != "0x00765ec1"
        or caller_join.get("receiver_first") != "HDVehicle+0x400"
        or caller_join.get("receiver_count") != 4
        or caller_join.get("receiver_stride") != "0x0a80"
    ):
        raise ValueError("FUN_00752fa0 caller-join drift")
    if wheel_proof.get("callee_side_effect_surface_closed") is not True:
        raise ValueError("FUN_00752fa0 side-effect surface is not closed")

    digest = sha256(executable)
    if digest != PE_SHA256:
        raise ValueError(f"unexpected retail PE SHA-256: {digest}")

    capture = disassemble(executable, CAPTURE_START, CAPTURE_END, objdump)
    loop = disassemble(executable, LOOP_START, LOOP_END, objdump)
    callee = disassemble(executable, CALLEE_START, CALLEE_END, objdump)
    require_surface(capture, CAPTURE_ANCHORS, "FUN_00765c40 root capture")
    require_surface(loop, LOOP_ANCHORS, "FUN_00765c40 wheel loop")
    require_surface(callee, CALLEE_ANCHORS, "FUN_00752fa0 leaf")

    if any(CALL_RE.match(norm(text)) for text in callee.values()):
        raise ValueError("FUN_00752fa0 unexpectedly contains a direct call")
    if any(ECX_VALUE_STORE_RE.match(norm(text)) for text in list(loop.values()) + list(callee.values())):
        raise ValueError("selected-wheel ECX pointer value is unexpectedly stored or pushed")

    receiver_offsets = [0x400 + index * 0xA80 for index in range(4)]
    if receiver_offsets != [0x400, 0xE80, 0x1900, 0x2380]:
        raise ValueError("wheel receiver arithmetic drift")
    selected_receiver = receiver_offsets[3]
    if selected_receiver != 0x2380:
        raise ValueError("fourth receiver no longer resolves to selected slot3")

    per_wheel_write_offsets = [0x9F8, 0xA00]
    selected_vehicle_writes = [selected_receiver + offset for offset in per_wheel_write_offsets]
    target_start = 0x28B8
    target_end = 0x28BF
    write_ranges = [(selected_vehicle_writes[0], selected_vehicle_writes[0] + 3),
                    (selected_vehicle_writes[1], selected_vehicle_writes[1] + 7)]
    overlap = any(start <= target_end and end >= target_start for start, end in write_ranges)
    if overlap:
        raise ValueError("FUN_00752fa0 selected-slot3 write unexpectedly overlaps target")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "upstream_contracts": [HANDOFF_FORMAT, WHEEL_PROOF_FORMAT],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": digest,
            "machine_transfer_adjudicates": True,
            "upstream_machine_contracts_consumed_not_reowned": True,
        },
        "root_capture": {
            "site": "0x00765c5f",
            "instruction": "mov esi,ecx",
            "input_receiver": "HDVehicle",
            "alias": "ESI=HDVehicle",
        },
        "wheel_loop": {
            "init_site": "0x00765eae",
            "init_instruction": "lea ecx,[esi+0x400]",
            "stride_site": "0x00765ec9",
            "stride_instruction": "add ecx,0xa80",
            "call_site": "0x00765ec1",
            "callee": "FUN_00752fa0",
            "receiver_count": 4,
            "receiver_offsets": ["+0x400", "+0x0e80", "+0x1900", "+0x2380"],
            "selected_slot3_iteration": 3,
            "selected_slot3_receiver": "HDVehicle+0x2380",
            "exact_receiver_pointer_store_found": False,
            "exact_receiver_pointer_push_found": False,
        },
        "callee": {
            "function": "FUN_00752fa0",
            "leaf": True,
            "direct_call_count": 0,
            "ecx_value_reassigned": False,
            "ecx_value_stored_or_pushed": False,
            "per_wheel_write_offsets": ["+0x9f8 dword", "+0xa00 qword"],
            "selected_slot3_vehicle_relative_writes": ["+0x2d78 dword", "+0x2d80 qword"],
            "selected_target_overlap": False,
        },
        "adjudication": {
            "fun00765c40_four_wheel_register_alias_subset_complete": True,
            "fun00765c40_selected_slot3_register_alias_reached": True,
            "fun00765c40_selected_slot3_pointer_escape_found": False,
            "fun00752fa0_selected_slot3_writer_found": False,
            "other_fun00765c40_derived_aliases_ruled_out": False,
            "machine_register_alias_storage_ruled_out": False,
            "runtime_generated_pointer_stores_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the four-wheel ECX alias loop at 0x00765eae..0x00765ed2 and its leaf FUN_00752fa0 receiver use.",
            "Other FUN_00765c40 interior wheel pointers, stack-local derived aliases, runtime/generated pointers, callbacks and indirect entry remain open.",
            "The callee's write semantics are consumed from SHIFT.Fun00752fa0WheelStateMachineProof/1 and are not re-owned here.",
        ],
        "next_step": "Bound the branch-equivalent FUN_00765c40 wheel+0x678 interior-pointer loops at 0x00765cde/0x00765d67, including their stack-local pointer slot and [wheel+0x420] child loads; then continue runtime/callee-created alias joins.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("wheel_proof", type=Path)
    parser.add_argument("--objdump", default="objdump")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.executable, args.handoff, args.wheel_proof, args.objdump)
    except ValueError as exc:
        parser.error(str(exc))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
