#!/usr/bin/env python3
"""Bound the final VehicleDetails physics/render owner join for P1.1.

The selected-vehicle render side is already source-backed through
``SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1`` and the BMW SDF construction
side is already source-backed through
``SHIFT.BMWSDFVehicleAssemblyReceiverProvenance/1``.  The remaining useful
question is narrower: does the reflected ``Vehicle Physics Model`` field on the
same VehicleDetails descriptor physically feed HighDetailVehicle::Init, and if
so through which exact producer expression?

This pass deliberately stops before coordinate-frame semantics.  It proves the
paired reflected property offsets, freezes the complete direct caller set of
HighDetailVehicle::Init for the retail executable, extracts the physical source
arguments at those callsites, and emits only those callers as the next targeted
instruction worklist.  A shared descriptor class or resource archive is never
promoted to frame identity.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_vehicle_render_hierarchy_resource_owner as _render_source

FORMAT = "SHIFT.VehicleDescriptorPhysicsRenderOwnerFrontier/1"
DB_FORMAT = "SHIFT.GhidraEvidenceDatabase/1"
RENDER_OWNER_FORMAT = "SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1"
SDF_RECEIVER_FORMAT = "SHIFT.BMWSDFVehicleAssemblyReceiverProvenance/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

REFLECTION_FUNCTION = _render_source.DESCRIPTOR_REFLECTION
HDVEHICLE_INIT = "0x0076df50"
HDVEHICLE_GLOBAL = "DAT_00c13700"
RENDER_MODEL_FIELD = "+0x54"
PHYSICS_MODEL_FIELD = "+0x60"
RENDER_MODEL_PROPERTY = "Vehicle Render Model"
PHYSICS_MODEL_PROPERTY = "Vehicle Physics Model"
MAX_DIRECT_CALLERS = 8

# Retail MD5 is fixed above, so this exact direct-caller set is a drift guard,
# not discovery by callgraph proximity.
EXPECTED_INIT_CALLS = {
    ("0x0074da70", "0x0074dadf"),
    ("0x00798df0", "0x00798f9c"),
}

REFLECTION_STRINGS = {
    "0x00abbb8c": (PHYSICS_MODEL_PROPERTY, "0x00d6bacf"),
    "0x00abbbcc": (RENDER_MODEL_PROPERTY, "0x00d6b929"),
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            text = raw.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            rows.append(value)
    return rows


def _addr(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field}: expected address string")
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError as exc:
        raise ValueError(f"{field}: invalid address {value!r}") from exc


def _validate_retail_database(root: Path) -> dict[str, str]:
    binary = _load_json(root / "binary.json")
    if binary.get("format") != DB_FORMAT:
        raise ValueError("unexpected Ghidra evidence database format")
    if binary.get("program_name") != PROGRAM or binary.get("executable_md5") != PE_MD5:
        raise ValueError("retail Ghidra database identity drift")
    return {"program": PROGRAM, "md5": PE_MD5}


def _validate_render_owner(path: Path) -> dict[str, Any]:
    report = _load_json(path)
    if report.get("format") != RENDER_OWNER_FORMAT or report.get("ready") is not True:
        raise ValueError("vehicle RenderHierarchy owner proof is not positive")
    descriptor = report.get("vehicle_descriptor")
    handoff = report.get("handoff")
    if not isinstance(descriptor, Mapping) or not isinstance(handoff, Mapping):
        raise ValueError("vehicle RenderHierarchy owner proof shape drift")
    if descriptor.get("render_model_field") != RENDER_MODEL_FIELD:
        raise ValueError("Vehicle Render Model field drift")
    if descriptor.get("render_model_property_name") != RENDER_MODEL_PROPERTY:
        raise ValueError("Vehicle Render Model property-name drift")
    if handoff.get("vehicle_render_hierarchy_owner_ready") is not True:
        raise ValueError("vehicle RenderHierarchy owner handoff is not ready")
    if handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is not False:
        raise ValueError("render owner proof unexpectedly preclaims frame identity")
    return report


def _validate_sdf_receiver(path: Path) -> dict[str, Any]:
    report = _load_json(path)
    if report.get("format") != SDF_RECEIVER_FORMAT or report.get("ready") is not True:
        raise ValueError("BMW SDF vehicle-assembly receiver proof is not positive")
    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("BMW SDF receiver handoff missing")
    if handoff.get("SDF_loader_receiver_equals_HighDetailVehicle_Init_entry_ECX") is not True:
        raise ValueError("SDF loader receiver is not proven equal to HighDetailVehicle::Init receiver")
    for key in ("SDF_model_to_VHF_vehicle_root_frame_relation_ready", "BODY0_bind_frame_proof_ready"):
        if handoff.get(key) is not False:
            raise ValueError(f"BMW SDF receiver proof unexpectedly preclaims {key}")
    return report


def _validate_reflection_strings(root: Path) -> list[dict[str, str]]:
    by_address: dict[str, Mapping[str, Any]] = {}
    for row in _read_jsonl(root / "strings_xrefs.jsonl"):
        raw = row.get("address")
        if isinstance(raw, str):
            by_address[_addr(raw, field="strings.address")] = row
    result: list[dict[str, str]] = []
    for address, (value, xref) in REFLECTION_STRINGS.items():
        row = by_address.get(address)
        if not isinstance(row, Mapping):
            raise ValueError(f"missing reflection string {address}")
        if row.get("value") != value:
            raise ValueError(f"reflection string value drift at {address}")
        xrefs = {
            _addr(item, field="strings.xref")
            for item in (row.get("xrefs") or [])
            if isinstance(item, str)
        }
        if xref not in xrefs:
            raise ValueError(f"reflection string xref drift at {address}")
        result.append({"address": address, "value": value, "xref": xref})
    return result


def _validate_reflection_source(source: str) -> dict[str, Any]:
    body = _render_source._extract_function(source, REFLECTION_FUNCTION)
    compact = _render_source._compact(body)
    required = (
        'FUN_00631740(&iStack_c,"Vehicle Render Model");',
        'FUN_0063a280(&DAT_00b81f20,0,&iStack_c,0x54,3,&iStack_8);',
        'FUN_00631740(&iStack_c,"Vehicle Physics Model");',
        'FUN_0063a280(&DAT_00b81f20,0,&iStack_c,0x60,3,&iStack_8);',
    )
    for fact in required:
        if _render_source._compact(fact) not in compact:
            raise ValueError(f"{REFLECTION_FUNCTION}: required source fact drift: {fact}")
    return {
        "function": REFLECTION_FUNCTION,
        "render_model_property": RENDER_MODEL_PROPERTY,
        "render_model_field": RENDER_MODEL_FIELD,
        "physics_model_property": PHYSICS_MODEL_PROPERTY,
        "physics_model_field": PHYSICS_MODEL_FIELD,
        "same_reflection_registry": "DAT_00b81f20",
    }


def _function_inventory(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(root / "functions.jsonl"):
        raw = row.get("address")
        if not isinstance(raw, str):
            continue
        address = _addr(raw, field="functions.address")
        if address in result:
            raise ValueError(f"duplicate function row {address}")
        result[address] = row
    return result


def _direct_init_calls(root: Path) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []
    for row in _read_jsonl(root / "callgraph.jsonl"):
        if row.get("indirect") is True:
            continue
        raw_from, raw_instruction, raw_to = row.get("from_function"), row.get("instruction"), row.get("to")
        if not all(isinstance(item, str) for item in (raw_from, raw_instruction, raw_to)):
            continue
        target = _addr(raw_to, field="callgraph.to")
        if target != HDVEHICLE_INIT:
            continue
        calls.append(
            (
                _addr(raw_from, field="callgraph.from_function"),
                _addr(raw_instruction, field="callgraph.instruction"),
            )
        )
    observed = set(calls)
    if observed != EXPECTED_INIT_CALLS:
        raise ValueError(
            "HighDetailVehicle::Init direct-caller drift; "
            f"missing={sorted(EXPECTED_INIT_CALLS - observed)}, "
            f"extra={sorted(observed - EXPECTED_INIT_CALLS)}"
        )
    if len(calls) > MAX_DIRECT_CALLERS:
        raise ValueError("HighDetailVehicle::Init caller set exceeds safety cap")
    return sorted(calls)


def _split_arguments(text: str) -> list[str]:
    args: list[str] = []
    start = 0
    paren = bracket = brace = 0
    quote: str | None = None
    escaped = False
    for index, ch in enumerate(text):
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in {'"', "'"}:
            quote = ch
            continue
        if ch == "(":
            paren += 1
        elif ch == ")":
            paren -= 1
        elif ch == "[":
            bracket += 1
        elif ch == "]":
            bracket -= 1
        elif ch == "{":
            brace += 1
        elif ch == "}":
            brace -= 1
        elif ch == "," and paren == bracket == brace == 0:
            args.append(text[start:index])
            start = index + 1
    args.append(text[start:])
    return [arg for arg in args if arg]


def _call_arguments(body: str, target: str) -> list[str]:
    compact = _render_source._compact(body)
    needle = target + "("
    offsets: list[int] = []
    start = 0
    while True:
        position = compact.find(needle, start)
        if position < 0:
            break
        offsets.append(position)
        start = position + len(needle)
    if len(offsets) != 1:
        raise ValueError(f"expected exactly one source call to {target}, found {len(offsets)}")
    open_paren = offsets[0] + len(target)
    close_paren = _render_source._matching(compact, open_paren, "(", ")")
    return _split_arguments(compact[open_paren + 1 : close_paren])


def _field_offsets(expression: str) -> list[str]:
    values = {
        f"0x{int(raw, 16):x}"
        for raw in re.findall(r"\+0x([0-9a-fA-F]+)", expression)
    }
    return sorted(values, key=lambda token: int(token, 16))


def analyze(
    database_root: Path,
    decompiler_source: Path,
    render_owner_proof: Path,
    sdf_receiver_proof: Path,
) -> dict[str, Any]:
    retail = _validate_retail_database(database_root)
    _validate_render_owner(render_owner_proof)
    _validate_sdf_receiver(sdf_receiver_proof)
    reflection_strings = _validate_reflection_strings(database_root)

    source = decompiler_source.read_text(encoding="utf-8", errors="strict")
    reflection = _validate_reflection_source(source)
    inventory = _function_inventory(database_root)
    calls = _direct_init_calls(database_root)

    caller_rows: list[dict[str, Any]] = []
    worklist: list[str] = []
    for caller, callsite in calls:
        meta = inventory.get(caller)
        if not isinstance(meta, Mapping):
            raise ValueError(f"missing function metadata for HighDetailVehicle::Init caller {caller}")
        name = meta.get("name")
        if not isinstance(name, str):
            raise ValueError(f"{caller}: function name missing")
        body = _render_source._extract_function(source, name)
        args = _call_arguments(body, "FUN_0076df50")
        if len(args) < 2:
            raise ValueError(f"{name}: HighDetailVehicle::Init call has fewer than two physical arguments")
        if HDVEHICLE_GLOBAL not in args[0]:
            raise ValueError(f"{name}: HighDetailVehicle::Init receiver is not {HDVEHICLE_GLOBAL}")
        second = args[1]
        caller_rows.append(
            {
                "function": caller,
                "function_name": name,
                "callsite": callsite,
                "receiver_expression": args[0],
                "second_argument_expression": second,
                "second_argument_field_offsets": _field_offsets(second),
                "second_argument_mentions_physics_model_field_0x60": "+0x60" in second.lower(),
                "second_argument_mentions_DAT_00c10b34": "DAT_00c10b34" in second,
                "source_body_mentions_DAT_00c10b34": "DAT_00c10b34" in body,
                "source_body_mentions_field_0x848": "+0x848" in _render_source._compact(body).lower(),
                "second_argument_is_proven_VehicleDetails_plus_0x60": False,
            }
        )
        worklist.append(caller)

    return {
        "format": FORMAT,
        "version": 1,
        "status": "vehicle-descriptor-physics-render-owner-frontier-ready",
        "ready": True,
        "retail": retail,
        "inputs": {
            "render_owner_proof": str(render_owner_proof),
            "render_owner_format": RENDER_OWNER_FORMAT,
            "sdf_receiver_proof": str(sdf_receiver_proof),
            "sdf_receiver_format": SDF_RECEIVER_FORMAT,
            "decompiler_source": str(decompiler_source),
        },
        "vehicle_details_reflection": {
            **reflection,
            "string_xrefs": reflection_strings,
            "paired_render_and_physics_property_offsets_ready": True,
            "same_descriptor_class_proves_same_coordinate_frame": False,
        },
        "proven_owner_ends": {
            "render": {
                "field": RENDER_MODEL_FIELD,
                "property": RENDER_MODEL_PROPERTY,
                "selected_descriptor_to_RenderHierarchy_owner_ready": True,
            },
            "physics": {
                "field": PHYSICS_MODEL_FIELD,
                "property": PHYSICS_MODEL_PROPERTY,
                "HighDetailVehicle_Init_to_SDF_loader_receiver_continuity_ready": True,
            },
        },
        "high_detail_vehicle_init_callers": caller_rows,
        "provenance": {
            "vehicle_details_render_and_physics_reflection_offsets_ready": True,
            "render_hierarchy_owner_input_positive": True,
            "sdf_vehicle_assembly_receiver_input_positive": True,
            "complete_direct_HighDetailVehicle_Init_caller_set_frozen": True,
            "HighDetailVehicle_Init_receiver_is_global_DAT_00c13700_at_all_direct_calls": True,
            "HighDetailVehicle_Init_second_argument_expressions_recovered": True,
            "VehicleDetails_plus_0x60_to_HighDetailVehicle_Init_argument_ready": False,
        },
        "targeted_instruction_worklist": {
            "format": INSTRUCTION_FORMAT,
            "function_count": len(worklist),
            "functions": worklist,
            "max_functions": MAX_DIRECT_CALLERS,
            "neighbors_added": False,
            "selection_rule": (
                "exact complete direct caller set of source-backed HighDetailVehicle::Init; "
                "no callgraph neighbors or descriptor-name heuristics"
            ),
            "question": (
                "at each exact FUN_0076df50 callsite, prove all-path provenance of the second "
                "physical argument and whether it is the selected VehicleDetails+0x60 "
                "Vehicle Physics Model value"
            ),
        },
        "blockers": [
            {
                "id": "vehicle-details-physics-model-to-high-detail-vehicle-init-argument-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "targeted instruction/value provenance must join the selected VehicleDetails "
                    "+0x60 value to the second physical argument of FUN_0076df50 on the exact "
                    "direct caller set, or close this branch negatively"
                ),
            },
            {
                "id": "high-detail-vehicle-assembly-frame-to-vhf-root-frame-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "even after a common descriptor owner is proven, show that no affine delta is "
                    "inserted between the physics assembly root and RenderHierarchy VHF root, or "
                    "recover that exact fixed delta"
                ),
            },
        ],
        "handoff": {
            "vehicle_details_render_model_property_ready": True,
            "vehicle_details_physics_model_property_ready": True,
            "vehicle_details_render_physics_property_pair_ready": True,
            "vehicle_render_hierarchy_owner_ready": True,
            "SDF_HighDetailVehicle_assembly_receiver_ready": True,
            "vehicle_physics_model_to_HighDetailVehicle_Init_argument_ready": False,
            "descriptor_physics_render_common_runtime_owner_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "next_frontier": (
                "run the exact two-caller instruction worklist and prove the second physical "
                "FUN_0076df50 argument provenance; common VehicleDetails class identity alone is "
                "not coordinate-frame identity"
            ),
        },
        "scope": {
            "common_descriptor_class_promoted_to_pointer_identity": False,
            "common_descriptor_class_promoted_to_frame_identity": False,
            "physics_model_property_name_promoted_to_runtime_value": False,
            "second_argument_expression_promoted_to_vehicle_physics_model": False,
            "callgraph_neighbors_added": False,
            "identity_affine_delta_assumed": False,
            "original_game_executed": False,
            "runtime_capture_required": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("decompiler_source", type=Path)
    parser.add_argument("render_owner_proof", type=Path)
    parser.add_argument("sdf_receiver_proof", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = analyze(
        args.ghidra_export,
        args.decompiler_source,
        args.render_owner_proof,
        args.sdf_receiver_proof,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out is None:
        print(text, end="")
    else:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
