#!/usr/bin/env python3
"""Prove the static outer-Vehicle -> render-snapshot affine bridge.

This pass closes the physical producer/consumer path from the persistent outer
Vehicle transform storage into the SMS participant root affine. It deliberately
stops before equating that root with the canonical BMW VHF hierarchy root: the
vehicle-local +0x19c/+0x1a0/+0x1a4 delta still needs an independent VHF-owner /
resource-frame semantic join.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.OuterVehicleRenderSnapshotAffineBridge/1"
DB_FORMAT = "SHIFT.GhidraEvidenceDatabase/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
IMAGE_BASE = 0x00400000
SLOT_MANAGER = 0x00C109E0
SLOT_ARRAY = 0x00C10B20
SLOT_ARRAY_OFFSET = SLOT_ARRAY - SLOT_MANAGER
SLOT_STRIDE = 0x1FA0
SNAPSHOT_BASE = 0xD70
SNAPSHOT_STRIDE = 0x8F0
SNAPSHOT_SELECTOR = 0x1F50

TARGETS: dict[str, tuple[str, int, str, str]] = {
    "0x0042fc90": ("FUN_0042fc90", 111, "__thiscall", "21fbeebafacbc9c2b9f2d6b9987915413a27b5a8263e75f4b177861701b7f7ce"),
    "0x00432c00": ("FUN_00432c00", 36, "__fastcall", "6ee202414e407b405a0710dacf80832588ad4b26b428be86d3e6587663b7ec5d"),
    "0x00438da0": ("FUN_00438da0", 207, "__fastcall", "afaa139e050a75dffccf4960c8d928bf9203aa8db2ae2e2f804b40fdc420864b"),
    "0x0047f9e0": ("FUN_0047f9e0", 88, "__fastcall", "54a699f4317f2f49384c4aec5b8aaa89b811c8849143e02daa3b4f3f6c66ebaa"),
    "0x0047fa40": ("FUN_0047fa40", 325, "__thiscall", "667f0fad50ce7f1035d3d6b9cb5adcb78387577d1c855bce660170dbbb1c0a69"),
    "0x00480700": ("FUN_00480700", 92, "__fastcall", "f516ada7168e7af185891058c2e3405389a715a4933cc64acb624502f06f9f6d"),
    "0x00481e20": ("FUN_00481e20", 5913, "__thiscall", "37a722e4d69ffa88ae44b3b22d251fda6064674d8654da3506a3a298a3bb8c7d"),
    "0x00483540": ("FUN_00483540", 1274, "__fastcall", "42c29f6f4d6cec8e4e250cd1c8e6d7ac691a36fc3eb249e2a16670b02f3cd483"),
    "0x004848bc": ("FUN_004848bc", 1005, "__fastcall", "c42d1f68ccf1c7aa9cbb78c1eeb130d296b1c1503044f564a6f30f31c59ce149"),
    "0x00484cb0": ("FUN_00484cb0", 1504, "__fastcall", "476f82aa8cec6ecb56d3bd631be65573883c572f27fd7880d5eff4de1fb79250"),
    "0x00485290": ("FUN_00485290", 455, "__thiscall", "5181aa0fa2c9430b9988290eaa63fce6a3421081f6300a54e2b3f1309870ba6a"),
    "0x004a8c20": ("FUN_004a8c20", 198, "__fastcall", "1bdaa8f843f668bc4bec2d58d23a62c20efd23c737b78795f687a1cf67e72ece"),
    "0x004f8040": ("FUN_004f8040", 410, "__fastcall", "fd40776109cdd5c1d794081af739545f8792111069a0d8057169ab9734290dc1"),
    "0x0065a770": ("FUN_0065a770", 55, "__fastcall", "37687152c538cbe12bca25ffd0ffbf884eaa76bf188ed31f59f1747d152a4b8c"),
    "0x0070db00": ("FUN_0070db00", 61, "__thiscall", "a94a57a6bd66e069657d30c0bac22fffbd1b541949a53633a07c31ea8e986455"),
    "0x0070dcc0": ("FUN_0070dcc0", 14, "__fastcall", "7f3525e393a359ecd49e913bb3ac5c3874b396de6a2a21ac986d0345fe64483c"),
    "0x0070dccf": ("FUN_0070dccf", 46, "__fastcall", "e7160b683a9244ca7603c5ad1086f286e05c243d507097b03ad578674ed33951"),
    "0x0070f940": ("FUN_0070f940", 121, "__stdcall", "48bd01bd625d246ae87404f2f60669931934bd9d545d51d5b83bd38575a33222"),
    "0x007125b0": ("FUN_007125b0", 36, "__thiscall", "41a659e6fed25de5012e23030195c7a0e616942cc2723c6cbeae50a9861897cc"),
    "0x007125e0": ("FUN_007125e0", 185, "__fastcall", "d0d7c65693b7f3ef34ea399789518ef8c2aee61543bfe0473ddad54f4333adf0"),
    "0x00715240": ("FUN_00715240", 308, "__fastcall", "3fd2dd8c13015fa5e6e0e7e9927e093b1eb7538869da1bac90ab282b3c726afe"),
    "0x00721ea0": ("FUN_00721ea0", 28, "__thiscall", "eed563bd9c36a2ecfbd52143cfe214a3247e0a1ac2242a02e850097b52fa431b"),
    "0x007839a0": ("FUN_007839a0", 16, "__thiscall", "72ec51e272d3011adfc92593a05e534b5ce1edbb76d92073dcd8a640b71064de"),
    "0x007904f0": ("FUN_007904f0", 1473, "__thiscall", "d3803fce7a49ed2b2849592e3b6e37aaa1ac49177f037faa9e1345974ba3b378"),
    "0x007927c0": ("FUN_007927c0", 340, "__thiscall", "32b16c7d280c26335f9244b4cc7f8269995e4d2608724f8b0e5c4c0c41a75561"),
    "0x00795630": ("FUN_00795630", 376, "__thiscall", "b5c8c101ed24b8378d5d3c43c295292e80539a5de67c7161c1a341e9451b0a71"),
    "0x00795d60": ("FUN_00795d60", 8797, "__fastcall", "c587cae5d3d8f99afed40fe0c059c8c60bc9cc45d9ee644f5e90e2e1f5a8eb14"),
    "0x00798df0": ("FUN_00798df0", 1581, "__thiscall", "88904019443d1ea4edaf5a3ef40dd5abfe9e28109ab0b1f09296388f36026e16"),
    "0x007aef50": ("FUN_007aef50", 83, "__thiscall", "4f20a5f630bb6182c44699f505011f5a1958a87f4433400b7776ffd1dc740c51"),
    "0x007af6e0": ("FUN_007af6e0", 257, "__fastcall", "13dcda957d9c318f066755dd7b1154042e1709693425e92fb547a025827fd8e3"),
}

SOURCE_FACTS: dict[str, tuple[str, ...]] = {
    "FUN_0070f940": ("FUN_007155e0((LONG *)&DAT_00c109e0);",),
    "FUN_00715240": ("piVar5=(int *)(*piVar1 * 0x1fa0 + param_1[0x50]);", "FUN_007125e0(piVar5);"),
    "FUN_007125e0": ("*param_1=puVar2;", "FUN_00721ea0(puVar2,param_1);"),
    "FUN_00721ea0": ("*(undefined4 *)((int)this + 0x2608)=param_1;", "FUN_007839a0((void *)((int)this + 0x340),param_1);"),
    "FUN_007839a0": ("*(undefined4 *)((int)this + 0x848)=param_1;",),
    "FUN_00485290": ("*(undefined4 *)((int)this + 0x100)=param_1;", "FUN_00484cb0((int)this);"),
    "FUN_00484cb0": ("*(undefined4 *)(param_1 + 0xfc)=*(undefined4 *)(param_1 + 0x100);",),
    "FUN_0047f9e0": ("cVar1=FUN_0070dcc0(param_1 + 0x44);",),
    "FUN_0070dccf": ("(int)in_EAX * 0x1fa0 + DAT_00c10b20",),
    "FUN_0070db00": ("(*(uint *)((int)this + 0x1f50) & 1) * 0x8f0 + 0xd70", "FUN_00481e20"),
    "FUN_007927c0": ("*(undefined4 *)((int)this + 0x16c)=*param_2;", "FUN_007af6e0((float *)((int)this + 0x178));"),
    "FUN_00795630": (
        "(*(int *)(*(int *)((int)this + 0x848) + 0x1f50) - 1U & 1) * 0x8f0",
        "FUN_007904f0(this,pfVar5",
        "piVar1=(int *)(*(int *)((int)this + 0x848) + 0x1f50);",
        "*piVar1=*piVar1 + 1;",
    ),
    "FUN_007904f0": (
        "FUN_007aef50((void *)((int)this + 0x178),(float *)((int)this + 0x19c),local_28);",
        "FUN_007125b0(this,local_34);",
        "FUN_00432c00(&local_44,pfVar2,pfVar3);",
        "param_1[0x18a]=*(float *)((int)this + 0x178);",
        "FUN_0065a770((int)(param_1 + 0x18a));",
        "FUN_004f8040(&local_48,param_1 + 0x18a);",
    ),
    "FUN_007125b0": (
        "*param_1=*(undefined4 *)((int)this + 0x160);",
        "param_1[1]=*(undefined4 *)((int)this + 0x164);",
        "param_1[2]=*(undefined4 *)((int)this + 0x168);",
    ),
    "FUN_004848bc": ("FUN_00481e20(param_1 + 0x280,param_1 + 0x44);", "FUN_00483540((uint)param_1);"),
    "FUN_00483540": ("FUN_00438da0((float *)(param_1 + 0xa00),(float *)(param_1 + 0x1028));",),
    "FUN_00480700": (
        "FUN_0042fc90(local_50,(undefined4 *)(param_1 + 0x1028));",
        "local_20=*(undefined4 *)(param_1 + 0xa10);",
        "local_1c=*(undefined4 *)(param_1 + 0xa14);",
        "local_18=*(undefined4 *)(param_1 + 0xa18);",
        "FUN_004a8c20(param_1 + 0x1340,local_50);",
    ),
    "FUN_004a8c20": ("param_2[0xc]", "param_2[0xd]", "param_2[0xe]"),
    "FUN_00798df0": ("FUN_00795d60(this,param_1,local_2390,*(void **)((int)this + 0x1d00),param_1);",),
    "FUN_00795d60": (
        "local_3c=-((float)local_40 + (local_3c + local_28) * 0.5);",
        "local_38=-(float)local_18;",
        "*(float *)((int)param_1 + 0x19c)=local_3c;",
        "*(float *)((int)param_1 + 0x1a0)=local_38;",
        "*(float *)((int)param_1 + 0x1a4)=local_34;",
    ),
}

REQUIRED_EDGES = {
    ("0x00715240", "0x007152ec", "0x007125e0"),
    ("0x007125e0", "0x00712659", "0x00721ea0"),
    ("0x00721ea0", "0x00721eb3", "0x007839a0"),
    ("0x0070db00", "0x0070db29", "0x00481e20"),
    ("0x00795630", "0x00795684", "0x007904f0"),
    ("0x00798df0", "0x007990ed", "0x00795d60"),
    ("0x007904f0", "0x0079055e", "0x007aef50"),
    ("0x007904f0", "0x0079056d", "0x007125b0"),
    ("0x007904f0", "0x00790577", "0x00432c00"),
    ("0x007904f0", "0x00790736", "0x0065a770"),
    ("0x007904f0", "0x00790744", "0x004f8040"),
    ("0x004848bc", "0x004848f5", "0x00481e20"),
    ("0x004848bc", "0x00484916", "0x00483540"),
    ("0x00483540", "0x00483996", "0x00438da0"),
    ("0x00480700", "0x00480726", "0x0042fc90"),
    ("0x00480700", "0x0048074f", "0x004a8c20"),
}

PE_SIGNATURES = {
    0x0047F9FB: "8b86fc00000068ff3f0000508d8e10010000",
    0x0070DCDB: "8b15200bc10069c0a01f000003c280784c0074e2518bc8e809feffff",
    0x0070DB03: "8b81501f0000568db1700d00008b4d0883e00169c0f008000003c6",
    0x00721EA3: "8b45088981082600005081c140030000e8e81a0600",
    0x007839A3: "8b45088981480800005d",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    return rows


def _compact(text: str) -> str:
    return "".join(text.split())


def _extract_function(source: str, name: str) -> str:
    pos = 0
    while True:
        pos = source.find(name, pos)
        if pos < 0:
            raise ValueError(f"decompiler source missing {name}")
        opening = source.find("(", pos + len(name))
        if opening < 0:
            raise ValueError(f"decompiler source malformed near {name}")
        depth = 0
        cursor = opening
        quote = None
        escaped = False
        while cursor < len(source):
            char = source[cursor]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
            else:
                if char in "\"'":
                    quote = char
                elif char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                    if depth == 0:
                        break
            cursor += 1
        body = cursor + 1
        while body < len(source) and source[body].isspace():
            body += 1
        if body < len(source) and source[body] == "{":
            depth = 0
            cursor = body
            quote = None
            escaped = False
            while cursor < len(source):
                char = source[cursor]
                if quote:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == quote:
                        quote = None
                else:
                    if char in "\"'":
                        quote = char
                    elif char == "{":
                        depth += 1
                    elif char == "}":
                        depth -= 1
                        if depth == 0:
                            return source[pos : cursor + 1]
                cursor += 1
        pos += len(name)


def _addr(value: Any) -> str:
    text = str(value).lower().strip()
    if text.startswith("fun_"):
        text = text[4:]
    if text.startswith("0x"):
        text = text[2:]
    return f"0x{int(text, 16):08x}"


def _validate_database(root: Path) -> None:
    binary = _load(root / "binary.json")
    if (
        binary.get("format") != DB_FORMAT
        or binary.get("program_name") != PROGRAM
        or binary.get("executable_md5") != PE_MD5
    ):
        raise ValueError("retail Ghidra database identity drift")

    functions: dict[str, dict[str, Any]] = {}
    for row in _jsonl(root / "functions.jsonl"):
        try:
            address = _addr(row.get("address"))
        except Exception:
            continue
        if address in TARGETS:
            functions[address] = row
    missing = sorted(set(TARGETS) - set(functions))
    if missing:
        raise ValueError("missing required function(s): " + ", ".join(missing))
    for address, (name, size, calling_convention, mnemonic_sha256) in TARGETS.items():
        row = functions[address]
        if row.get("external") is True or row.get("thunk") is True:
            raise ValueError(f"{address}: expected concrete function")
        expected = {
            "name": name,
            "size": size,
            "calling_convention": calling_convention,
            "mnemonic_sha256": mnemonic_sha256,
        }
        for key, value in expected.items():
            if row.get(key) != value:
                raise ValueError(f"{address}: {key} drift")

    edges = set()
    for row in _jsonl(root / "callgraph.jsonl"):
        if row.get("indirect") is True:
            continue
        try:
            edge = (_addr(row.get("from_function")), _addr(row.get("instruction")), _addr(row.get("to")))
        except Exception:
            continue
        edges.add(edge)
    missing_edges = sorted(REQUIRED_EDGES - edges)
    if missing_edges:
        raise ValueError(f"required call-edge drift: {missing_edges}")

    globals_by_name = {row.get("name"): row for row in _jsonl(root / "globals.jsonl")}
    for name, address in (("DAT_00c109e0", SLOT_MANAGER), ("DAT_00c10b20", SLOT_ARRAY)):
        row = globals_by_name.get(name)
        if not isinstance(row, Mapping) or int(str(row.get("address")), 16) != address:
            raise ValueError(f"global address drift for {name}")
    if SLOT_ARRAY_OFFSET != 0x140:
        raise AssertionError("slot array offset invariant")


def _validate_source(path: Path) -> str:
    source = path.read_text(encoding="utf-8", errors="strict")
    for name, facts in SOURCE_FACTS.items():
        compact = _compact(_extract_function(source, name))
        for fact in facts:
            if _compact(fact) not in compact:
                raise ValueError(f"{name}: source fact drift: {fact}")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pe_sections(data: bytes) -> tuple[int, list[tuple[int, int, int, int]]]:
    if data[:2] != b"MZ":
        raise ValueError("SHIFT.exe: missing MZ")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe : pe + 4] != b"PE\0\0":
        raise ValueError("SHIFT.exe: missing PE signature")
    count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    optional = pe + 24
    if struct.unpack_from("<H", data, optional)[0] != 0x10B:
        raise ValueError("SHIFT.exe: expected PE32")
    image_base = struct.unpack_from("<I", data, optional + 28)[0]
    sections = []
    table = optional + optional_size
    for index in range(count):
        offset = table + index * 40
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from("<IIII", data, offset + 8)
        sections.append((virtual_address, max(virtual_size, raw_size), raw_pointer, raw_size))
    return image_base, sections


def _read_va(
    data: bytes,
    image_base: int,
    sections: list[tuple[int, int, int, int]],
    va: int,
    size: int,
) -> bytes:
    rva = va - image_base
    for virtual_address, span, raw_pointer, _raw_size in sections:
        if virtual_address <= rva and rva + size <= virtual_address + span:
            offset = raw_pointer + (rva - virtual_address)
            if offset + size <= len(data):
                return data[offset : offset + size]
    raise ValueError(f"SHIFT.exe: VA {va:#x} outside file-backed sections")


def _validate_pe(path: Path) -> list[dict[str, Any]]:
    md5 = _md5(path)
    if md5 != PE_MD5:
        raise ValueError(f"unexpected SHIFT.exe MD5 {md5}")
    data = path.read_bytes()
    image_base, sections = _pe_sections(data)
    if image_base != IMAGE_BASE:
        raise ValueError("SHIFT.exe image base drift")
    witnesses = []
    for va, expected_hex in PE_SIGNATURES.items():
        expected = bytes.fromhex(expected_hex)
        actual = _read_va(data, image_base, sections, va, len(expected))
        if actual != expected:
            raise ValueError(f"machine-byte drift at {va:#x}")
        witnesses.append({"address": f"0x{va:08x}", "bytes": expected_hex})
    return witnesses


def analyze(database_root: Path, decompiler_source: Path, shift_exe: Path) -> dict[str, Any]:
    _validate_database(database_root)
    source_sha = _validate_source(decompiler_source)
    machine = _validate_pe(shift_exe)
    return {
        "format": FORMAT,
        "version": 1,
        "status": "outer-render-snapshot-affine-bridge-proven-vhf-delta-join-pending",
        "ready": True,
        "retail": {"program": PROGRAM, "md5": PE_MD5, "source_sha256": source_sha},
        "machine_witnesses": machine,
        "slot_identity": {
            "manager_global": "0x00c109e0",
            "slot_array_global": "0x00c10b20",
            "slot_array_offset_from_manager": "0x140",
            "slot_stride": "0x1fa0",
            "outer_vehicle_record_offset": "+0x340",
            "outer_vehicle_slot_backpointer_offset": "+0x848",
            "participant_vehicle_index_staging": ["+0x100", "+0xfc"],
            "participant_snapshot_destination": "+0x110",
            "active_snapshot_base": "+0xd70",
            "active_snapshot_stride": "0x8f0",
            "active_snapshot_selector": "+0x1f50 & 1",
            "physical_slot_producer_consumer_bridge_ready": True,
        },
        "outer_transform": {
            "position_offsets": ["+0x160", "+0x164", "+0x168"],
            "orientation_parameter_offsets": ["+0x16c", "+0x170", "+0x174"],
            "orientation_matrix_offsets": [f"+0x{x:x}" for x in range(0x178, 0x19C, 4)],
            "render_root_local_delta_offsets": ["+0x19c", "+0x1a0", "+0x1a4"],
            "local_delta_has_concrete_setup_producer": True,
            "local_delta_is_runtime_pose_source": False,
        },
        "snapshot_relation": {
            "translation_formula": "P_snapshot = P_outer + R_outer * delta_local",
            "rotation_source": "R_outer (+0x178..+0x198) -> normalize -> matrix_to_quaternion -> snapshot quaternion",
            "independent_rotation_source_present": False,
            "writer_buffer": "slot + 0xd70 + ((selector - 1) & 1) * 0x8f0",
            "reader_buffer": "slot + 0xd70 + (selector & 1) * 0x8f0",
            "writer_increments_selector_after_publish": True,
            "retail_scheduler_cadence_claimed": False,
        },
        "render_participant_relation": {
            "source_snapshot": "participant+0x110",
            "render_snapshot": "participant+0xa00",
            "root_quaternion": "participant+0xa00..+0xa0c",
            "root_translation": ["participant+0xa10", "participant+0xa14", "participant+0xa18"],
            "derived_rotation_matrix": "participant+0x1028",
            "vehicle_render_model": "participant+0x1340",
            "world_affine_translation_slots": [12, 13, 14],
            "world_affine_consumed_by": "FUN_004a8c20",
            "node_local_FUN_004ae150_promoted_to_root_setter": False,
        },
        "handoff": {
            "outer_vehicle_to_render_root_symbolic_affine_ready": True,
            "outer_vehicle_render_snapshot_slot_identity_ready": True,
            "render_root_translation_delta_producer_bounded": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": [
            {
                "id": "render-root-local-delta-to-canonical-vhf-root",
                "required_evidence": "join outer Vehicle +0x19c/+0x1a0/+0x1a4 setup-produced local delta to the canonical BMW VHF hierarchy vehicle-root frame",
            },
            {
                "id": "orientation-roundtrip-semantic-equivalence",
                "required_evidence": "only if exact numeric identity is required: prove normalization/matrix->quaternion->matrix preserves the admitted outer orientation under the retail invariants; current proof needs only common-source provenance",
            },
        ],
        "next_proof": {
            "target": "FUN_00795d60 local delta producer -> canonical BMW VHF root / HIERARCHY owner",
            "do_not_reopen": [
                "car-body+0x34 PhysX owner",
                "car-body+0x534 collision LOD owner",
                "render-manager+0xca4 negative branches",
            ],
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database_root", type=Path)
    parser.add_argument("decompiler_source", type=Path)
    parser.add_argument("shift_exe", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = analyze(args.database_root, args.decompiler_source, args.shift_exe)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
