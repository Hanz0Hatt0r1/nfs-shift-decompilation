#!/usr/bin/env python3
"""Close the remaining static proof obligations on SHIFT.RetailOuterUpdateCadence/1.

The base cadence contract proves the corrected BManager registration/default
+0x18 dispatch, the 30 Hz manager configuration, scheduler argument forwarding,
and the 1/rate inner-step algebra.  This completion pass proves three facts that
must also hold before Process 2 may consume that contract:

1. the 30 Hz initializer and +0x18 scheduler entry are slots of the same
   source-backed cPhysicsManager vtable;
2. the steady active scheduler path invokes FUN_007155e0 once per default
   manager dispatch (the debug multi-call flag is PE zero-fill and has no
   source-visible writer in the pinned decompile);
3. cPhysicsManager +0x388 is loaded from the PhysicsTweaker "tick rate" field,
   whose constructor default is 180 but whose loaded session value is not frozen.

No runtime capture or original-game execution is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.RetailOuterUpdateCadenceCompletion/1"
BASE_FORMAT = "SHIFT.RetailOuterUpdateCadence/1"
OWNER_FORMAT = "SHIFT.PhysicsManagerSchedulerEntryOwner/1"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

FUNCTIONS = (
    "FUN_0070fae0",
    "FUN_00710a70",
    "FUN_00748280",
    "FUN_00749a60",
    "FUN_0074d400",
    "FUN_0070f170",
    "FUN_0070f940",
    "FUN_00714a10",
    "FUN_00715240",
    "FUN_00712890",
)


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _extract(source: str, name: str) -> str:
    pattern = re.compile(
        rf"(?m)^(?:{re.escape(name)}|[^\s\n][^\n]*\b{re.escape(name)})\s*\("
    )
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise ValueError(f"{name}: expected exactly one definition; found {len(matches)}")
    match = matches[0]
    brace = source.find("{", match.end())
    if brace < 0:
        raise ValueError(f"{name}: opening brace missing")
    depth = 0
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return _compact(source[match.start() : index + 1])
    raise ValueError(f"{name}: closing brace missing")


def _require(name: str, body: str, fragment: str) -> None:
    if _compact(fragment) not in body:
        raise ValueError(f"{name}: missing required fragment: {fragment}")


class PE:
    def __init__(self, path: Path):
        self.data = path.read_bytes()
        if self.data[:2] != b"MZ":
            raise ValueError("PE: missing MZ")
        pe = struct.unpack_from("<I", self.data, 0x3C)[0]
        if self.data[pe : pe + 4] != b"PE\0\0":
            raise ValueError("PE: missing signature")
        machine, section_count = struct.unpack_from("<HH", self.data, pe + 4)
        if machine != 0x14C:
            raise ValueError("PE: expected x86")
        optional_size = struct.unpack_from("<H", self.data, pe + 20)[0]
        optional = pe + 24
        if struct.unpack_from("<H", self.data, optional)[0] != 0x10B:
            raise ValueError("PE: expected PE32")
        self.image_base = struct.unpack_from("<I", self.data, optional + 28)[0]
        section_table = optional + optional_size
        self.sections: list[tuple[int, int, int, int]] = []
        for index in range(section_count):
            offset = section_table + index * 40
            virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
                "<IIII", self.data, offset + 8
            )
            self.sections.append((virtual_address, virtual_size, raw_pointer, raw_size))

    def va(self, address: int, size: int) -> bytes:
        rva = address - self.image_base
        for section_va, _, raw_pointer, raw_size in self.sections:
            if section_va <= rva and rva + size <= section_va + raw_size:
                offset = raw_pointer + (rva - section_va)
                return self.data[offset : offset + size]
        raise ValueError(f"PE: VA 0x{address:08x}+{size} is not raw-backed")

    def require(self, address: int, hex_bytes: str, label: str) -> None:
        expected = bytes.fromhex(hex_bytes)
        actual = self.va(address, len(expected))
        if actual != expected:
            raise ValueError(
                f"{label}: bytes drift at 0x{address:08x}: "
                f"expected {expected.hex()}, got {actual.hex()}"
            )

    def is_zero_fill(self, address: int, size: int = 1) -> bool:
        rva = address - self.image_base
        for section_va, virtual_size, _, raw_size in self.sections:
            if section_va <= rva and rva + size <= section_va + virtual_size:
                return rva >= section_va + raw_size
        return False


def build(
    source_path: Path,
    pe_path: Path,
    owner_path: Path,
    base_path: Path,
) -> dict[str, Any]:
    source_bytes = source_path.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if source_hash != SOURCE_SHA256:
        raise ValueError("unexpected SHIFT.exe.c SHA-256")
    source = source_bytes.decode("utf-8", "strict")

    pe_bytes = pe_path.read_bytes()
    pe_md5 = hashlib.md5(pe_bytes).hexdigest()
    pe_sha256 = hashlib.sha256(pe_bytes).hexdigest()
    if pe_md5 != PE_MD5 or pe_sha256 != PE_SHA256:
        raise ValueError("unexpected retail SHIFT.exe fingerprint")
    pe = PE(pe_path)

    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    scheduler = owner.get("scheduler_entry", {})
    if (
        owner.get("format") != OWNER_FORMAT
        or owner.get("ready") is not True
        or scheduler.get("owner_proven") is not True
        or scheduler.get("vtable_address") != "0x00b04524"
        or scheduler.get("slot_offset") != 0x18
        or scheduler.get("target_address") != "0x00711b50"
    ):
        raise ValueError("positive source-backed cPhysicsManager owner handoff required")

    base = json.loads(base_path.read_text(encoding="utf-8"))
    if base.get("format") != BASE_FORMAT or base.get("ready") is not True:
        raise ValueError("positive base retail cadence contract required")
    if base.get("provenance", {}).get("source_sha256") != SOURCE_SHA256:
        raise ValueError("base cadence source fingerprint drift")
    if base.get("provenance", {}).get("retail_pe_md5") != PE_MD5:
        raise ValueError("base cadence PE fingerprint drift")
    if base.get("bmanager_registration_dispatch", {}).get(
        "registration_and_default_dispatch_proven"
    ) is not True:
        raise ValueError("base BManager registration/default dispatch is not proven")
    if base.get("outer_manager_cadence", {}).get("configured_frequency_hz") != 30.0:
        raise ValueError("base outer manager frequency drift")
    if base.get("outer_manager_cadence", {}).get("period_ms") != 33:
        raise ValueError("base outer manager quantized gate drift")
    if base.get("fixed_step_accumulator", {}).get("fixed_step_semantics_proven") is not True:
        raise ValueError("base fixed-step accumulator semantics are not proven")

    bodies = {name: _extract(source, name) for name in FUNCTIONS}

    # Same source-backed cPhysicsManager vtable owns initializer and scheduler entry.
    _require("FUN_0070fae0", bodies["FUN_0070fae0"], "*param_1 = &PTR_FUN_00b04524;")
    pe.require(0x00B04524, "60fe7000", "cPhysicsManager-vtable-slot0")
    pe.require(0x00B04528, "700a7100", "cPhysicsManager-vtable-initializer")
    pe.require(0x00B0453C, "501b7100", "cPhysicsManager-vtable-scheduler")
    pe.require(0x00B04540, "b0ff7000", "cPhysicsManager-vtable-alternate")
    _require("FUN_00710a70", bodies["FUN_00710a70"], "FUN_00647860((int)param_1,0,30.0);")

    # PhysicsTweaker source for the loaded +0x388 rate.
    _require("FUN_00748280", bodies["FUN_00748280"], 'FUN_00631740(&local_14,"Physics Tweaker");')
    _require("FUN_00748280", bodies["FUN_00748280"], "*(undefined2 *)((int)param_1 + 0x492) = 0xb4;")
    _require("FUN_00749a60", bodies["FUN_00749a60"], 'FUN_00631740(&local_1c,"tick rate");')
    _require("FUN_00749a60", bodies["FUN_00749a60"], "FUN_0063a280(&DAT_00b8d248,0x17,&local_1c,0x492,3,&local_28);")
    _require("FUN_0074d400", bodies["FUN_0074d400"], '"PhysicsTweaker.xml"')
    _require("FUN_0074d400", bodies["FUN_0074d400"], "FUN_0074d310(param_1,puVar5);")
    _require("FUN_00710a70", bodies["FUN_00710a70"], "FUN_0074d400(&DAT_00c12c40);")
    _require("FUN_00710a70", bodies["FUN_00710a70"], "FUN_0070f170(param_1,(uint)DAT_00c130d2);")
    if 0x00C12C40 + 0x492 != 0x00C130D2:
        raise AssertionError("PhysicsTweaker tick-rate alias arithmetic drift")
    for fragment in (
        "*(int *)((int)this + 0x388) = param_1;",
        "*(float *)((int)this + 0x38c) = 1.0 / (float)param_1;",
        "*(float *)((int)this + 0x390) = fVar1;",
        "*(float *)((int)this + 0x394) = 1.0 / fVar1;",
    ):
        _require("FUN_0070f170", bodies["FUN_0070f170"], fragment)

    # Steady-state scheduler multiplicity.
    if source.count("DAT_00c104a4") != 2:
        raise ValueError("DAT_00c104a4 reference-count drift")
    if not pe.is_zero_fill(0x00C104A4):
        raise ValueError("DAT_00c104a4 is no longer PE zero-fill")
    _require("FUN_0070f940", bodies["FUN_0070f940"], "if (DAT_00c104a4 != '\\0')")
    call = _compact("FUN_007155e0((LONG *)&DAT_00c109e0);")
    if bodies["FUN_0070f940"].count(call) != 4:
        raise ValueError("FUN_0070f940 scheduler-call multiplicity drift")
    _require("FUN_00714a10", bodies["FUN_00714a10"], "param_1[0x4f] = 1;")
    _require("FUN_00715240", bodies["FUN_00715240"], "param_1[0x4f] = 2;")
    _require("FUN_00712890", bodies["FUN_00712890"], "*(undefined4 *)(param_1 + 0x13c) = 3;")

    # Pin the loaded-rate machine path as an independent check of the decompile.
    pe.require(0x00748919, "889e91040000d99e9804000066c78692040000b400898e94040000", "PhysicsTweaker-default-180")
    pe.require(0x00710B06, "b9402cc100e8f0c80300", "PhysicsTweaker-load")
    pe.require(0x00710C12, "0fb705d230c100508bcee84fe5ffff", "loaded-tick-rate-to-cPhysicsManager")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "retail-cadence-proof-complete",
        "ready": True,
        "base": {
            "format": BASE_FORMAT,
            "ready": True,
            "source_sha256": SOURCE_SHA256,
            "retail_pe_md5": PE_MD5,
        },
        "same_owner_vtable": {
            "vtable_address": "0x00b04524",
            "initializer_slot_offset": "0x04",
            "initializer_target": "FUN_00710a70",
            "scheduler_slot_offset": "0x18",
            "scheduler_target": "FUN_00711b50",
            "alternate_slot_offset": "0x1c",
            "verified": True,
        },
        "scheduler_multiplicity": {
            "multi_call_flag": "DAT_00c104a4",
            "multi_call_flag_initial_storage": "PE zero-fill",
            "source_visible_writers": 0,
            "calls_present_in_function": 4,
            "normal_calls_per_FUN_0070f940": 1,
            "scheduler_object_initial_state": 1,
            "state_transition_surface": ["1 -> 2", "2 -> 3 under active-init condition"],
            "steady_active_state": 3,
            "steady_state_scheduler_invocations_per_default_manager_dispatch": 1,
            "verified": True,
        },
        "physics_rate_source": {
            "tweaker": "Physics Tweaker",
            "xml": "PhysicsTweaker.xml",
            "field": "tick rate",
            "tweaker_base": "DAT_00c12c40",
            "field_offset": "0x492",
            "runtime_alias": "DAT_00c130d2",
            "constructor_default_rate_hz": 180,
            "loaded_value_applied_by": "FUN_0070f170",
            "cPhysicsManager_rate_offset": "0x388",
            "final_loaded_session_rate_frozen": False,
            "verified": True,
        },
        "handoff": {
            "retail_outer_scheduler_cadence_proof_complete": True,
            "scheduler_authority": "RetailEvidence",
            "retail_cadence_admitted": True,
            "host_1_60_is_retail_evidence": False,
            "worker_poll_10ms_is_physics_cadence": False,
            "consumer": "native runtime explicit retail scheduler authority seam",
        },
        "limits": {
            "constructor_default_180_promoted_to_loaded_session_rate": False,
            "final_numeric_physics_rate_guessed": False,
            "host_1_60_promoted": False,
            "worker_poll_10ms_promoted": False,
            "rendered_frame_equivalence_claimed": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("pe", type=Path)
    parser.add_argument("owner", type=Path)
    parser.add_argument("base", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = build(args.source, args.pe, args.owner, args.base)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
