#!/usr/bin/env python3
"""Join FUN_007b7840 Ghidra parameter storage to proven callsite registers.

This layer consumes the all-path physical callsite provenance from Process 1
#1205 and the ordinary SHIFT Ghidra ``functions.jsonl`` export.  It binds each
Ghidra parameter ordinal to its physical register or stack storage and, for
register-backed parameters, attaches the exact all-path origins observed before
each relevant call.

The join is deliberately narrower than a semantic bind proof.  Ghidra-reported
parameter names/types are retained as metadata only.  Stack argument *locations*
are proven by the function ABI, but their callsite values remain unproven until a
later stack-value provenance pass.  No parameter is named BODY/origin/basis from
its ordinal or register position.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.BMWBody0BindPoseWriterABI/1"
PHYSICAL_FORMAT = "SHIFT.BMWBody0BindCallsiteRegisterProvenance/1"
POSE_WRITER = "0x007b7840"

_REGISTER_STORAGE = re.compile(
    r"^(?P<register>[A-Za-z][A-Za-z0-9]*):(?P<size>[0-9]+)(?P<auto> \(auto\))?$"
)
_STACK_STORAGE = re.compile(
    r"^Stack\[(?P<offset>0x[0-9A-Fa-f]+)\]:(?P<size>[0-9]+)$"
)

# Ghidra can report byte/word aliases while the Process 1 register engine tracks
# the containing IA-32 general-purpose register.  This map is storage plumbing,
# not semantic role inference.
_PARENT_REGISTER = {
    "EAX": "EAX", "AX": "EAX", "AH": "EAX", "AL": "EAX",
    "EBX": "EBX", "BX": "EBX", "BH": "EBX", "BL": "EBX",
    "ECX": "ECX", "CX": "ECX", "CH": "ECX", "CL": "ECX",
    "EDX": "EDX", "DX": "EDX", "DH": "EDX", "DL": "EDX",
    "ESI": "ESI", "SI": "ESI",
    "EDI": "EDI", "DI": "EDI",
    "EBP": "EBP", "BP": "EBP",
    "ESP": "ESP", "SP": "ESP",
}


def _read_json(path: Path, expected_format: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict) or value.get("format") != expected_format:
        raise ValueError(f"{path}: expected {expected_format}")
    return value


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            text = raw.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield row


def _normalize_address(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field}: expected address string")
    text = value.strip().lower()
    if text.startswith("fun_"):
        text = text[4:]
    if not text.startswith("0x"):
        text = "0x" + text
    try:
        number = int(text, 16)
    except ValueError as exc:
        raise ValueError(f"{field}: invalid address {value!r}") from exc
    return f"0x{number:08x}"


def _load_pose_writer_function(export_root: Path) -> dict[str, Any]:
    path = export_root / "functions.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing Ghidra functions export: {path}")
    found: list[dict[str, Any]] = []
    for row in _read_jsonl(path):
        address = row.get("address")
        if not isinstance(address, str):
            continue
        try:
            normalized = _normalize_address(address, field="functions.address")
        except ValueError:
            continue
        if normalized == POSE_WRITER:
            found.append(row)
    if len(found) != 1:
        raise ValueError(
            f"functions.jsonl must contain exactly one {POSE_WRITER} row; found {len(found)}"
        )
    row = found[0]
    if row.get("external") is True:
        raise ValueError("pose writer unexpectedly marked external")
    if row.get("thunk") is True:
        raise ValueError("pose writer unexpectedly marked thunk")
    if not isinstance(row.get("calling_convention"), str) or not row["calling_convention"]:
        raise ValueError("pose writer calling convention missing")
    parameters = row.get("parameters")
    if not isinstance(parameters, list) or not parameters:
        raise ValueError("pose writer parameter storage missing")
    return row


def _parse_storage(storage: Any, *, parameter_index: int) -> dict[str, Any]:
    if not isinstance(storage, str) or not storage:
        raise ValueError(f"parameter {parameter_index}: storage missing")
    register_match = _REGISTER_STORAGE.fullmatch(storage)
    if register_match:
        register = register_match.group("register").upper()
        parent = _PARENT_REGISTER.get(register)
        if parent is None:
            raise ValueError(
                f"parameter {parameter_index}: unsupported register storage {storage!r}"
            )
        return {
            "kind": "register",
            "storage": storage,
            "register": register,
            "tracked_parent_register": parent,
            "size": int(register_match.group("size")),
            "auto": bool(register_match.group("auto")),
        }

    stack_match = _STACK_STORAGE.fullmatch(storage)
    if stack_match:
        offset = int(stack_match.group("offset"), 16)
        if offset < 0:
            raise ValueError(f"parameter {parameter_index}: invalid stack offset")
        return {
            "kind": "stack",
            "storage": storage,
            "stack_offset": offset,
            "stack_offset_hex": f"0x{offset:x}",
            "size": int(stack_match.group("size")),
            "auto": False,
        }

    raise ValueError(
        f"parameter {parameter_index}: unsupported/composite storage {storage!r}"
    )


def _function_parameter_abi(function: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen_storage: set[str] = set()
    parameters = function.get("parameters") or []
    for index, parameter in enumerate(parameters):
        if not isinstance(parameter, dict):
            raise ValueError(f"parameter {index}: expected object")
        storage = _parse_storage(parameter.get("storage"), parameter_index=index)
        storage_text = str(storage["storage"])
        if storage_text in seen_storage:
            raise ValueError(f"duplicate parameter storage: {storage_text}")
        seen_storage.add(storage_text)
        result.append(
            {
                "ordinal": index,
                "reported_name": parameter.get("name"),
                "reported_type": parameter.get("type"),
                **storage,
                "reported_name_used_as_semantic_role": False,
                "reported_type_used_as_semantic_role": False,
            }
        )
    return result


def _validate_physical_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    target = report.get("target")
    if not isinstance(target, dict):
        raise ValueError("physical report target missing")
    writer = _normalize_address(
        target.get("pose_writer_candidate"), field="target.pose_writer_candidate"
    )
    if writer != POSE_WRITER:
        raise ValueError("physical report pose-writer target drift")

    analysis = report.get("analysis")
    if not isinstance(analysis, dict):
        raise ValueError("physical report analysis missing")
    callsites = analysis.get("callsites")
    if not isinstance(callsites, list) or not callsites:
        raise ValueError("physical report contains no analyzed callsites")
    if analysis.get("all_frontier_callsites_analyzed") is not True:
        raise ValueError("physical report does not cover every frontier callsite")
    if analysis.get("analyzed_callsite_count") != len(callsites):
        raise ValueError("physical report callsite count mismatch")

    handoff = report.get("handoff")
    if not isinstance(handoff, dict) or handoff.get(
        "pose_writer_callsite_register_provenance_ready"
    ) is not True:
        raise ValueError("physical callsite register provenance is not ready")

    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, callsite in enumerate(callsites):
        if not isinstance(callsite, dict):
            raise ValueError(f"callsites[{index}] must be an object")
        caller = _normalize_address(callsite.get("caller"), field=f"callsites[{index}].caller")
        address = _normalize_address(
            callsite.get("callsite"), field=f"callsites[{index}].callsite"
        )
        target_address = _normalize_address(
            callsite.get("target"), field=f"callsites[{index}].target"
        )
        if target_address != POSE_WRITER:
            raise ValueError(f"{caller}:{address}: target drift")
        key = (caller, address)
        if key in seen:
            raise ValueError(f"duplicate physical callsite {caller}:{address}")
        seen.add(key)
        registers = callsite.get("registers_before_call")
        if not isinstance(registers, dict):
            raise ValueError(f"{caller}:{address}: registers_before_call missing")
        normalized.append({**callsite, "caller": caller, "callsite": address})
    normalized.sort(key=lambda row: (int(row["caller"], 0), int(row["callsite"], 0)))
    return normalized


def _register_binding(
    parameter: dict[str, Any],
    callsite: dict[str, Any],
) -> dict[str, Any]:
    parent = parameter["tracked_parent_register"]
    register_row = callsite["registers_before_call"].get(parent)
    if not isinstance(register_row, dict):
        raise ValueError(
            f"{callsite['caller']}:{callsite['callsite']}: physical report does not track {parent}"
        )
    origins = register_row.get("origins")
    if not isinstance(origins, list) or not all(isinstance(value, str) for value in origins):
        raise ValueError(
            f"{callsite['caller']}:{callsite['callsite']}:{parent}: malformed origins"
        )
    exact = bool(
        register_row.get("exact_single_origin") is True
        and register_row.get("contains_unknown_or_derived") is False
        and len(origins) == 1
    )
    return {
        "value_provenance_source": "all-path-register-provenance",
        "tracked_parent_register": parent,
        "origins": list(origins),
        "exact_single_origin": exact,
        "value_provenance_ready": exact,
    }


def join_bmw_body0_bind_pose_writer_abi(
    ghidra_export: Path,
    physical_report_path: Path,
) -> dict[str, Any]:
    physical = _read_json(physical_report_path, PHYSICAL_FORMAT)
    callsites = _validate_physical_report(physical)
    function = _load_pose_writer_function(ghidra_export)
    parameters = _function_parameter_abi(function)

    register_parameters = [row for row in parameters if row["kind"] == "register"]
    stack_parameters = [row for row in parameters if row["kind"] == "stack"]

    joined_callsites: list[dict[str, Any]] = []
    all_register_values_ready = True
    for callsite in callsites:
        bindings: list[dict[str, Any]] = []
        for parameter in parameters:
            binding = {
                "ordinal": parameter["ordinal"],
                "reported_name": parameter["reported_name"],
                "reported_type": parameter["reported_type"],
                "storage": parameter["storage"],
                "storage_kind": parameter["kind"],
                "semantic_role": None,
                "semantic_role_proven": False,
            }
            if parameter["kind"] == "register":
                provenance = _register_binding(parameter, callsite)
                binding.update(provenance)
                all_register_values_ready = (
                    all_register_values_ready and provenance["value_provenance_ready"]
                )
            else:
                binding.update(
                    {
                        "stack_offset": parameter["stack_offset"],
                        "stack_offset_hex": parameter["stack_offset_hex"],
                        "value_provenance_source": None,
                        "origins": [],
                        "exact_single_origin": False,
                        "value_provenance_ready": False,
                    }
                )
            bindings.append(binding)

        joined_callsites.append(
            {
                "caller": callsite["caller"],
                "caller_name": callsite.get("caller_name"),
                "callsite": callsite["callsite"],
                "target": POSE_WRITER,
                "candidate_class": callsite.get("candidate_class"),
                "parameter_bindings": bindings,
                "parameter_storage_binding_ready": True,
                "register_parameter_value_provenance_ready": all(
                    row["value_provenance_ready"]
                    for row in bindings
                    if row["storage_kind"] == "register"
                ),
                "stack_parameter_value_provenance_ready": not any(
                    row["storage_kind"] == "stack" for row in bindings
                ),
                "parameter_semantic_roles_ready": False,
            }
        )

    stack_slots = sorted(
        {
            (row["stack_offset"], row["size"], row["storage"])
            for row in stack_parameters
        }
    )
    stack_worklist = [
        {
            "stack_offset": offset,
            "stack_offset_hex": f"0x{offset:x}",
            "size": size,
            "storage": storage,
            "value_provenance_required_at_every_relevant_callsite": True,
        }
        for offset, size, storage in stack_slots
    ]

    blockers: list[dict[str, Any]] = []
    if stack_worklist:
        blockers.append(
            {
                "id": "pose-writer-stack-argument-value-provenance-unproven",
                "evidence_state": "finite-worklist",
                "stack_slots": [row["storage"] for row in stack_worklist],
                "required_evidence": (
                    "trace the exact value written to each listed FUN_007b7840 stack argument "
                    "at every relevant caller using path-aware ESP/stack provenance"
                ),
            }
        )
    if not all_register_values_ready:
        blockers.append(
            {
                "id": "pose-writer-register-argument-value-provenance-ambiguous",
                "evidence_state": "blocked",
                "required_evidence": (
                    "resolve non-single or unknown register origins at the affected callsites"
                ),
            }
        )
    blockers.extend(
        [
            {
                "id": "pose-writer-parameter-semantic-roles-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "prove which ABI parameter controls the BODY target, flags and source pose values "
                    "from FUN_007b7840 machine/p-code behavior; do not infer roles from ordinal/name"
                ),
            },
            {
                "id": "BODY0-pointer-at-bind-callsite-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "join the proven BODY-target parameter value to exact BMW chassis BODY index 0"
                ),
            },
            {
                "id": "bind-origin-basis-value-provenance-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "trace bind-time origin/basis parameter values through the selected initialization callsite"
                ),
            },
        ]
    )

    return {
        "format": FORMAT,
        "inputs": {
            "ghidra_export": str(ghidra_export),
            "physical_callsite_provenance": str(physical_report_path),
        },
        "pose_writer": {
            "address": POSE_WRITER,
            "name": function.get("name"),
            "calling_convention": function.get("calling_convention"),
            "reported_signature": function.get("signature"),
            "parameter_count": len(parameters),
            "register_parameter_count": len(register_parameters),
            "stack_parameter_count": len(stack_parameters),
            "parameters": parameters,
            "reported_parameter_names_used_as_semantic_roles": False,
            "reported_parameter_types_used_as_semantic_roles": False,
        },
        "analysis": {
            "callsite_count": len(joined_callsites),
            "callsites": joined_callsites,
            "all_callsites_parameter_storage_bound": bool(joined_callsites),
            "all_register_parameter_values_ready": all_register_values_ready,
            "stack_value_worklist": stack_worklist,
        },
        "handoff": {
            "pose_writer_parameter_storage_binding_ready": bool(joined_callsites),
            "pose_writer_register_argument_provenance_ready": all_register_values_ready,
            "pose_writer_stack_argument_locations_ready": True,
            "pose_writer_stack_argument_values_ready": not stack_worklist,
            "pose_writer_ABI_semantic_roles_ready": False,
            "BODY0_pointer_at_bind_callsite_ready": False,
            "BODY0_bind_origin_basis_values_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "next_required_join": (
                "path-aware stack-value provenance + FUN_007b7840 parameter role proof"
                if stack_worklist
                else "FUN_007b7840 parameter role proof"
            ),
        },
        "blockers": blockers,
        "scope": {
            "ghidra_calling_convention_observed": True,
            "ghidra_physical_parameter_storage_observed": True,
            "all_path_register_provenance_reused": True,
            "register_position_used_as_semantic_role": False,
            "parameter_ordinal_used_as_semantic_role": False,
            "reported_parameter_name_trusted_as_semantics": False,
            "reported_parameter_type_trusted_as_semantics": False,
            "stack_value_provenance_inferred": False,
            "pose_writer_candidate_promoted_to_initializer": False,
            "BODY0_pointer_identity_proven": False,
            "BODY0_bind_matrix_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("physical_callsite_provenance", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = join_bmw_body0_bind_pose_writer_abi(
        args.ghidra_export,
        args.physical_callsite_provenance,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
