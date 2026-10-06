#!/usr/bin/env python3
"""Build the positive retail outer-update cadence handoff from pinned retail source + PE.

This builder joins the pinned full Ghidra decompile with exact raw PE bytes. It
proves the source-backed cPhysicsManager identity, default BManager dispatch,
30 Hz manager initialization, scheduler multiplicity/state, scheduler argument,
and inner fixed-step accumulator algebra. It never executes the game and never
promotes host 1/60 or the worker's 10 ms poll sleep to retail physics cadence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.RetailOuterUpdateCadence/1"
OWNER_FORMAT = "SHIFT.PhysicsManagerSchedulerEntryOwner/1"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

FUNCS = (
    "FUN_0070fe90", "FUN_0041903c", "FUN_0070fe99", "FUN_0070fae0",
    "FUN_0065bd70", "FUN_0065bf80", "FUN_00647d80", "FUN_00d36000",
    "FUN_006485b0", "FUN_00662600", "FUN_006626a0", "FUN_0065b8b0",
    "FUN_00647ef0", "FUN_00662880", "FUN_00710a70", "FUN_00647860",
    "FUN_0070f170", "FUN_00714a10", "FUN_00715240", "FUN_00712890",
    "FUN_00710780", "FUN_007117e0", "FUN_0070f940", "FUN_007155e0",
    "FUN_0048ed52", "FUN_007155e9", "FUN_00715380", "FUN_00712450",
    "FUN_00713050",
)


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def extract(source: str, name: str) -> dict[str, Any]:
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
    end = None
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end is None:
        raise ValueError(f"{name}: closing brace missing")
    body = source[match.start():end]
    return {
        "body": body,
        "compact": compact(body),
        "line": source.count("\n", 0, match.start()) + 1,
    }


def require(name: str, body: str, fragment: str) -> None:
    if compact(fragment) not in body:
        raise ValueError(f"{name}: missing required fragment: {fragment}")


def require_order(name: str, body: str, fragments: Iterable[str]) -> None:
    cursor = 0
    for fragment in fragments:
        token = compact(fragment)
        found = body.find(token, cursor)
        if found < 0:
            raise ValueError(f"{name}: missing ordered fragment: {fragment}")
        cursor = found + len(token)


class PE:
    def __init__(self, path: Path):
        self.path = path
        self.data = path.read_bytes()
        if self.data[:2] != b"MZ":
            raise ValueError("PE: missing MZ")
        pe = struct.unpack_from("<I", self.data, 0x3C)[0]
        if self.data[pe:pe + 4] != b"PE\0\0":
            raise ValueError("PE: missing signature")
        machine, section_count = struct.unpack_from("<HH", self.data, pe + 4)
        if machine != 0x14C:
            raise ValueError(f"PE: expected x86 machine, got 0x{machine:x}")
        optional_size = struct.unpack_from("<H", self.data, pe + 20)[0]
        optional = pe + 24
        if struct.unpack_from("<H", self.data, optional)[0] != 0x10B:
            raise ValueError("PE: expected PE32")
        self.image_base = struct.unpack_from("<I", self.data, optional + 28)[0]
        section_table = optional + optional_size
        self.sections = []
        for index in range(section_count):
            offset = section_table + index * 40
            name = self.data[offset:offset + 8].rstrip(b"\0").decode("ascii", "replace")
            virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
                "<IIII", self.data, offset + 8
            )
            self.sections.append(
                (name, virtual_address, virtual_size, raw_pointer, raw_size)
            )

    def va(self, address: int, size: int) -> bytes:
        rva = address - self.image_base
        for _, section_va, _, raw_pointer, raw_size in self.sections:
            if section_va <= rva and rva + size <= section_va + raw_size:
                offset = raw_pointer + (rva - section_va)
                return self.data[offset:offset + size]
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
        for _, section_va, virtual_size, _, raw_size in self.sections:
            if section_va <= rva and rva + size <= section_va + virtual_size:
                return rva >= section_va + raw_size
        return False

    def f32(self, address: int) -> float:
        return struct.unpack("<f", self.va(address, 4))[0]

    def f64(self, address: int) -> float:
        return struct.unpack("<d", self.va(address, 8))[0]


def build(source_path: Path, pe_path: Path, owner_path: Path) -> dict[str, Any]:
    source_bytes = source_path.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if source_hash != SOURCE_SHA256:
        raise ValueError(
            f"unexpected SHIFT.exe.c SHA-256: expected {SOURCE_SHA256}, got {source_hash}"
        )
    source = source_bytes.decode("utf-8", "strict")

    pe_bytes = pe_path.read_bytes()
    pe_md5 = hashlib.md5(pe_bytes).hexdigest()
    pe_sha256 = hashlib.sha256(pe_bytes).hexdigest()
    if pe_md5 != PE_MD5:
        raise ValueError(f"unexpected SHIFT.exe MD5: expected {PE_MD5}, got {pe_md5}")
    if pe_sha256 != PE_SHA256:
        raise ValueError(
            f"unexpected SHIFT.exe SHA-256: expected {PE_SHA256}, got {pe_sha256}"
        )
    pe = PE(pe_path)

    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    if owner.get("format") != OWNER_FORMAT or owner.get("ready") is not True:
        raise ValueError("positive owner handoff required")
    scheduler_entry = owner.get("scheduler_entry", {})
    if (
        scheduler_entry.get("owner_proven") is not True
        or scheduler_entry.get("slot_offset") != 0x18
        or scheduler_entry.get("target_address") != "0x00711b50"
    ):
        raise ValueError("owner handoff scheduler slot drift")

    extracted = {name: extract(source, name) for name in FUNCS}
    bodies = {name: value["compact"] for name, value in extracted.items()}

    # Accessor -> singleton -> source-backed cPhysicsManager constructor alias.
    require("FUN_0070fe90", bodies["FUN_0070fe90"], "FUN_0041903c();")
    require("FUN_0041903c", bodies["FUN_0041903c"], "FUN_0070fe99();")
    require(
        "FUN_0070fe99", bodies["FUN_0070fe99"],
        "FUN_0070fae0((undefined4 *)&DAT_00c104e0);"
    )
    require("FUN_0070fe99", bodies["FUN_0070fe99"], "return &DAT_00c104e0;")
    require("FUN_0070fae0", bodies["FUN_0070fae0"], "*param_1 = &PTR_FUN_00b04524;")
    require(
        "FUN_0070fae0", bodies["FUN_0070fae0"],
        'FUN_00647820((int)param_1,"Physics Manager");'
    )
    require("FUN_0070fae0", bodies["FUN_0070fae0"], "FUN_0070f170(param_1,0xb4);")

    # BManager default mode and cPhysicsManager registration/list identity.
    require(
        "FUN_0065bf80", bodies["FUN_0065bf80"],
        "FUN_0065bd70((AptFrameStack *)&DAT_00bfb4a0);"
    )
    require(
        "FUN_0065bd70", bodies["FUN_0065bd70"],
        "param_1[0x529] = (AptFrameStack)0x0;"
    )
    require(
        "FUN_0065bd70", bodies["FUN_0065bd70"],
        'FUN_0064f570((undefined4 *)(param_1 + 0x700),"BManager Tick",\'\\0\',\'\\x01\');'
    )
    require("FUN_00647d80", bodies["FUN_00647d80"], "if (puVar1[0x529] != '\\0')")
    require("FUN_00647d80", bodies["FUN_00647d80"], "(**(code **)(*param_1 + 0x1c))();")
    require("FUN_00647d80", bodies["FUN_00647d80"], "(**(code **)(*param_1 + 0x18))();")
    require_order(
        "FUN_00d36000", bodies["FUN_00d36000"],
        ["pvVar3 = (void *)FUN_0070fe90();", "FUN_006485b0(pvVar3,iVar7);"]
    )
    require(
        "FUN_006485b0", bodies["FUN_006485b0"],
        "piVar4 = (int *)FUN_00662600(iVar2,(int)this);"
    )
    require("FUN_00662600", bodies["FUN_00662600"], "piVar1 = (int *)(param_1 + 0x58);")
    require(
        "FUN_00662600", bodies["FUN_00662600"],
        "if (param_2 == *(int *)(iVar3 + 0xc))"
    )
    require("FUN_00662600", bodies["FUN_00662600"], "FUN_004f5e60(piVar1,param_2);")
    require_order(
        "FUN_006626a0", bodies["FUN_006626a0"],
        [
            "if (*(int *)(param_1 + 0x98) == 6)",
            "piVar7 = (int *)(param_1 + 0x58);",
            "FUN_0065b8b0(piVar7);",
        ],
    )
    require("FUN_0065b8b0", bodies["FUN_0065b8b0"], "piVar2 = *(int **)(iVar4 + 0xc);")
    require("FUN_0065b8b0", bodies["FUN_0065b8b0"], "FUN_00647ef0(piVar2);")
    require("FUN_00662880", bodies["FUN_00662880"], "while (cVar4 == '\\0')")
    require_order(
        "FUN_00662880", bodies["FUN_00662880"],
        ["FUN_006626a0((int)param_1);", "FUN_00649780(10,1);", "cVar4 = (char)param_1[4];"],
    )

    # Bind the 30 Hz initializer and +0x18 scheduler to this exact vtable.
    pe.require(0x00B04524, "60fe7000", "cPhysicsManager-vtable-slot0")
    pe.require(0x00B04528, "700a7100", "cPhysicsManager-vtable-slot1-initializer")
    pe.require(0x00B0453C, "501b7100", "cPhysicsManager-vtable-slot6-scheduler")
    pe.require(0x00B04540, "b0ff7000", "cPhysicsManager-vtable-slot7-alternate")

    # Per-manager cadence configuration and timing gate.
    require("FUN_00710a70", bodies["FUN_00710a70"], "FUN_00647860((int)param_1,0,30.0);")
    for fragment in (
        "*(undefined1 *)(param_1 + 0xdc) = 1;",
        "*(double *)(param_1 + 0xe0) = (double)param_3;",
        "*(undefined1 *)(param_1 + 0xf8) = param_2;",
        "local_c = (undefined4)(longlong)ROUND(1000.0 / param_3);",
        "*(undefined4 *)(param_1 + 0xe8) = local_c;",
    ):
        require("FUN_00647860", bodies["FUN_00647860"], fragment)
    require_order(
        "FUN_00647ef0", bodies["FUN_00647ef0"],
        [
            "if ((char)param_1[0x3e] == '\\0')",
            "uVar8 = thunk_FUN_004a5020(piVar1,iVar7);",
            "dVar4 = dVar2 + *(double *)(param_1 + 0x3c);",
            "dVar3 = (double)param_1[0x3a];",
            "if (dVar3 - *(double *)(param_1 + 0x34) < dVar4 !=",
            "local_8 = FUN_00647d80(param_1);",
            "*(double *)(param_1 + 0x3c) = dVar4 - dVar2;",
        ],
    )

    # +0x388 writer establishes rate domain and all reciprocal relationships.
    for fragment in (
        "*(int *)((int)this + 0x388) = param_1;",
        "*(float *)((int)this + 0x38c) = 1.0 / (float)param_1;",
        "fVar1 = (float)param_1 / 30.0;",
        "*(float *)((int)this + 0x390) = fVar1;",
        "*(float *)((int)this + 0x394) = 1.0 / fVar1;",
    ):
        require("FUN_0070f170", bodies["FUN_0070f170"], fragment)

    # Multiplicity/state proof: DAT_00c104a4 has one declaration + one read,
    # resides in zero-filled PE storage, and therefore selects the one-call path.
    if source.count("DAT_00c104a4") != 2:
        raise ValueError("DAT_00c104a4 reference-count drift in pinned source")
    if not pe.is_zero_fill(0x00C104A4, 1):
        raise ValueError("DAT_00c104a4 is no longer zero-filled PE storage")
    require("FUN_0070f940", bodies["FUN_0070f940"], "if (DAT_00c104a4 != '\\0')")
    require("FUN_0070f940", bodies["FUN_0070f940"], "FUN_007155e0((LONG *)&DAT_00c109e0);")
    require("FUN_00714a10", bodies["FUN_00714a10"], "param_1[0x4f] = 1;")
    require("FUN_00715240", bodies["FUN_00715240"], "param_1[0x4f] = 2;")
    require("FUN_00712890", bodies["FUN_00712890"], "*(undefined4 *)(param_1 + 0x13c) = 3;")

    # Scheduler argument and fixed-step accumulator semantics.
    require("FUN_00710780", bodies["FUN_00710780"], "local_8 = 1.0;")
    require(
        "FUN_00710780", bodies["FUN_00710780"],
        "return (float10)(30.0 / (float)*(int *)(iVar1 + 0x388));"
    )
    require("FUN_00710780", bodies["FUN_00710780"], "return (float10)0.5;")
    require("FUN_00710780", bodies["FUN_00710780"], "local_8 = 0.0;")
    require("FUN_007117e0", bodies["FUN_007117e0"], "FUN_00710780();")
    require("FUN_007117e0", bodies["FUN_007117e0"], "cVar3 = FUN_0070f940();")
    require("FUN_0070f940", bodies["FUN_0070f940"], "FUN_007155e0((LONG *)&DAT_00c109e0);")
    require("FUN_007155e0", bodies["FUN_007155e0"], "FUN_0048ed52(param_1);")
    require("FUN_0048ed52", bodies["FUN_0048ed52"], "FUN_007155e9(param_1);")
    require(
        "FUN_007155e9", bodies["FUN_007155e9"],
        "uVar1 = FUN_00715380(param_1,*(float *)(unaff_EBP + 8));"
    )
    require("FUN_00715380", bodies["FUN_00715380"], "FUN_00712450(this,param_1);")
    require("FUN_00715380", bodies["FUN_00715380"], "FUN_00713050(this,piVar2);")
    require(
        "FUN_00712450", bodies["FUN_00712450"],
        "*(double *)((int)this + 0x348) = (double)(param_1 * 0.033333335 + (float)*(double *)((int)this + 0x348));"
    )
    for fragment in (
        "iVar6 = FUN_0070fe90();",
        "dVar3 = (double)*(int *)(iVar6 + 0x388);",
        "local_14 = (uint)(longlong)ROUND(dVar3 * *(double *)((int)this + 0x348) + 0.5);",
        "dVar4 = 1.0 / dVar3;",
        "*(double *)((int)this + 0x348) = *(double *)((int)this + 0x348) - dVar2 / dVar3;",
    ):
        require("FUN_00713050", bodies["FUN_00713050"], fragment)

    # Exact PE byte anchors close decompiler calling-convention gaps.
    signatures = {
        "bmanager_dispatch_selector": (
            0x00647D80,
            "568bf1e8f841010080b829050000008b068bce5e74058b501cffe28b5018ffe2",
        ),
        "registration_accessor_call": (0x00D3604B, "8b0e8bc48908e83a9e9dff"),
        "registration_return_to_this": (0x00D36068, "8bc8e8412591ff"),
        "controller_resolve_and_core_add": (
            0x006485B5,
            "8bf9807f3400750832c05f5e5dc20400518b4d088bc48908e8ae3901008bc8e8673201008bf085f674de8bcee80acb000084c074198bcee81fcb000084c0750e89b750010000b0015f5e5dc204008bd78bcee8f49f0100",
        ),
        "controller_list_insert": (0x00662605, "8bda85db744c56578d7958"),
        "active_controller_list_consumer": (
            0x006626A6, "8bf183be98000000065775108d465850e8c598ffff8bc8e8ee91ffff"
        ),
        "manager_list_to_timing_gate": (
            0x0065B8E0,
            "8b4e0c80793400741b80793500741580792900740fc6814002000001e8efc5feff",
        ),
        "timing_gate_to_dispatch": (
            0x00647FA2,
            "8b86e8000000dd9ec80000008bce8986d8000000e885feffff8bcee8befdffff",
        ),
        "rate_scale_to_f940": (
            0x00711951,
            "e82aeeffffd95dfc51dd05400bc1008bcedd5df0d945fcd91c24e8d0dfffff",
        ),
        "state_dispatch_to_scheduler": (0x0048ED52, "8b813c010000e98c682800"),
        "scheduler_push_to_715380": (0x007155F6, "83e8017522d9450851d91c24e879fdffff"),
        "accumulator_update": (
            0x00712453,
            "d94508d9c0dc8140030000dd9940030000dc0de845b000dc8148030000dd9948030000",
        ),
        "rate_read_and_substep_reciprocal": (
            0x0071307C,
            "e80fceffffdb8088030000d97dfa33c90fb745fadd55d8d9c00d000c0000dc8e480300008945f4dc05209aaa00d96df4df7df08b7df085ff897df4d96dfa894df8dd86600100000f8640010000d9e853def2",
        ),
    }
    for label, (address, hex_bytes) in signatures.items():
        pe.require(address, hex_bytes, label)

    one_thirtieth = pe.f64(0x00B045E8)
    thirty = pe.f64(0x00AB2000)
    half = pe.f64(0x00AA9A20)
    init_thirty = pe.f32(0x00AAC2C8)
    if not (
        abs(one_thirtieth - (1.0 / 30.0)) < 5e-9
        and thirty == 30.0
        and half == 0.5
        and init_thirty == 30.0
    ):
        raise ValueError("retail scheduler constants drift")

    gate_ms = round(1000.0 / 30.0)
    return {
        "format": FORMAT,
        "version": 1,
        "status": "retail-cadence-admitted",
        "ready": True,
        "blocker": "retail-outer-update-scheduler-cadence-admission",
        "provenance": {
            "source": "SHIFT.exe.c",
            "source_sha256": source_hash,
            "retail_program": "SHIFT.exe",
            "retail_pe_md5": pe_md5,
            "retail_pe_sha256": pe_sha256,
            "source_function_lines": {
                name: extracted[name]["line"] for name in FUNCS
            },
            "machine_byte_anchors": {
                label: {"address": f"0x{address:08x}", "bytes": hex_bytes}
                for label, (address, hex_bytes) in signatures.items()
            },
            "vtable_anchors": {
                "vtable": "0x00b04524",
                "initializer_slot_plus_0x04": "FUN_00710a70",
                "scheduler_slot_plus_0x18": "FUN_00711b50",
                "alternate_slot_plus_0x1c": "FUN_0070ffb0",
            },
        },
        "owner_handoff": {
            "format": OWNER_FORMAT,
            "owner": owner.get("owner"),
            "slot_offset": 0x18,
            "target": "FUN_00711b50",
            "verified": True,
        },
        "bmanager_registration_dispatch": {
            "singleton": "FUN_0065bf80",
            "default_mode_flag_offset": "0x529",
            "default_mode_flag_value": 0,
            "registered_manager": "FUN_0070fe90() -> DAT_00c104e0 source-backed cPhysicsManager singleton",
            "controller_list_offset": "0x58",
            "active_controller_state": 6,
            "worker_loop": "FUN_00662880",
            "worker_poll_sleep_ms": 10,
            "poll_sleep_is_physics_cadence": False,
            "manager_timing_gate": "FUN_00647ef0",
            "dispatch_selector": "FUN_00647d80",
            "default_dispatch_slot_offset": "0x18",
            "default_dispatch_target": "FUN_00711b50",
            "alternate_mode_slot_offset": "0x1c",
            "alternate_mode_target": scheduler_entry.get("neighbor_release_target"),
            "scope": "default BManager mode (+0x529 == 0); alternate mode remains separate",
            "accessor_alias_to_cPhysicsManager_proven": True,
            "registration_and_default_dispatch_proven": True,
        },
        "outer_manager_cadence": {
            "initializer": "FUN_00710a70",
            "initializer_bound_to_cPhysicsManager_vtable": True,
            "configuration_function": "FUN_00647860",
            "configured_frequency_hz": 30.0,
            "period_expression": "ROUND(1000.0 / 30.0)",
            "period_ms": gate_ms,
            "period_field_offset": "0xe8",
            "enabled_field_offset": "0xdc",
            "enabled_value": 1,
            "mode_field_offset": "0xf8",
            "mode_value": 0,
            "timing_gate_consumes_period_field": True,
            "nominal_hz_and_ms_gate_are_distinct": True,
        },
        "physics_rate_field": {
            "writer": "FUN_0070f170",
            "rate_offset": "0x388",
            "reciprocal_offset": "0x38c",
            "rate_over_30_offset": "0x390",
            "thirty_over_rate_offset": "0x394",
            "relationships": [
                "+0x388 = rate",
                "+0x38c = 1/rate",
                "+0x390 = rate/30",
                "+0x394 = 30/rate",
            ],
            "rate_domain_proven": True,
            "final_numeric_rate_not_frozen": True,
        },
        "scheduler_multiplicity": {
            "multi_call_flag": "DAT_00c104a4",
            "multi_call_flag_initial_storage": "PE zero-fill",
            "source_visible_writers": 0,
            "normal_calls_to_FUN_007155e0_per_FUN_0070f940": 1,
            "scheduler_object_initial_state": 1,
            "startup_state_transition": "1 -> 2 -> 3",
            "steady_active_state": 3,
            "steady_state_scheduler_invocations_per_manager_dispatch": 1,
        },
        "scheduler_argument": {
            "producer": "FUN_00710780",
            "normal_mode_scale": 1.0,
            "mode_2_scale_expression": "30.0/rate",
            "mode_3_scale": 0.5,
            "paused_scale": 0.0,
            "machine_forwarding_path": [
                "FUN_007117e0", "FUN_0070f940", "FUN_007155e0",
                "FUN_0048ed52", "FUN_007155e9", "FUN_00715380",
            ],
            "active_scheduler_state_value": 3,
            "state_dispatch_field_offset": "0x13c",
            "producer_to_FUN_00715380_param1_proven": True,
        },
        "fixed_step_accumulator": {
            "accumulator_offset": "0x348",
            "normal_outer_increment_seconds": one_thirtieth,
            "increment_expression": "scale * 0.03333333507180214",
            "normal_scale_increment_is_one_thirtieth": True,
            "single_step_scale_expression": "30/rate",
            "single_step_accumulator_increment_expression": "(30/rate)*(1/30) = 1/rate",
            "substep_count_expression": "ROUND(rate * accumulator + 0.5)",
            "substep_dt_expression": "1.0/rate",
            "post_step_accumulator_expression": "accumulator - substep_count/rate",
            "fixed_step_semantics_proven": True,
        },
        "adjudication": {
            "FUN_0070fe90_return_aliases_source_backed_cPhysicsManager_instance": True,
            "cPhysicsManager_registered_in_active_controller_list": True,
            "active_controller_list_reaches_manager_timing_gate": True,
            "default_manager_dispatch_reaches_source_backed_cPhysicsManager_slot_plus_0x18": True,
            "cPhysicsManager_initializer_slot_plus_0x04_reaches_30hz_configuration": True,
            "retail_outer_manager_nominal_frequency_30hz_proven": True,
            "retail_outer_manager_quantized_gate_33ms_proven": True,
            "one_steady_scheduler_invocation_per_default_manager_dispatch_proven": True,
            "scheduler_argument_value_proven": True,
            "physics_rate_field_domain_and_reciprocal_proven": True,
            "inner_fixed_step_1_over_rate_proven": True,
            "retail_cadence_admitted": True,
        },
        "runtime_handoff": {
            "scheduler_authority": "RetailEvidence",
            "retail_cadence_admitted": True,
            "outer_schedule": {
                "nominal_frequency_hz": 30.0,
                "gate_period_ms": gate_ms,
                "default_mode_required": True,
                "steady_scheduler_invocations_per_dispatch": 1,
            },
            "simulation_quantum": {
                "normal_outer_increment_seconds": one_thirtieth,
                "inner_substep_seconds": "1/rate_source",
            },
            "must_not_substitute_host_1_60": True,
            "must_not_treat_worker_poll_10ms_as_physics_cadence": True,
            "consumer": "native runtime explicit retail scheduler authority seam",
        },
        "limits": {
            "host_1_60_promoted": False,
            "worker_poll_10ms_promoted": False,
            "rendered_frame_equivalence_claimed": False,
            "alternate_BManager_mode_admitted": False,
            "final_numeric_physics_rate_guessed": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("pe", type=Path)
    parser.add_argument("owner", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = build(args.source, args.pe, args.owner)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
