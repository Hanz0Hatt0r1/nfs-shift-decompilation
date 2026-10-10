#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330GetProcAddressWrapperOutputPersistence/1"
EXPECTED_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED_SIZE = 8_801_792
EXPECTED_PROVIDER_COUNT = 7
WRAPPER = 0x0093DD2B

ROWS = [
    (0x0093CF1D, "[ebp-0x30]", 0x0093CF2F, None),
    (0x0093CF5B, "[ebp-0x20]", 0x0093CF6D, None),
    (0x0093CF99, "[ebp-0x24]", 0x0093CFA8, None),
    (0x0093CFD4, "[ebp-0x1c]", 0x0093CFE3, None),
    (0x0093D007, "[ebp-0x28]", 0x0093D016, None),
    (0x0093D042, "[ebp-0x34]", 0x0093D051, None),
    (0x0093D06E, "[ebp-0x18]", 0x0093D09B, None),
    (0x0093D086, "[ebp-0x18]", 0x0093D09B, None),
    (0x0093D276, "[ebp-0x2c]", 0x0093D288, None),
    (0x00997659, "[ebp-0x14]", 0x0099767C, 0x009976D8),
    (0x00997B7A, "[ebp-0x14]", 0x00997B9D, 0x00997C65),
    (0x009A8A1D, "[ebp-0x20]", 0x009A8A32, 0x009A8AC9),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def disassemble(path: Path) -> list[tuple[int, str]]:
    text = subprocess.check_output(
        ["objdump", "-d", "-Mintel", str(path)], text=True, errors="replace"
    )
    out = []
    rx = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*\t(.*)$")
    for line in text.splitlines():
        m = rx.match(line)
        if m:
            out.append((int(m.group(1), 16), m.group(2).strip()))
    return out


def is_value_read(text: str, slot: str) -> bool:
    if slot not in text:
        return False
    if text.startswith("lea "):
        return False
    if re.match(rf"^(mov|and)\s+DWORD PTR {re.escape(slot)},", text):
        return False
    return True


def build(exe: Path) -> dict:
    if exe.stat().st_size != EXPECTED_SIZE:
        raise ValueError("retail executable size drift")
    digest = sha256(exe)
    if digest != EXPECTED_SHA256:
        raise ValueError("retail executable hash drift")

    insns = disassemble(exe)
    by_addr = {a: t for a, t in insns}
    direct_calls = [a for a, t in insns if t == f"call   0x{WRAPPER:x}"]
    expected_calls = [r[0] for r in ROWS]
    if direct_calls != expected_calls:
        raise ValueError(f"wrapper direct-call surface drift: {direct_calls!r}")

    details = []
    unique_indirect_calls = set()
    for callsite, slot, terminal_use, overwrite in ROWS:
        if by_addr.get(callsite) != f"call   0x{WRAPPER:x}":
            raise ValueError(f"wrapper call mismatch at 0x{callsite:08x}")
        terminal_text = by_addr.get(terminal_use, "")
        expected_terminal = f"call   DWORD PTR {slot}"
        if terminal_text != expected_terminal:
            raise ValueError(
                f"terminal use drift at 0x{terminal_use:08x}: {terminal_text!r}"
            )
        unique_indirect_calls.add(terminal_use)

        prev = [(a, t) for a, t in insns if callsite - 0x20 <= a < callsite]
        lea_hits = [a for a, t in prev if t.startswith("lea ") and slot in t]
        if not lea_hits:
            raise ValueError(f"stack-local destination setup missing at 0x{callsite:08x}")

        end = overwrite if overwrite is not None else terminal_use
        interval = [(a, t) for a, t in insns if callsite < a <= end and slot in t]
        value_reads = [(a, t) for a, t in interval if is_value_read(t, slot)]
        bad_reads = [(a, t) for a, t in value_reads if a != terminal_use]
        if bad_reads:
            raise ValueError(
                f"resolved pointer copied/escaped before kill at 0x{callsite:08x}: {bad_reads!r}"
            )

        if overwrite is not None:
            overwrite_text = by_addr.get(overwrite, "")
            if slot not in overwrite_text:
                raise ValueError(f"expected overwrite missing at 0x{overwrite:08x}")

        details.append(
            {
                "wrapper_callsite": f"0x{callsite:08x}",
                "output_destination": slot,
                "destination_class": "stack_local",
                "terminal_pointer_use": f"0x{terminal_use:08x}",
                "terminal_pointer_use_class": "indirect_call",
                "persistent_nonstack_store_before_terminal_or_kill": False,
                "pointer_value_copy_before_terminal_or_kill": False,
                "overwrite_kill": None if overwrite is None else f"0x{overwrite:08x}",
            }
        )

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_bytes_are_machine_authority": True,
            "retail_executable_sha256": digest,
            "retail_file_size": exe.stat().st_size,
            "disassembler": "GNU objdump -d -Mintel",
        },
        "upstream_contracts": [
            "SHIFT.P1B.HDVehicle4330GetProcAddressStaticResolutionSurface/1",
            "SHIFT.P1B.HDVehicle4330GetProcAddressWrapperStaticEntrySurface/1",
        ],
        "surface": {
            "generic_wrapper": f"0x{WRAPPER:08x}",
            "direct_wrapper_callsite_count": len(ROWS),
            "stack_local_output_destination_count": len(ROWS),
            "nonstack_output_destination_count": 0,
            "unique_terminal_indirect_call_count": len(unique_indirect_calls),
            "resolved_pointer_value_copy_count_before_terminal_or_kill": 0,
            "resolved_pointer_persistent_nonstack_store_count": 0,
            "rows": details,
        },
        "adjudication": {
            "generic_wrapper_direct_output_persistence_subset_complete": True,
            "generic_wrapper_direct_outputs_stack_local_only": True,
            "generic_wrapper_direct_output_persistent_store_found": False,
            "generic_wrapper_runtime_indirect_entry_ruled_out": False,
            "dynamic_getprocaddress_resolution_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "runtime_patching_or_generated_code_ruled_out": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": EXPECTED_PROVIDER_COUNT,
        },
        "limits": [
            "This closes persistence only for the 12 direct machine callers of the generic GetProcAddress wrapper.",
            "Direct GetProcAddress callsites outside the wrapper, register-loaded GetProcAddress calls, runtime/indirect wrapper entry, external proc addresses and unrelated runtime-populated function-pointer stores remain open.",
            "A stack-local resolved pointer may be invoked transiently; this contract proves only that these direct wrapper outputs are not copied into persistent non-stack storage before their terminal use or overwrite.",
        ],
        "next_step": "Classify direct-IAT/register-loaded GetProcAddress result stores and their downstream indirect calls, then compose bounded runtime-populated function-pointer storage coverage.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("exe", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    data = build(args.exe)
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
