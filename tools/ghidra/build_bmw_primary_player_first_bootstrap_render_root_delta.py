#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.BMWPrimaryPlayerFirstBootstrapRenderRootDelta/1"
RELATION_FORMAT = "SHIFT.OuterVehicleBMWVHFRootRelation/1"
SESSION_FORMAT = "SHIFT.BMWOffset33bNativeSessionSelection/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
VEHICLE = "BMW_M3_E36"
SESSION_TARGET = "Silverstone+BMW_M3_E36"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"

FUNCTIONS = {
    "0x0074ddc3": ("FUN_0074ddc3", 957, "__fastcall", "1b8f7a6602190fdd97b5a3d410495c8ff92b3a8b854a703459427b1ff548e4a6"),
    "0x0074e760": ("FUN_0074e760", 101, "__fastcall", "ee0a3baf733559a20dd134f43707056898cf73dd31be7d15a51922e1c02260b4"),
    "0x0078ef00": ("FUN_0078ef00", 1538, "__fastcall", "f981daa8164768121875faef1a053d93a6f78e6a3901a73aa32904b875ddb8e1"),
    "0x00795d60": ("FUN_00795d60", 8797, "__fastcall", "c587cae5d3d8f99afed40fe0c059c8c60bc9cc45d9ee644f5e90e2e1f5a8eb14"),
    "0x00797fd0": ("FUN_00797fd0", 612, "__thiscall", "b8f3cb6525e0742e2afefd31ca51dd050a9d869444526ce03df41067ecb3eeb8"),
    "0x00798df0": ("FUN_00798df0", 1581, "__thiscall", "88904019443d1ea4edaf5a3ef40dd5abfe9e28109ab0b1f09296388f36026e16"),
    "0x0079bfd0": ("FUN_0079bfd0", 445, "__fastcall", "06e730897a4a85d93a5f33765fd15b0c52708fb2c864c290804024b109a3d950"),
}

ORIGIN_GLOBALS = (0x00C16AB0, 0x00C16AB8, 0x00C16AC0)
SWITCH_FLAG = 0x00C19DB9

EXPECTED_INCOMING = {
    "0x0079bfd0": {("0x0079c1c0", "0x0079c1e1")},
    "0x00798df0": {("0x0074ddc3", "0x0074de12")},
    "0x00795d60": {("0x00798df0", "0x007990ed")},
    "0x0078ef00": {
        ("0x0074bfd0", "0x0074c05b"),
        ("0x00794a30", "0x00794a81"),
        ("0x0079b2d0", "0x0079b323"),
    },
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), f"{label} missing")
    return value


def _load_json(path: Path) -> Mapping[str, Any]:
    return _mapping(json.loads(path.read_text(encoding="utf-8")), str(path))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            _require(isinstance(value, dict), f"{path} contains a non-object row")
            rows.append(value)
    return rows


def parse_pe_sections(image: bytes) -> tuple[int, list[dict[str, int | str]]]:
    _require(len(image) >= 0x100, "PE image too small")
    pe = struct.unpack_from("<I", image, 0x3C)[0]
    _require(image[pe:pe + 4] == b"PE\0\0", "PE signature drift")
    number_of_sections = struct.unpack_from("<H", image, pe + 6)[0]
    optional_size = struct.unpack_from("<H", image, pe + 20)[0]
    optional = pe + 24
    _require(struct.unpack_from("<H", image, optional)[0] == 0x10B, "expected PE32 image")
    image_base = struct.unpack_from("<I", image, optional + 28)[0]
    section_table = optional + optional_size
    sections: list[dict[str, int | str]] = []
    for index in range(number_of_sections):
        off = section_table + index * 40
        name = image[off:off + 8].split(b"\0", 1)[0].decode("ascii", errors="strict")
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from("<IIII", image, off + 8)
        sections.append(
            {
                "name": name,
                "virtual_size": virtual_size,
                "virtual_address": virtual_address,
                "raw_size": raw_size,
                "raw_pointer": raw_pointer,
            }
        )
    return image_base, sections


