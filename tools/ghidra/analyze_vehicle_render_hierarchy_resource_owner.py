#!/usr/bin/env python3
"""Prove the selected-vehicle runtime path into the SMS RenderHierarchy owner.

This pass is intentionally narrower than BMW VHF identity.  It proves that the
retail participant installs a descriptor selected from the vehicle registry,
that the descriptor's reflected +0x54 field is `Vehicle Render Model`, and that
the embedded participant render model materializes that resource through the
same RenderHierarchy-family loader/vslot used by explicit `.vhf` resources.

The pass deliberately does *not* claim the concrete `Vehicle Render Model`
string stored by the retail `bmw_m3_e36` descriptor.  Consequently it does not
promote the canonical BMW VHF resource, outer-Vehicle/VHF frame equivalence,
BODY0 bind-frame readiness, or vehicle-world-transform readiness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1"
DB_FORMAT = "SHIFT.GhidraEvidenceDatabase/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

REGISTRY_LOOKUP = "FUN_004a5800"
PARTICIPANT_DESCRIPTOR_INSTALL = "FUN_00484720"
DESCRIPTOR_CLONE = "thunk_FUN_00d6e910"
DESCRIPTOR_COPY = "FUN_004a3000"
PARTICIPANT_RESOURCE_BUILD = "FUN_00483c50"
PARTICIPANT_RENDER_TICK = "FUN_004848bc"
PARTICIPANT_WORLD_CONSUMER = "FUN_00480700"
RENDER_MODEL_LOAD = "FUN_004aecd0"
RESOURCE_MATERIALIZE = "FUN_004aea10"
VHF_LOADER_WITNESS = "FUN_0043e670"
LOADER_DISPATCH = "FUN_0069c0b9"
HIERARCHY_GRAMMAR = "FUN_00699b10"
VEHICLE_SHADER_WITNESS = "FUN_004a8740"
DESCRIPTOR_REFLECTION = "thunk_FUN_00d6b610"

REQUIRED_FUNCTIONS = (
    REGISTRY_LOOKUP,
    PARTICIPANT_DESCRIPTOR_INSTALL,
    DESCRIPTOR_CLONE,
    DESCRIPTOR_COPY,
    PARTICIPANT_RESOURCE_BUILD,
    PARTICIPANT_RENDER_TICK,
    PARTICIPANT_WORLD_CONSUMER,
    RENDER_MODEL_LOAD,
    RESOURCE_MATERIALIZE,
    VHF_LOADER_WITNESS,
    LOADER_DISPATCH,
    HIERARCHY_GRAMMAR,
    VEHICLE_SHADER_WITNESS,
    DESCRIPTOR_REFLECTION,
)

SOURCE_FACTS: dict[str, tuple[str, ...]] = {
    REGISTRY_LOOKUP: (
        "piVar1=(int*)((int)this+0x10);",
        "iVar3=*(int*)(iVar4+0xc);",
        "_Str1=*(char**)(iVar3+0x10);",
        "iVar3=__stricmp(_Str1,_Str2);",
        "return*(undefined4*)(iVar4+0xc);",
    ),
    PARTICIPANT_DESCRIPTOR_INSTALL: (
        "piVar1=(int*)((int)param_1+0xa0);",
        "this=(void*)thunk_FUN_0047f675();",
        "iVar3=FUN_004a5800(this,piVar6);",
        "puVar4=thunk_FUN_00d6e910(iVar3);",
        "*(undefined4**)((int)param_1+0xf0)=puVar4;",
        "FUN_00483c50(param_1);",
    ),
    DESCRIPTOR_CLONE: (
        "FUN_008868c0(0x370)",
        "FUN_004a27e0(puVar1)",
        "FUN_004a3000(puVar1,param_1)",
    ),
    DESCRIPTOR_COPY: (
        "FUN_00632920((void*)((int)this+0x14),(int*)(param_1+0x14));",
        "FUN_00632920((void*)((int)this+0x54),(int*)(param_1+0x54));",
    ),
    PARTICIPANT_RESOURCE_BUILD: (
        "pcVar7=*(char**)(*(int*)((int)param_1+0xf0)+0x14);",
        "puVar13=*(undefined1**)(*(int*)((int)param_1+0xf0)+0x54);",
        "FUN_00636310(local_64,\"rcf\");",
        "local_150=*(undefined4*)((int)param_1+0xf0);",
        "FUN_004aecd0((int*)((int)param_1+0x1340),&local_158);",
    ),
    PARTICIPANT_RENDER_TICK: (
        "FUN_00481e20(param_1+0x280,param_1+0x44);",
        "FUN_00483540((uint)param_1);",
        "FUN_004ae150(param_1+0x4d0,unaff_EBP+-0x50,(uint)(param_1+0x280));",
    ),
    PARTICIPANT_WORLD_CONSUMER: (
        "FUN_0042fc90(local_50,(undefined4*)(param_1+0x1028));",
        "FUN_004a8c20(param_1+0x1340,local_50);",
    ),
    RENDER_MODEL_LOAD: (
        "local_10=param_2;",
        "FUN_004aea10(param_1,&local_20,*(uint*)((int)&uStack_454+uVar11*-10+iVar5+iVar4));",
    ),
    RESOURCE_MATERIALIZE: (
        "uVar1=param_3;",
        "iVar9=*(int*)(*(int*)(param_3+8)+0x54);",
        "pcVar2=*(char**)(*(int*)(uVar1+8)+0x14);",
        "puVar3=*(undefined1**)(*(int*)(uVar1+8)+0x54);",
        "piVar4=(int*)FUN_0069c0b0(param_2);",
        "uVar5=(**(code**)(*piVar4+0x24))();",
        "*(undefined4*)(local_18+0x178)=uVar5;",
    ),
    VHF_LOADER_WITNESS: (
        "FUN_00636310(local_44,\".vhf\");",
        "local_2c=(int*)FUN_0069c0b0(&local_24);",
        "uVar3=(**(code**)(*local_2c+0x24))();",
    ),
    LOADER_DISPATCH: (
        "piVar8=FUN_0069bac0(cVar13,pvVar14);",
    ),
    HIERARCHY_GRAMMAR: (
        "__stricmp(pcVar4,\"HIERARCHY\")",
        "__stricmp(pcVar4,\"OBJECT\")",
        "__stricmp(local_40,\"DAMAGE\")",
    ),
    VEHICLE_SHADER_WITNESS: (
        "FUN_00631740(&local_2c,\"render\\\\shaders\\\\vehicles_basic.fx\")",
        "FUN_00631740(&local_28,\"render\\\\shaders\\\\wheels.fx\")",
    ),
    DESCRIPTOR_REFLECTION: (
        "FUN_00631740(&iStack_c,\"Vehicle Render Model\");",
        "FUN_0063a280(&DAT_00b81f20,0,&iStack_c,0x54,3,&iStack_8);",
    ),
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compact(value: str) -> str:
    return "".join(value.split())


def _skip_quoted(text: str, index: int, quote: str) -> int:
    index += 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        ch = text[index]
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


def _validate_retail_database(root: Path) -> dict[str, str]:
    binary = _load_json(root / "binary.json")
    if binary.get("format") != DB_FORMAT:
        raise ValueError("unexpected Ghidra evidence database format")
    if binary.get("program_name") != PROGRAM or binary.get("executable_md5") != PE_MD5:
        raise ValueError("retail Ghidra database identity drift")
    return {"program": PROGRAM, "md5": PE_MD5}


def analyze(database_root: Path, decompiler_source: Path) -> dict[str, Any]:
    retail = _validate_retail_database(database_root)
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
        "status": "vehicle-render-hierarchy-owner-proven-bmw-vhf-value-pending",
        "ready": True,
        "retail": retail,
        "inputs": {
            "decompiler_source": str(decompiler_source),
            "decompiler_source_sha256": _sha256(decompiler_source),
            "source_function_count": len(extracted),
        },
        "vehicle_descriptor": {
            "registry_lookup": REGISTRY_LOOKUP,
            "registry_key_field": "+0x10",
            "case_insensitive_name_match": True,
            "participant_descriptor_install": PARTICIPANT_DESCRIPTOR_INSTALL,
            "participant_descriptor_field": "+0xf0",
            "descriptor_clone": DESCRIPTOR_CLONE,
            "descriptor_copy": DESCRIPTOR_COPY,
            "base_path_field_preserved": "+0x14",
            "render_model_field": "+0x54",
            "render_model_property_name": "Vehicle Render Model",
            "render_model_property_reflection_ready": True,
            "selected_registry_descriptor_to_participant_copy_ready": True,
        },
        "render_hierarchy_owner": {
            "participant_render_model_field": "+0x1340",
            "participant_snapshot_field": "+0x280",
            "participant_render_tick": PARTICIPANT_RENDER_TICK,
            "participant_world_consumer": PARTICIPANT_WORLD_CONSUMER,
            "resource_build": PARTICIPANT_RESOURCE_BUILD,
            "render_model_load": RENDER_MODEL_LOAD,
            "resource_materialize": RESOURCE_MATERIALIZE,
            "loader_entry": "FUN_0069c0b0",
            "loader_dispatch": LOADER_DISPATCH,
            "materialize_vslot": "+0x24",
            "materialized_runtime_object_field": "+0x178",
            "explicit_vhf_same_loader_and_vslot_witness": VHF_LOADER_WITNESS,
            "hierarchy_grammar": ["HIERARCHY", "OBJECT", "DAMAGE"],
            "vehicle_shader_witnesses": [
                "render\\shaders\\vehicles_basic.fx",
                "render\\shaders\\wheels.fx",
            ],
            "selected_vehicle_descriptor_to_render_hierarchy_owner_ready": True,
            "sms_participant_vehicle_render_model_ready": True,
            "vehicle_render_hierarchy_owner_ready": True,
        },
        "provenance": {
            "selected_vehicle_registry_lookup_is_name_based": True,
            "selected_descriptor_is_cloned_into_participant": True,
            "vehicle_render_model_property_offset_0x54_ready": True,
            "descriptor_render_model_value_flows_to_render_hierarchy_loader": True,
            "same_loader_and_materialize_slot_used_by_explicit_vhf": True,
            "materialized_object_has_vehicle_shader_consumers": True,
            "sms_participant_and_world_consumer_share_embedded_plus_0x1340_render_model": True,
        },
        "blockers": [
            {
                "id": "retail-bmw-m3-e36-vehicle-render-model-value-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "recover the exact retail `Vehicle Render Model` (+0x54) string from the "
                    "bmw_m3_e36 vehicle descriptor and join it to the canonical BMW VHF resource"
                ),
            },
            {
                "id": "outer-vehicle-root-to-vhf-vehicle-root-frame-relation-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "after exact BMW VHF identity is joined to this runtime owner, prove the "
                    "coordinate-frame relation between the outer Vehicle root and VHF vehicle root"
                ),
            },
        ],
        "handoff": {
            "selected_vehicle_descriptor_identity_ready": True,
            "vehicle_render_model_property_name_ready": True,
            "vehicle_render_model_property_offset_ready": True,
            "render_hierarchy_loader_family_ready": True,
            "vehicle_render_model_loader_materialization_ready": True,
            "vehicle_render_hierarchy_owner_ready": True,
            "selected_BMW_vehicle_render_model_value_ready": False,
            "canonical_BMW_VHF_resource_join_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "next_frontier": (
                "recover the exact bmw_m3_e36 `Vehicle Render Model` descriptor value; do not "
                "reopen car-body +0x34/+0x534 or render-manager +0xca4 negative branches"
            ),
        },
        "scope": {
            "bmw_vehicle_render_model_string_invented": False,
            "canonical_bmw_vhf_identity_promoted": False,
            "outer_vehicle_root_equated_to_vhf_root": False,
            "decompiler_source_promoted_beyond_frozen_facts": False,
            "car_body_physx_branch_reopened": False,
            "car_body_collision_branch_reopened": False,
            "render_manager_ca4_branches_reopened": False,
            "original_game_executed": False,
            "runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database_root", type=Path)
    parser.add_argument("decompiler_source", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = analyze(args.database_root, args.decompiler_source)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"status: {report['status']}")
    print("vehicle RenderHierarchy resource owner join: ready")
    print("BMW Vehicle Render Model value: pending")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
