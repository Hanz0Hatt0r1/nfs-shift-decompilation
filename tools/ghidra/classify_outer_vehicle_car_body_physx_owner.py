#!/usr/bin/env python3
"""Retire the car-body +0x34 branch as standalone VHF/root identity evidence.

This is a deliberately narrow source-backed negative classifier.  The already
proven HighDetailVehicle/car-body join exposes a loaded pointer at car-body
+0x34, and that pointer participates in transform-looking virtual calls.  The
retail Ghidra C export, however, also shows the complete ownership boundary:

* FUN_007506b0 creates the global DAT_00c133ac owner from NxCreatePhysicsSDK;
* FUN_007798a0 asks DAT_00c133ac slot +0x1c for an object and stores it in
  param_2[1];
* FUN_007ac4d0 passes car_body+0x30 as that output pair, so param_2[1] is
  exactly car_body+0x34;
* FUN_007ab8e0 releases the same field through DAT_00c133ac slot +0x20 and
  clears it.

Therefore car-body+0x34 has a source-backed PhysX-owned lifetime.  It must not
be promoted to RenderHierarchy/VHF root identity merely because later virtual
calls consume transform-like data.  This pass does not claim that physics
objects can never be referenced by rendering code, and it does not prove the
remaining outer-Vehicle -> VHF frame relation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.OuterVehicleCarBodyPhysXOwnerNegative/1"
DB_FORMAT = "SHIFT.GhidraEvidenceDatabase/1"
UPSTREAM_FORMAT = "SHIFT.OuterVehicleChassisOwnerJoin/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

PHYSICS_INIT = "FUN_007506b0"
PHYSICS_OBJECT_BUILDER = "FUN_007798a0"
PHYSICS_OBJECT_SETUP = "FUN_00777cd0"
CAR_BODY_POST = "FUN_007ac2f0"
CAR_BODY_INIT = "FUN_007ac4d0"
CAR_BODY_TEARDOWN = "FUN_007ab8e0"

REQUIRED_FUNCTIONS = (
    PHYSICS_INIT,
    PHYSICS_OBJECT_BUILDER,
    PHYSICS_OBJECT_SETUP,
    CAR_BODY_POST,
    CAR_BODY_INIT,
    CAR_BODY_TEARDOWN,
)

SOURCE_FACTS: dict[str, tuple[str, ...]] = {
    PHYSICS_INIT: (
        'DAT_00c13384=(int*)NxCreatePhysicsSDK(0x2080100,DAT_00c13388,DAT_00c1338c,&local_7c,0);',
        '"FailedtoCreatePhysXSDK"',
        '".\\\\Source\\\\System\\\\PhysicsSystem.cpp"',
        'DAT_00c133ac=(int*)(**(code**)(*DAT_00c13384+0x10))(&local_128);',
    ),
    PHYSICS_OBJECT_BUILDER: (
        'piVar11=(int*)(**(code**)(*DAT_00c133ac+0x1c))(local_c0);',
        '*param_2=param_3;',
        'param_2[1]=(int)piVar11;',
        'piVar11[1]=(int)param_2;',
    ),
    CAR_BODY_INIT: (
        'FUN_007798a0(piVar5,&local_4c,(int*)(param_1+0x30)',
        'param_4=*(int**)(param_1+0x34);',
        'FUN_00777cd0(param_4);',
    ),
    CAR_BODY_TEARDOWN: (
        'piVar1=*(int**)(param_1+0x34);',
        '(**(code**)(*DAT_00c133ac+0x20))(piVar1);',
        '*(undefined4*)(param_1+0x34)=0;',
    ),
    CAR_BODY_POST: (
        'piVar1=*(int**)((int)this+0x34);',
        'FUN_007ab4e0(piVar1,local_58);',
        '(**(code**)(*piVar1+0xe0))(local_58+0xf);',
        '(**(code**)(*piVar1+0xe4))(local_58+0xc);',
    ),
    PHYSICS_OBJECT_SETUP: (
        'uVar2=(**(code**)(*param_1+0x4c))();',
        'local_8=(**(code**)(*param_1+0x50))();',
    ),
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _compact(value: str) -> str:
    return "".join(value.split())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _skip_quoted(text: str, index: int, quote: str) -> int:
    index += 1
    while index < len(text):
        ch = text[index]
        if ch == "\\":
            index += 2
            continue
        index += 1
        if ch == quote:
            return index
    raise ValueError("unterminated quoted literal in decompiler source")


def _skip_comment(text: str, index: int) -> int:
    if text.startswith("//", index):
        end = text.find("\n", index + 2)
        return len(text) if end < 0 else end + 1
    if text.startswith("/*", index):
        end = text.find("*/", index + 2)
        if end < 0:
            raise ValueError("unterminated block comment in decompiler source")
        return end + 2
    return index


def _matching(text: str, start: int, opening: str, closing: str) -> int:
    if start >= len(text) or text[start] != opening:
        raise ValueError(f"expected {opening!r} at source offset {start}")
    depth = 1
    index = start + 1
    while index < len(text):
        ch = text[index]
        if ch in {'"', "'"}:
            index = _skip_quoted(text, index, ch)
            continue
        after_comment = _skip_comment(text, index)
        if after_comment != index:
            index = after_comment
            continue
        if ch == opening:
            depth += 1
        elif ch == closing:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise ValueError(f"unterminated {opening}{closing} region in decompiler source")


def _extract_function(source: str, name: str) -> str:
    offset = 0
    while True:
        position = source.find(name, offset)
        if position < 0:
            raise ValueError(f"decompiler source missing definition for {name}")
        cursor = position + len(name)
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        if cursor >= len(source) or source[cursor] != "(":
            offset = position + len(name)
            continue
        end_args = _matching(source, cursor, "(", ")")
        cursor = end_args + 1
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        if cursor < len(source) and source[cursor] == "{":
            end_body = _matching(source, cursor, "{", "}")
            return source[position : end_body + 1]
        offset = position + len(name)


def _validate_upstream(path: Path) -> dict[str, Any]:
    report = _load_json(path)
    if report.get("format") != UPSTREAM_FORMAT or report.get("ready") is not True:
        raise ValueError(f"{path}: expected ready {UPSTREAM_FORMAT}")
    handoff = report.get("handoff") or {}
    if handoff.get("HDVehicle_car_body_CHASSIS_child_domain_joined_to_runtime_post_transform_domain") is not True:
        raise ValueError("upstream car-body/CHASSIS owner join is not ready")
    if handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is not False:
        raise ValueError("upstream unexpectedly preclaims VHF-root identity")
    chassis = report.get("chassis_init") or {}
    edges = chassis.get("embedded_owner_edges") or []
    if not any(
        isinstance(row, dict)
        and row.get("offset") == "+0x34"
        and str(row.get("callee") or "").lower() == "0x00777cd0"
        and row.get("kind") == "loaded-pointer"
        for row in edges
    ):
        raise ValueError("upstream car-body +0x34 -> FUN_00777cd0 loaded-pointer edge missing")
    return report


def _validate_retail_database(root: Path) -> dict[str, Any]:
    binary = _load_json(root / "binary.json")
    if binary.get("format") != DB_FORMAT:
        raise ValueError("unexpected Ghidra evidence database format")
    if binary.get("program_name") != PROGRAM or binary.get("executable_md5") != PE_MD5:
        raise ValueError("retail Ghidra database identity drift")
    return {"program": PROGRAM, "md5": PE_MD5}


def analyze(database_root: Path, upstream_path: Path, decompiler_source: Path) -> dict[str, Any]:
    retail = _validate_retail_database(database_root)
    upstream = _validate_upstream(upstream_path)
    source = decompiler_source.read_text(encoding="utf-8", errors="strict")
    extracted: dict[str, str] = {}
    for name in REQUIRED_FUNCTIONS:
        body = _extract_function(source, name)
        compact = _compact(body)
        for fact in SOURCE_FACTS[name]:
            if _compact(fact) not in compact:
                raise ValueError(f"{name}: required source fact drift: {fact}")
        extracted[name] = body

    return {
        "format": FORMAT,
        "version": 1,
        "status": "car-body-plus-0x34-physx-owner-branch-retired",
        "ready": True,
        "retail": retail,
        "inputs": {
            "upstream_format": UPSTREAM_FORMAT,
            "upstream_ready": upstream.get("ready") is True,
            "decompiler_source": str(decompiler_source),
            "decompiler_source_sha256": _sha256(decompiler_source),
            "source_function_count": len(extracted),
        },
        "source_audit": {
            "evidence_state": "source-backed-decompiler",
            "scope": (
                "audited SHIFT.exe.c ownership semantics anchored to the retail binary identity "
                "and the already instruction-proven car-body +0x34 consumer edge; not a claim "
                "that every possible alias/use of the created physics object is known"
            ),
            "facts": [
                "FUN_007506b0 creates DAT_00c13384 with NxCreatePhysicsSDK",
                "FUN_007506b0 obtains DAT_00c133ac from the PhysX SDK object through virtual slot +0x10",
                "FUN_007798a0 obtains piVar11 from DAT_00c133ac virtual slot +0x1c",
                "FUN_007798a0 stores piVar11 in param_2[1] and back-links piVar11[1] to param_2",
                "FUN_007ac4d0 passes car-body+0x30 as param_2, therefore param_2[1] is exactly car-body+0x34",
                "FUN_007ac4d0 immediately reloads car-body+0x34 and sends it to FUN_00777cd0",
                "FUN_007ab8e0 releases car-body+0x34 through the same DAT_00c133ac owner at virtual slot +0x20 and clears the field",
                "FUN_007ac2f0 later consumes car-body+0x34 through transform-like virtual calls, but those calls do not override the proven PhysX ownership domain",
            ],
        },
        "ownership_chain": {
            "sdk_global": "DAT_00c13384",
            "sdk_constructor": "NxCreatePhysicsSDK",
            "physics_owner_global": "DAT_00c133ac",
            "physics_owner_from_sdk_slot": "+0x10",
            "physics_object_create_slot": "+0x1c",
            "physics_object_release_slot": "+0x20",
            "builder": PHYSICS_OBJECT_BUILDER,
            "car_body_output_pair_base": "+0x30",
            "car_body_object_field": "+0x34",
            "producer_equation": "car_body[+0x34] = DAT_00c133ac.vslot(+0x1c)(descriptor)",
            "destroy_equation": "DAT_00c133ac.vslot(+0x20)(car_body[+0x34]); car_body[+0x34] = 0",
            "same_physics_owner_for_create_and_release": True,
            "physx_owned_lifetime_ready": True,
        },
        "negative_classification": {
            "car_body_plus_0x34_physx_owned_lifetime_proven": True,
            "car_body_plus_0x34_is_admissible_standalone_VHF_identity_anchor": False,
            "transform_like_virtual_calls_promoted_to_RenderHierarchy_identity": False,
            "car_body_plus_0x34_branch_removed_from_positive_VHF_owner_search": True,
        },
        "handoff": {
            "outer_vehicle_car_body_plus_0x34_physx_branch_retired": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "next_frontier": (
                "continue only with an independently identified VHF/render-resource owner path; "
                "do not reuse car-body +0x34 or the already-retired +0x534 collision lane as positive VHF identity evidence"
            ),
        },
        "scope": {
            "physx_subclass_name_invented": False,
            "absence_of_all_render_aliases_claimed": False,
            "physics_ownership_promoted_to_coordinate_frame_identity": False,
            "outer_vehicle_root_equated_to_VHF_root": False,
            "car_body_plus_0x534_collision_branch_reopened": False,
            "render_manager_ca4_branches_reopened": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database_root", type=Path)
    parser.add_argument("upstream_chassis_owner_join", type=Path)
    parser.add_argument("decompiler_source", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = analyze(args.database_root, args.upstream_chassis_owner_join, args.decompiler_source)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"status: {report['status']}")
    print("car-body +0x34 PhysX-owner negative classification: ready")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
