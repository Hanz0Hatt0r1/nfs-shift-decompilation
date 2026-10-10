#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, re, subprocess
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330GetProcAddressDirectResultLineage/1"
SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SIZE = 8_801_792
IAT = 0x00AA62FC
PROVIDER_COUNT = 7

ROWS = [
    (0x0061B684, "transient_immediate_call"),
    (0x00634046, "transient_register_call"),
    (0x007D655A, "bounded_return_helper"),
    (0x009074A0, "transient_immediate_call"),
    (0x00909DB9, "transient_immediate_call"),
    (0x0090AA7B, "transient_encodepointer_call"),
    (0x0090AAF2, "transient_decodepointer_call"),
    (0x00918A26, "persistent_encoded_global"),
    (0x0093DD43, "generic_wrapper_upstream_closed"),
    (0x009506B9, "persistent_global"),
    (0x00A61A7C, "transient_register_call"),
    (0x00A9AB1A, "persistent_global"),
]


def digest(path: Path) -> str:
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    if path.stat().st_size != SIZE or h != SHA256:
        raise ValueError("retail authority drift")
    return h


def disasm(path: Path):
    text = subprocess.check_output(["objdump", "-d", "-Mintel", str(path)], text=True, errors="replace")
    out = []
    rx = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*\t(.*)$")
    for line in text.splitlines():
        m = rx.match(line)
        if m:
            out.append((int(m.group(1), 16), m.group(2).strip()))
    return out


def build(exe: Path) -> dict:
    h = digest(exe)
    ins = disasm(exe)
    by = {a: t for a, t in ins}
    calls = [a for a, t in ins if t == f"call   DWORD PTR ds:0x{IAT:x}"]
    expected = [a for a, _ in ROWS]
    if calls != expected:
        raise ValueError(f"direct GetProcAddress callsite drift: {calls!r}")

    checks = {
        0x0061B692: "call   eax",
        0x00634064: "call   esi",
        0x009074AE: "call   eax",
        0x00909DC5: "call   eax",
        0x0090AA89: "call   eax",
        0x0090AB00: "call   eax",
        0x00918A3E: "mov    ds:0xc328c8,eax",
        0x009189DE: "push   DWORD PTR ds:0xc328c8",
        0x009506C1: "mov    ds:0xc593b0,eax",
        0x0095073B: "call   DWORD PTR ds:0xc593b0",
        0x00A61A8D: "call   ebp",
        0x00A9AB25: "mov    ds:0xcce308,eax",
    }
    for a, want in checks.items():
        if by.get(a) != want:
            raise ValueError(f"lineage instruction drift at 0x{a:08x}: {by.get(a)!r}")

    helper_calls = [a for a, t in ins if t == "call   0x7d6550"]
    if helper_calls != [0x007D6591, 0x007D65FB]:
        raise ValueError("GetEventHandler helper caller surface drift")
    if by.get(0x007D6607) != "call   eax":
        raise ValueError("GetEventHandler terminal call drift")

    refs = {}
    for va in (0x00C328C8, 0x00C593B0, 0x00CCE308):
        needle = f"{va:x}"
        refs[f"0x{va:08x}"] = [f"0x{a:08x}" for a, t in ins if needle in t]
    if len(refs["0x00c328c8"]) != 3 or len(refs["0x00c593b0"]) != 3 or len(refs["0x00cce308"]) != 2:
        raise ValueError("persistent global exact-reference surface drift")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {"platform":"PC retail 1.02","retail_executable_sha256":h,"retail_file_size":SIZE,"retail_bytes_are_machine_authority":True},
        "upstream_contracts": [
            "SHIFT.P1B.HDVehicle4330GetProcAddressStaticResolutionSurface/1",
            "SHIFT.P1B.HDVehicle4330GetProcAddressWrapperOutputPersistence/1",
        ],
        "surface": {
            "direct_iat_callsite_count": len(ROWS),
            "classified_direct_iat_result_lineage_count": len(ROWS),
            "persistent_global_lineage_count": 3,
            "persistent_exact_pointer_global_count": 2,
            "persistent_encoded_pointer_global_count": 1,
            "persistent_carrier_identity_hit_count": 0,
            "geteventhandler_helper_direct_caller_count": 2,
            "persistent_globals": [
                {"global":"0x00c328c8","identity":"InitializeCriticalSectionAndSpinCount","storage":"EncodePointer result","decode":"DecodePointer before call","exact_reference_count":3},
                {"global":"0x00c593b0","identity":"WMCreateSyncReader","module":"wmvcore.dll","terminal_call":"0x0095073b","exact_reference_count":3},
                {"global":"0x00cce308","identity":"ReadDirectoryChangesW","module":"kernel32.dll","exact_reference_count":2,"exact_direct_call_count":0},
            ],
            "direct_calls": [{"callsite":f"0x{a:08x}","classification":c} for a,c in ROWS],
            "persistent_global_exact_reference_addresses": refs,
        },
        "adjudication": {
            "direct_getprocaddress_result_lineage_subset_complete": True,
            "direct_getprocaddress_persistent_global_lineage_complete": True,
            "direct_getprocaddress_persistent_carrier_identity_found": False,
            "register_loaded_getprocaddress_result_lineage_complete": False,
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
            "external_provider_count": PROVIDER_COUNT,
        },
        "limits": [
            "This closes result lineage for the 12 direct calls to the imported GetProcAddress IAT slot only.",
            "The 86 register-loaded GetProcAddress calls, runtime/indirect resolver entry, external function pointers and unrelated runtime-populated tables remain open.",
            "Known persistent globals contain resolved external API identities, not P1B exact carrier identities."
        ],
        "next_step": "Classify the 86 register-loaded GetProcAddress result lineages and compose bounded resolver-populated function-pointer storage coverage."
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("exe",type=Path); ap.add_argument("--output",type=Path)
    a=ap.parse_args(); d=build(a.exe); s=json.dumps(d,indent=2,sort_keys=True)+"\n"
    if a.output: a.output.write_text(s,encoding="utf-8")
    else: print(s,end="")

if __name__ == "__main__": main()