def zero_fill_fact(image_base: int, sections: Sequence[Mapping[str, Any]], absolute_va: int) -> dict[str, Any]:
    rva = absolute_va - image_base
    for section in sections:
        start = int(section["virtual_address"])
        virtual_size = int(section["virtual_size"])
        if start <= rva < start + virtual_size:
            offset = rva - start
            raw_size = int(section["raw_size"])
            return {
                "address": f"0x{absolute_va:08x}",
                "section": str(section["name"]),
                "section_offset": f"0x{offset:x}",
                "section_virtual_size": f"0x{virtual_size:x}",
                "section_raw_size": f"0x{raw_size:x}",
                "image_loader_zero_fill": offset >= raw_size,
            }
    raise ValueError(f"VA 0x{absolute_va:08x} is outside PE sections")


def _file_offset_to_va(image_base: int, sections: Sequence[Mapping[str, Any]], file_offset: int) -> tuple[int, str] | None:
    for section in sections:
        raw_pointer = int(section["raw_pointer"])
        raw_size = int(section["raw_size"])
        if raw_pointer <= file_offset < raw_pointer + raw_size:
            va = image_base + int(section["virtual_address"]) + (file_offset - raw_pointer)
            return va, str(section["name"])
    return None


def absolute_reference_sites(
    image: bytes,
    image_base: int,
    sections: Sequence[Mapping[str, Any]],
    absolute_va: int,
) -> list[dict[str, Any]]:
    needle = struct.pack("<I", absolute_va)
    out: list[dict[str, Any]] = []
    start = 0
    while True:
        offset = image.find(needle, start)
        if offset < 0:
            break
        mapped = _file_offset_to_va(image_base, sections, offset)
        if mapped is not None:
            va, section = mapped
            out.append({"pattern_va": f"0x{va:08x}", "section": section})
        start = offset + 1
    return out


def _function_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        address = str(row.get("address") or "").lower()
        if address in FUNCTIONS:
            result[address] = row
    _require(set(result) == set(FUNCTIONS), "required retail function fingerprint row missing")
    for address, expected in FUNCTIONS.items():
        name, size, convention, mnemonic = expected
        row = result[address]
        _require(row.get("name") == name, f"{address} name drift")
        _require(row.get("size") == size, f"{address} size drift")
        _require(row.get("calling_convention") == convention, f"{address} calling convention drift")
        _require(row.get("mnemonic_sha256") == mnemonic, f"{address} mnemonic fingerprint drift")
    return result


def _incoming_edges(rows: Sequence[Mapping[str, Any]], target: str) -> set[tuple[str, str]]:
    return {
        (str(row.get("from_function") or "").lower(), str(row.get("instruction") or "").lower())
        for row in rows
        if str(row.get("to") or "").lower() == target and row.get("indirect") is False
    }


