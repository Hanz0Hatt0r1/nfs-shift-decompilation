#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1D.P13DSlot3UnrolledMovMachineClosure/1"
INPUT_FORMAT = "SHIFT.P1A.P13ASlot01UnrolledMovCopyFrontierEvidence/1"
PE_SHA = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED = [
    "0x0076e560",
    "0x007b0710",
    "0x00403d00",
    "0x004e9380",
    "0x00633290",
    "0x006333f0",
    "0x0075a8d0",
    "0x007b0580",
    "0x0064fef0",
    "0x007b0450",
    "0x00900fef",
]
INSN_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s*(.*)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def disassemble(executable: Path, start: int, end: int) -> dict[int, tuple[str, str]]:
    output = subprocess.check_output(
        [
            "objdump",
            "-d",
            "-Mintel",
            f"--start-address=0x{start:x}",
            f"--stop-address=0x{end:x}",
            str(executable),
        ],
        text=True,
        errors="replace",
    )
    decoded: dict[int, tuple[str, str]] = {}
    for line in output.splitlines():
        match = INSN_RE.match(line)
        if match:
            decoded[int(match.group(1), 16)] = (
                "".join(match.group(2).split()).lower(),
                match.group(3).strip().lower(),
            )
    return decoded


def check(decoded: dict[int, tuple[str, str]], address: int, hex_bytes: str, text_contains: str | None = None) -> str:
    if address not in decoded:
        raise ValueError(f"missing instruction 0x{address:08x}")
    got_bytes, got_text = decoded[address]
    if got_bytes != hex_bytes.lower():
        raise ValueError(f"byte drift 0x{address:08x}: {got_bytes} != {hex_bytes}")
    if text_contains and text_contains.lower() not in got_text:
        raise ValueError(f"text drift 0x{address:08x}: {got_text!r}")
    return f"0x{address:08x} {got_text}"


def validate_frontier(frontier: dict) -> None:
    if frontier.get("format") != INPUT_FORMAT:
        raise ValueError("frontier format drift")
    if not frontier.get("ready"):
        raise ValueError("frontier not ready")
    addresses = [str(row.get("address", "")).lower() for row in frontier.get("candidates", [])]
    if addresses != EXPECTED:
        raise ValueError(f"candidate order/set drift: {addresses!r}")
    scan = frontier.get("scan", {})
    if scan.get("candidate_function_count") != 11:
        raise ValueError("candidate count drift")
    if scan.get("max_direct_call_depth") != 4:
        raise ValueError("depth drift")