def validate_callgraph(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for target, expected in EXPECTED_INCOMING.items():
        actual = _incoming_edges(rows, target)
        _require(actual == expected, f"incoming direct-call set drift for {target}: {sorted(actual)}")
        result[target] = [
            {"from_function": caller, "instruction": instruction}
            for caller, instruction in sorted(actual)
        ]
    return result


def function_body(source: str, name: str) -> str:
    needle = f"{name}("
    search_from = 0
    while True:
        start = source.find(needle, search_from)
        _require(start >= 0, f"{name} definition missing from source")
        brace = source.find("{", start)
        semicolon = source.find(";", start)
        if brace >= 0 and (semicolon < 0 or brace < semicolon):
            depth = 0
            for index in range(brace, len(source)):
                char = source[index]
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        return source[start:index + 1]
            raise ValueError(f"{name} body is unterminated")
        search_from = start + len(needle)

def validate_source(source: str, *, require_hash: bool = True) -> dict[str, Any]:
    if require_hash:
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        _require(digest == SOURCE_SHA256, "retail decompiler source SHA-256 drift")

    restart = function_body(source, "FUN_0074ddc3")
    restart_config = function_body(source, "FUN_0074d640")
    role_setter = function_body(source, "FUN_00797fd0")
    init_vehicle = function_body(source, "FUN_00798df0")
    constructor = function_body(source, "FUN_0079bfd0")
    delta = function_body(source, "FUN_00795d60")
    config_init = function_body(source, "FUN_0074e760")
    origin_writer = function_body(source, "FUN_0078ef00")
    base_init = function_body(source, "FUN_00a62690")

    restart_role = "FUN_00797fd0((void *)(*unaff_ESI + 0x340),*(int *)(iVar1 + 0x10),'\\0',1);"
    restart_primary = "if (*(int *)(iVar1 + 0x10) == 0)"
    restart_primary_store = "DAT_00c10b34 = unaff_ESI;"
    restart_init = "FUN_00798df0((void *)(iVar6 + 0x340),(char)*(undefined4 *)(unaff_EBP + 0xc));"
    for marker in (restart_role, restart_primary, restart_primary_store, restart_init):
        _require(marker in restart, f"Restart source marker drift: {marker}")
    _require(
        restart.index(restart_role) < restart.index(restart_primary) < restart.index(restart_primary_store) < restart.index(restart_init),
        "Restart role-binding/InitVehicle lexical order drift",
    )
    _require("FUN_0078ef00(" not in restart[:restart.index(restart_init)], "origin writer entered Restart->InitVehicle prefix")
    for prefix_body, label in ((restart_config, "FUN_0074d640"), (role_setter, "FUN_00797fd0"), (base_init, "FUN_00a62690")):
        _require("FUN_0078ef00(" not in prefix_body, f"origin writer entered {label}")
        for offset in ("0x19c", "0x1a0", "0x1a4"):
            _require(offset not in prefix_body, f"{label} touches render-root delta field {offset}")

    init_delta_call = "FUN_00795d60(this,param_1,local_2390,*(void **)((int)this + 0x1d00),param_1);"
    _require(init_delta_call in init_vehicle, "InitVehicle -> FUN_00795d60 source binding drift")
    init_prefix = init_vehicle[:init_vehicle.index(init_delta_call)]
    _require("FUN_0078ef00(" not in init_prefix, "origin writer entered InitVehicle prefix")
    for offset in ("0x19c", "0x1a0", "0x1a4"):
        _require(f"(int)this + {offset}" not in init_prefix, f"InitVehicle prefix directly touches outer delta field {offset}")

    _require("*(int *)((int)this + 0x234) = param_1;" in role_setter, "Vehicle+0x234 role-code store drift")
    _require("*(undefined4 *)(param_1 + 0x10) = 0;" in config_init, "spawn config +0x10 default-zero initializer drift")

    for index in (0x67, 0x68, 0x69):
        _require(f"param_1[0x{index:x}] = 0;" in constructor, f"constructor delta zero at index 0x{index:x} missing")

    branch_markers = (
        "if (*(int *)((int)param_1 + 0x234) == 0)",
        "local_3c = local_28 - (float)_DAT_00c16ab0;",
        "local_38 = *(float *)((int)param_1 + 0x1a0) - (float)_DAT_00c16ab8;",
        "local_34 = *(float *)((int)param_1 + 0x1a4) - (float)_DAT_00c16ac0;",
        "*(float *)((int)param_1 + 0x19c) = local_3c;",
        "*(float *)((int)param_1 + 0x1a0) = local_38;",
        "*(float *)((int)param_1 + 0x1a4) = local_34;",
    )
    for marker in branch_markers:
        _require(marker in delta, f"primary-role delta branch marker drift: {marker}")

    _require("(double *)&DAT_00c16ab0" in origin_writer, "origin writer no longer receives DAT_00c16ab0")
    _require("FUN_007afd20" in origin_writer, "origin-vector writer helper drift")

    return {
        "restart_role_code_source": "PhysicsParticipant spawn config +0x10",
        "restart_zero_role_designates_primary_participant": True,
        "vehicle_role_code_field": "+0x234",
        "vehicle_constructor_delta_zero_offsets": ["+0x19c", "+0x1a0", "+0x1a4"],
        "primary_role_delta_formula": [
            "new +0x19c = old +0x19c - DAT_00c16ab0",
            "new +0x1a0 = old +0x1a0 - DAT_00c16ab8",
            "new +0x1a4 = old +0x1a4 - DAT_00c16ac0",
        ],
        "origin_writer": "FUN_0078ef00 -> FUN_007afd20(..., &DAT_00c16ab0, ...)",
        "origin_writer_in_restart_to_initvehicle_prefix": False,
    }


def validate_upstream(relation: Mapping[str, Any], session: Mapping[str, Any]) -> None:
    _require(relation.get("format") == RELATION_FORMAT and relation.get("ready") is True, "outer/VHF relation not positive")
    _require(relation.get("semantic_authority") == "Process 1", "outer/VHF relation semantic authority drift")
    subject = _mapping(relation.get("subject"), "outer/VHF relation subject")
    _require(subject.get("vehicle") == VEHICLE, "relation vehicle drift")
    _require(str(subject.get("canonical_vhf") or "").lower() == CANONICAL_VHF, "relation canonical VHF drift")
    rel = _mapping(relation.get("relation"), "outer/VHF relation")
    _require(rel.get("kind") == "fixed_affine", "outer/VHF relation is not fixed-affine")
    _require(rel.get("relation_matrix_numeric_ready") is False, "upstream relation already has a numeric matrix")
    handoff = _mapping(relation.get("handoff"), "outer/VHF relation handoff")
    _require(handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is True, "outer/VHF relation semantic gate not ready")
    _require(handoff.get("outer_vehicle_root_to_VHF_fixed_affine_delta_ready") is True, "outer/VHF fixed-affine gate not ready")
    _require(handoff.get("outer_vehicle_root_to_VHF_relation_numeric_matrix_ready") is False, "upstream numeric relation gate preclaimed")

    _require(session.get("format") == SESSION_FORMAT and session.get("ready") is True, "native BMW session selector not ready")
    _require(session.get("vehicle") == VEHICLE, "native session vehicle drift")
    _require(session.get("session_target") == SESSION_TARGET, "native session target drift")
    selector = _mapping(session.get("selector"), "native session selector")
    _require(selector.get("source") == "explicit-native-vertical-slice-policy", "native session is not explicit policy")
    _require(selector.get("validated_against_retail_selector_domain") is True, "native session selector not retail-domain validated")


def build_report(
    relation: Mapping[str, Any],
    session: Mapping[str, Any],
    function_rows: Sequence[Mapping[str, Any]],
    callgraph_rows: Sequence[Mapping[str, Any]],
    source: str,
    image: bytes,
    *,
    native_role: str,
    first_vehicle_bootstrap: bool,
) -> dict[str, Any]:
    validate_upstream(relation, session)
    _require(native_role == "primary-player", "this proof is limited to explicit native primary-player role")
    _require(first_vehicle_bootstrap is True, "this proof is limited to first vehicle bootstrap")
    _require(hashlib.md5(image).hexdigest() == PE_MD5, "retail SHIFT.exe MD5 drift")
    _function_rows(function_rows)
    incoming = validate_callgraph(callgraph_rows)
    source_proof = validate_source(source)

    image_base, sections = parse_pe_sections(image)
    zero_facts = [zero_fill_fact(image_base, sections, address) for address in (*ORIGIN_GLOBALS, SWITCH_FLAG)]
    _require(all(row["section"] == ".data" and row["image_loader_zero_fill"] is True for row in zero_facts), "required globals are not PE .data zero-fill")

    refs = {
        f"0x{address:08x}": absolute_reference_sites(image, image_base, sections, address)
        for address in (*ORIGIN_GLOBALS, SWITCH_FLAG)
    }
    _require(len(refs["0x00c16ab0"]) == 2, "DAT_00c16ab0 absolute xref count drift")
    _require(len(refs["0x00c16ab8"]) == 1, "DAT_00c16ab8 absolute xref count drift")
    _require(len(refs["0x00c16ac0"]) == 1, "DAT_00c16ac0 absolute xref count drift")
    _require(len(refs["0x00c19db9"]) == 2, "DAT_00c19db9 absolute xref count drift")
    _require(all(row["section"] == ".text" for rows in refs.values() for row in rows), "required global absolute xref escaped .text")

    writer_pointer_refs = absolute_reference_sites(image, image_base, sections, 0x0078EF00)
    _require(writer_pointer_refs == [], "FUN_0078ef00 has an absolute function-pointer reference")

    delta_numeric = [0.0, 0.0, 0.0]

    return {
        "format": FORMAT,
        "version": 1,
        "status": "bmw-primary-player-first-bootstrap-render-root-delta-proven",
        "ready": True,
        "vehicle": VEHICLE,
        "session_target": SESSION_TARGET,
        "semantic_authority": "Process 1",
        "inputs": {
            "outer_vehicle_vhf_relation": RELATION_FORMAT,
            "native_session_selector": SESSION_FORMAT,
            "retail_program": PROGRAM,
        },
        "native_bootstrap_policy": {
            "role": "primary-player",
            "physics_participant_spawn_config_plus_0x10": 0,
            "first_vehicle_bootstrap": True,
            "source": "explicit-native-vertical-slice-policy",
            "validated_against_retail_restart_role_semantics": True,
            "retail_live_session_role_observed": False,
        },
        "retail": {
            "program": PROGRAM,
            "md5": PE_MD5,
            "decompiler_source_sha256": SOURCE_SHA256,
            "function_fingerprints": {
                address: {
                    "name": expected[0],
                    "size": expected[1],
                    "calling_convention": expected[2],
                    "mnemonic_sha256": expected[3],
                }
                for address, expected in FUNCTIONS.items()
            },
            "incoming_direct_calls": incoming,
        },
        "bootstrap_provenance": {
            "source_proof": source_proof,
            "pe_zero_fill": {
                "image_base": f"0x{image_base:08x}",
                "globals": zero_facts,
            },
            "absolute_reference_sites": refs,
            "origin_vector_unique_reviewed_direct_writer": "FUN_0078ef00",
            "origin_writer_direct_callers": ["FUN_0074bfd0", "FUN_00794a30", "FUN_0079b2d0"],
            "origin_writer_absolute_function_pointer_refs": [],
            "selected_prefix": "first native primary-player PhysicsParticipant::Restart -> FUN_00797fd0(role=0) -> Vehicle::InitVehicle -> FUN_00795d60",
            "origin_writer_reached_before_selected_delta_store": False,
            "constructor_old_delta": [0.0, 0.0, 0.0],
            "image_initial_origin_vector": [0.0, 0.0, 0.0],
            "primary_role_formula_evaluation": "old_delta - initial_origin",
        },
        "selected_numeric": {
            "delta_local_offsets": ["+0x19c", "+0x1a0", "+0x1a4"],
            "delta_local": delta_numeric,
            "producer": "FUN_00795d60",
            "scope": "first explicit native primary-player vehicle bootstrap before any origin-update path",
        },
        "handoff": {
            "BMW_primary_player_first_bootstrap_render_root_delta_numeric_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": True,
            "outer_vehicle_root_to_VHF_relation_numeric_matrix_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "consumer": "Process 1 numeric outer->VHF evaluator, then SHIFT.BMWBody0BindFrameProof/1; Process 2 only after numeric relation admission",
        },
        "limits": {
            "first_primary_player_bootstrap_only": True,
            "delta_zero_claimed_for_restart_or_mode_switch": False,
            "delta_zero_claimed_for_non_primary_vehicle": False,
            "native_role_policy_is_retail_live_session_observation": False,
            "origin_vector_assumed_zero_after_first_origin_update": False,
            "VHF_root_numeric_matrix_consumed": False,
            "outer_vehicle_VHF_numeric_matrix_claimed": False,
            "BODY0_bind_frame_claimed": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
        "next_blocker": {
            "id": "BMW-outer-VHF-numeric-relation-evaluation",
            "required": "consume the exact positive BMW VHF HIERARCHY Root row-vector matrix and delta_local=(0,0,0), evaluate SHIFT.OuterVehicleBMWVHFRootRelation/1 numerically, then compose the already-positive selected BMW BODY0->outer matrix",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("relation", type=Path)
    parser.add_argument("native_session", type=Path)
    parser.add_argument("functions_jsonl", type=Path)
    parser.add_argument("callgraph_jsonl", type=Path)
    parser.add_argument("shift_c", type=Path)
    parser.add_argument("shift_exe", type=Path)
    parser.add_argument("--native-role", required=True, choices=("primary-player",))
    parser.add_argument("--first-vehicle-bootstrap", action="store_true")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    source_bytes = args.shift_c.read_bytes()
    _require(hashlib.sha256(source_bytes).hexdigest() == SOURCE_SHA256, "retail decompiler source SHA-256 drift")
    source = source_bytes.decode("utf-8")
    report = build_report(
        _load_json(args.relation),
        _load_json(args.native_session),
        _load_jsonl(args.functions_jsonl),
        _load_jsonl(args.callgraph_jsonl),
        source,
        args.shift_exe.read_bytes(),
        native_role=args.native_role,
        first_vehicle_bootstrap=args.first_vehicle_bootstrap,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