def analyze(executable: Path, frontier_path: Path) -> dict:
    executable_hash = sha256(executable)
    if executable_hash != PE_SHA:
        raise ValueError(f"unexpected retail PE hash: {executable_hash}")
    frontier = json.loads(frontier_path.read_text(encoding="utf-8"))
    validate_frontier(frontier)

    ranges = [
        (0x0076E560, 0x0076E850),
        (0x00765DF0, 0x00766120),
        (0x0074F560, 0x0074F773),
        (0x007B0C80, 0x007B0D10),
        (0x00770100, 0x00770145),
        (0x0076D6A0, 0x0076D800),
        (0x00403D00, 0x00403D6C),
        (0x004E9380, 0x004E94A0),
        (0x00633290, 0x00633304),
        (0x006333F0, 0x0063353D),
        (0x00767CB0, 0x00767CE0),
        (0x0075AD40, 0x0075AD90),
        (0x007B0900, 0x007B0940),
        (0x007B0580, 0x007B05FC),
        (0x0064FEF0, 0x0064FF31),
        (0x007B0450, 0x007B0485),
        (0x0090DB50, 0x0090DB80),
        (0x00900FEF, 0x0090106F),
    ]
    maps = [disassemble(executable, start, end) for start, end in ranges]
    candidate_adjudication = []

    candidate_adjudication.append(
        {
            "function": "FUN_0076e560",
            "address": "0x0076e560",
            "class": "service-query-record-output",
            "anchors": [
                check(maps[0], 0x0076E75E, "e82d17faff", "call"),
                check(maps[0], 0x0076E763, "8bb888020000", "[eax+0x288]"),
                check(maps[0], 0x0076E76F, "8d55fc", "[ebp-0x4]"),
                check(maps[0], 0x0076E774, "e817c4f9ff", "call"),
                check(maps[0], 0x0076E77D, "8b55fc", "[ebp-0x4]"),
                check(maps[0], 0x0076E7A6, "894208", "[edx+0x8]"),
                check(maps[0], 0x0076E7B7, "89420c", "[edx+0xc]"),
                check(maps[0], 0x0076E7E5, "e8a616faff", "call"),
                check(maps[0], 0x0076E7EA, "8bb888020000", "[eax+0x288]"),
                check(maps[0], 0x0076E7F6, "8d55f4", "[ebp-0xc]"),
                check(maps[0], 0x0076E7FB, "e890c3f9ff", "call"),
                check(maps[0], 0x0076E804, "8b55f4", "[ebp-0xc]"),
                check(maps[0], 0x0076E82D, "894a08", "[edx+0x8]"),
                check(maps[0], 0x0076E83C, "894a0c", "[edx+0xc]"),
            ],
            "reason": "Both 8-byte store clusters target records returned through FUN_0070a290 from the service object at FUN_0070fe90()->+0x288, not the wheel receiver.",
        }
    )
    candidate_adjudication.append(
        {
            "function": "FUN_007b0710",
            "address": "0x007b0710",
            "class": "fixed-global-contact-ring-record",
            "anchors": [
                check(maps[1], 0x00765E38, "8d8d20ffffff", "[ebp-0xe0]"),
                check(maps[1], 0x00765E86, "e885a80400", "call"),
                check(maps[1], 0x007660E5, "8d8d20ffffff", "[ebp-0xe0]"),
                check(maps[1], 0x00766119, "e8f2a50400", "call"),
                check(maps[3], 0x007B0C8A, "8bcf", "mov"),
                check(maps[3], 0x007B0C8E, "e8cde8f9ff", "call"),
                check(maps[3], 0x007B0C93, "8bf0", "mov"),
                check(maps[3], 0x007B0CCA, "894648", "[esi+0x48]"),
                check(maps[3], 0x007B0CCD, "894e4c", "[esi+0x4c]"),
                check(maps[2], 0x0074F579, "8b35e8bbc100", "0xc1bbe8"),
                check(maps[2], 0x0074F584, "6bf658", "0x58"),
                check(maps[2], 0x0074F587, "0335e0bac100", "0xc1bae0"),
                check(maps[2], 0x0074F757, "8bc6", "mov"),
            ],
            "reason": "FUN_0074f560 returns the current 0x58-byte record from the fixed global ring rooted at 0x00c1bae0; the unrolled stores update that record at +0x48/+0x4c.",
        }
    )
    candidate_adjudication.append(
        {
            "function": "FUN_00403d00",
            "address": "0x00403d00",
            "class": "tagged-service-query-record",
            "anchors": [
                check(maps[4], 0x00770105, "e886fdf9ff", "call"),
                check(maps[4], 0x0077010A, "8bb888020000", "[eax+0x288]"),
                check(maps[4], 0x00770116, "8d55bc", "[ebp-0x44]"),
                check(maps[4], 0x0077011B, "e870a1f9ff", "call"),
                check(maps[4], 0x00770124, "8b55bc", "[ebp-0x44]"),
                check(maps[4], 0x0077012A, "c6420503", "[edx+0x5]"),
                check(maps[4], 0x0077012E, "c6420449", "[edx+0x4]"),
                check(maps[5], 0x0076D77D, "8d55f0", "[ebp-0x10]"),
                check(maps[5], 0x0076D787, "e804cbf9ff", "call"),
                check(maps[5], 0x0076D7B5, "8b4df0", "[ebp-0x10]"),
                check(maps[5], 0x0076D7B9, "e84265c9ff", "call"),
                check(maps[6], 0x00403D03, "8bc1", "mov"),
                check(maps[6], 0x00403D5F, "895004", "[eax+0x4]"),
                check(maps[6], 0x00403D65, "894808", "[eax+0x8]"),
            ],
            "reason": "The destination ECX/EAX is returned by the same service-query family that creates tagged request/record objects; it is not selected wheel storage.",
        }
    )
    candidate_adjudication.append(
        {
            "function": "FUN_004e9380",
            "address": "0x004e9380",
            "class": "fixed-global-table-entry",
            "anchors": [
                check(maps[3], 0x007B0CF4, "b9e0b9c100", "0xc1b9e0"),
                check(maps[3], 0x007B0CF9, "e88286d3ff", "call"),
                check(maps[7], 0x004E9387, "8bd9", "mov"),
                check(maps[7], 0x004E93CB, "8b93e0000000", "[ebx+0xe0]"),
                check(maps[7], 0x004E93D8, "8d047f", "lea"),
                check(maps[7], 0x004E93DB, "8d34c2", "lea"),
                check(maps[7], 0x004E9454, "890e", "[esi]"),
                check(maps[7], 0x004E9459, "895604", "[esi+0x4]"),
                check(maps[7], 0x004E945C, "894608", "[esi+0x8]"),
                check(maps[7], 0x004E945F, "894e0c", "[esi+0xc]"),
                check(maps[7], 0x004E9476, "894610", "[esi+0x10]"),
            ],
            "reason": "The destination ESI is an indexed entry from fixed global object 0x00c1b9e0->+0xe0, not a selected HDVehicle wheel.",
        }
    )
    candidate_adjudication.append(
        {
            "function": "FUN_00633290",
            "address": "0x00633290",
            "class": "fresh-allocator-node",
            "anchors": [
                check(maps[8], 0x006332AF, "8bd6", "mov"),
                check(maps[8], 0x006332B1, "e8fafeffff", "call"),
                check(maps[8], 0x006332BC, "8bcf", "mov"),
                check(maps[8], 0x006332BE, "e82dc4ffff", "call"),
                check(maps[8], 0x006332D6, "e8454d0000", "call"),
                check(maps[8], 0x006332F4, "894804", "[eax+0x4]"),
                check(maps[8], 0x006332F7, "895008", "[eax+0x8]"),
                check(maps[8], 0x006332FA, "83c010", "0x10"),
            ],
            "reason": "Candidate stores initialize an allocator-managed node and return node+0x10; no store targets the caller wheel receiver.",
        }
    )
    candidate_adjudication.append(
        {
            "function": "FUN_006333f0",
            "address": "0x006333f0",
            "class": "service-record-linked-list",
            "anchors": [
                check(maps[5], 0x0076D6D2, "8bfa", "mov"),
                check(maps[5], 0x0076D745, "57", "push"),
                check(maps[5], 0x0076D748, "e8a35cecff", "call"),
                check(maps[9], 0x006333F7, "8bf1", "mov"),
                check(maps[9], 0x00633401, "8b7d08", "[ebp+0x8]"),
                check(maps[9], 0x00633421, "e8caca0100", "call"),
                check(maps[9], 0x00633492, "89501c", "[eax+0x1c]"),
                check(maps[9], 0x00633498, "8996b8000000", "[esi+0xb8]"),
                check(maps[9], 0x006334B6, "895018", "[eax+0x18]"),
                check(maps[9], 0x006334BC, "8986b4000000", "[esi+0xb4]"),
            ],
            "reason": "The candidate writes are linked-list fields joining the service-query record passed in EDI, not wheel-local storage.",
        }
    )
    candidate_adjudication.append(
        {
            "function": "FUN_0075a8d0",
            "address": "0x0075a8d0",
            "class": "hdvehicle-output-at-0x40c8",
            "anchors": [
                check(maps[10], 0x00767CBC, "8dbec8400000", "[esi+0x40c8]"),
                check(maps[10], 0x00767CC2, "57", "push"),
                check(maps[10], 0x00767CD3, "e8f82bffff", "call"),
                check(maps[11], 0x0075AD4F, "8b4510", "[ebp+0x10]"),
                check(maps[11], 0x0075AD5C, "8908", "[eax]"),
                check(maps[11], 0x0075AD61, "894804", "[eax+0x4]"),
                check(maps[11], 0x0075AD67, "895008", "[eax+0x8]"),
                check(maps[11], 0x0075AD6A, "89480c", "[eax+0xc]"),
            ],
            "reason": "The third stack argument is exactly HDVehicle+0x40c8, so the 16-byte destination is +0x40c8..+0x40d7, not slot3 +0x28b8..+0x28bf.",
        }
    )
    candidate_adjudication.append(
        {
            "function": "FUN_007b0580",
            "address": "0x007b0580",
            "class": "stack-local-output-record",
            "anchors": [
                check(maps[12], 0x007B0919, "8d55a8", "[ebp-0x58]"),
                check(maps[12], 0x007B091E, "b9e0b9c100", "0xc1b9e0"),
                check(maps[12], 0x007B092A, "e851fcffff", "call"),
                check(maps[13], 0x007B0590, "8bf2", "mov"),
                check(maps[13], 0x007B05CC, "895608", "[esi+0x8]"),
                check(maps[13], 0x007B05D2, "89560c", "[esi+0xc]"),
                check(maps[13], 0x007B05DF, "894e18", "[esi+0x18]"),
                check(maps[13], 0x007B05E6, "89561c", "[esi+0x1c]"),
            ],
            "reason": "The candidate destination ESI is exactly the caller stack local EBP-0x58.",
        }
    )
    candidate_adjudication.append(
        {
            "function": "FUN_0064fef0",
            "address": "0x0064fef0",
            "class": "fresh-allocator-output",
            "anchors": [
                check(maps[14], 0x0064FEF7, "8d8f90000000", "[edi+0x90]"),
                check(maps[14], 0x0064FEFF, "e8ecf7fdff", "call"),
                check(maps[14], 0x0064FF04, "8906", "[esi]"),
                check(maps[14], 0x0064FF0C, "8908", "[eax]"),
                check(maps[14], 0x0064FF1E, "894808", "[eax+0x8]"),
                check(maps[14], 0x0064FF21, "89500c", "[eax+0xc]"),
            ],
            "reason": "All candidate stores target the freshly allocated block returned by FUN_0062f6f0 and published through an out-pointer.",
        }
    )
    candidate_adjudication.append(
        {
            "function": "FUN_007b0450",
            "address": "0x007b0450",
            "class": "path-infeasible-zero-gated-optional-output",
            "anchors": [
                check(maps[3], 0x007B0CE4, "6a00", "push"),
                check(maps[3], 0x007B0CE6, "6a00", "push"),
                check(maps[3], 0x007B0CE8, "6a00", "push"),
                check(maps[3], 0x007B0CF9, "e88286d3ff", "call"),
                check(maps[7], 0x004E9479, "8b5518", "[ebp+0x18]"),
                check(maps[7], 0x004E947C, "85d2", "test"),
                check(maps[7], 0x004E947E, "7408", "je"),
                check(maps[7], 0x004E9483, "e8c86f2c00", "call"),
            ],
            "reason": "On the only bounded path, 0x007b0710 passes zero as arg5 to FUN_004e9380; FUN_004e9380 calls FUN_007b0450 only when arg5 is nonzero, so this path cannot execute that candidate.",
        }
    )
    candidate_adjudication.append(
        {
            "function": "_LocaleUpdate",
            "address": "0x00900fef",
            "class": "crt-stack-local-locale-update",
            "anchors": [
                check(maps[16], 0x0090DB5A, "8d4d9c", "[ebp-0x64]"),
                check(maps[16], 0x0090DB78, "e87234ffff", "call"),
                check(maps[17], 0x00900FF6, "8bf1", "mov"),
                check(maps[17], 0x00901009, "890e", "[esi]"),
                check(maps[17], 0x0090100E, "894e04", "[esi+0x4]"),
                check(maps[17], 0x00901063, "890e", "[esi]"),
                check(maps[17], 0x00901068, "894604", "[esi+0x4]"),
            ],
            "reason": "The bounded caller passes ECX=EBP-0x64, so all candidate stores update a stack-local CRT locale wrapper.",
        }
    )

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": PE_SHA,
            "machine_transfer_adjudicates": True,
            "p1a_frontier_is_navigation_only": True,
        },
        "upstream_contract": INPUT_FORMAT,
        "slot3": {
            "absolute_target": "HDVehicle+0x28b8",
            "target_byte_range": ["HDVehicle+0x28b8", "HDVehicle+0x28bf"],
            "local_field": "+0x538",
            "width": "f64/qword",
        },
        "frontier": {
            "max_direct_call_depth": 4,
            "candidate_count": 11,
            "rejected_count": 11,
            "candidate_adjudication": candidate_adjudication,
        },
        "adjudication": {
            "slot3_shallow_straight_line_unrolled_mov_depth4_subset_complete": True,
            "slot3_shallow_unrolled_mov_writer_found": False,
            "slot3_straight_line_zero_init_surface_complete": False,
            "slot3_sse_custom_copy_surface_complete": False,
            "slot3_non_entry_alias_loop_surface_complete": False,
            "slot3_deeper_direct_copy_init_paths_complete": False,
            "slot3_indirect_dispatch_surface_complete": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the 11 shallow depth<=4 non-loop, non-stack, non-zero-init unrolled MOV-copy candidates inventoried by the upstream P1A navigation frontier.",
            "Zero-init, SSE/vector/custom transforms, non-entry alias loops, deeper direct paths and indirect/callback dispatch remain open.",
            "No numeric offset or callgraph reachability is used as selected-HDVehicle identity.",
        ],
        "next_step": "Inventory shallow straight-line zero-initialization and SSE/custom transfer candidates; separately trace non-entry alias loops. Widen deeper/indirect only when exact selected-wheel-derived destination provenance exists.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("frontier", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.executable, args.frontier)
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
