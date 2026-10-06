#!/usr/bin/env python3
"""Bound the exact Vehicle::InitVehicle input frontier for the BMW render-root delta.

``SHIFT.OuterVehicleBMWVHFRootRelation/1`` proves that the remaining numeric
outer->VHF relation is determined by the setup-fixed translation stored by
``FUN_00795d60`` at outer Vehicle +0x19c/+0x1a0/+0x1a4.  The retail source call
from ``MWL::Core::Vehicle::InitVehicle`` is already source-backed as:

    FUN_00795d60(this,param_1,local_2390,
                 *(void **)((int)this + 0x1d00),param_1);

The missing numeric proof is therefore not a broad frame/ownership question.  It
is the value provenance of one stack local, ``local_2390``, before the unique
retail callsite ``0x007990ed``.

This analyzer consumes the exact retail Ghidra evidence database and the exact
retail decompiler source SHA.  It extracts the concrete ``FUN_00798df0`` function
body, proves the unique target call, enumerates every pre-call source reference
to ``local_2390``, and joins any ``FUN_xxxxxxxx`` call reference to the direct
retail callgraph when possible.  The result is a finite producer worklist only:
source lexical order is not all-path value proof, passing a pointer is not proof
that a callee writes it, and no numeric delta is invented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.OuterVehicleRenderRootDeltaInitVehicleInputFrontier/1"
RELATION_FORMAT = "SHIFT.OuterVehicleBMWVHFRootRelation/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"

INIT = "0x00798df0"
INIT_NAME = "FUN_00798df0"
INIT_SIZE = 1581
INIT_CC = "__thiscall"
INIT_MNEMONIC_SHA256 = "88904019443d1ea4edaf5a3ef40dd5abfe9e28109ab0b1f09296388f36026e16"
INIT_SOURCE_LABEL = "MWL::Core::Vehicle::InitVehicle"
INIT_SOURCE_FILE = ".\\Source\\Vehicle\\Vehicle.cpp"

DELTA = "0x00795d60"
DELTA_NAME = "FUN_00795d60"
DELTA_SIZE = 8797
DELTA_CC = "__fastcall"
DELTA_MNEMONIC_SHA256 = "c587cae5d3d8f99afed40fe0c059c8c60bc9cc45d9ee644f5e90e2e1f5a8eb14"
DELTA_CALLSITE = "0x007990ed"
DELTA_LOCAL = "local_2390"
DELTA_FIELDS = ["outerVehicle+0x19c", "outerVehicle+0x1a0", "outerVehicle+0x1a4"]
EXPECTED_CALL_COMPACT = (
    "FUN_00795d60(this,param_1,local_2390,"
    "*(void**)((int)this+0x1d00),param_1);"
)

DEFAULT_RELATION = (
    Path(__file__).resolve().parents[2]
    / "evidence"
    / "process1_outer_vehicle_bmw_vhf_root_relation.json"
)

_FUN_TOKEN = re.compile(r"\bFUN_([0-9a-fA-F]{8})\b")
_LOCAL_ASSIGN = re.compile(r"\blocal_2390(?:\s*\[[^\]]+\])?\s*=")
_LOCAL_DECL = re.compile(
    r"^(?:[A-Za-z_][A-Za-z0-9_]*(?:\s+|\s*\*\s*))+local_2390(?:\s*\[[^\]]+\])?\s*;?$"
)
_CALL_TOKEN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_:]*)\s*\(")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            text = raw.strip()
            if not text:
                continue
            value = json.loads(text)
            _require(isinstance(value, dict), f"{path}:{line_no}: expected JSON object")
            rows.append(value)
    return rows


def _norm_address(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text.startswith("fun_"):
        text = text[4:]
    if text.startswith("0x"):
        text = text[2:]
    try:
        return f"0x{int(text, 16):08x}"
    except ValueError as exc:
        raise ValueError(f"invalid address {value!r}") from exc


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _validate_relation(path: Path) -> dict[str, Any]:
    relation = _read_json(path)
    _require(
        relation.get("format") == RELATION_FORMAT
        and relation.get("ready") is True
        and relation.get("status") == "outer-vehicle-bmw-vhf-fixed-affine-relation-proven",
        f"{path}: expected positive {RELATION_FORMAT}",
    )
    _require(relation.get("semantic_authority") == "Process 1", "outer/VHF semantic authority drift")
    row = relation.get("relation")
    _require(isinstance(row, Mapping), "outer/VHF relation payload missing")
    _require(row.get("kind") == "fixed_affine", "outer/VHF relation must remain setup-fixed affine")
    _require(row.get("delta_producer") == DELTA_NAME, "outer/VHF delta producer drift")
    _require(row.get("delta_local_source") == DELTA_FIELDS, "outer/VHF delta source-field drift")
    _require(row.get("delta_lifetime") == "Vehicle::InitVehicle/setup state; not runtime pose", "outer/VHF delta lifetime drift")
    _require(row.get("relation_matrix_numeric_ready") is False, "relation unexpectedly already has numeric matrix")
    proof = relation.get("proof")
    _require(isinstance(proof, Mapping), "outer/VHF relation proof missing")
    _require(proof.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is True, "outer/VHF semantic relation not ready")
    _require(proof.get("outer_vehicle_root_to_VHF_fixed_affine_delta_ready") is True, "outer/VHF fixed-affine relation not ready")
    handoff = relation.get("handoff")
    _require(isinstance(handoff, Mapping), "outer/VHF relation handoff missing")
    _require(handoff.get("outer_vehicle_root_to_VHF_relation_numeric_matrix_ready") is False, "numeric relation unexpectedly preclaimed")
    _require(handoff.get("BODY0_bind_frame_proof_ready") is False, "relation unexpectedly preclaims BODY0 bind proof")
    lifecycle = relation.get("static_lifecycle_provenance")
    _require(isinstance(lifecycle, Mapping), "relation static lifecycle provenance missing")
    init = lifecycle.get(INIT_NAME)
    delta = lifecycle.get(DELTA_NAME)
    _require(isinstance(init, Mapping) and isinstance(delta, Mapping), "relation InitVehicle/delta lifecycle rows missing")
    _require(_norm_address(init.get("address")) == INIT, "relation InitVehicle address drift")
    _require(init.get("mnemonic_sha256") == INIT_MNEMONIC_SHA256, "relation InitVehicle fingerprint drift")
    _require(init.get("source_label") == INIT_SOURCE_LABEL, "relation InitVehicle source label drift")
    _require(_norm_address(delta.get("address")) == DELTA, "relation delta function address drift")
    _require(delta.get("mnemonic_sha256") == DELTA_MNEMONIC_SHA256, "relation delta fingerprint drift")
    _require(delta.get("unique_direct_caller") == INIT_NAME, "relation delta unique caller drift")
    _require(_norm_address(delta.get("callsite")) == DELTA_CALLSITE, "relation delta callsite drift")
    return relation


def _validate_binary(root: Path) -> None:
    binary = _read_json(root / "binary.json")
    _require(binary.get("program_name") == PROGRAM, "unexpected retail program name")
    _require(binary.get("executable_md5") == PE_MD5, "unexpected retail executable identity")


def _function_row(rows: list[dict[str, Any]], address: str) -> dict[str, Any]:
    hits = [row for row in rows if _norm_address(row.get("address")) == address]
    _require(len(hits) == 1, f"expected exactly one function row for {address}; found {len(hits)}")
    return hits[0]


def _validate_functions(root: Path) -> dict[str, dict[str, Any]]:
    rows = _read_jsonl(root / "functions.jsonl")
    expected = {
        INIT: (INIT_NAME, INIT_SIZE, INIT_CC, INIT_MNEMONIC_SHA256),
        DELTA: (DELTA_NAME, DELTA_SIZE, DELTA_CC, DELTA_MNEMONIC_SHA256),
    }
    result: dict[str, dict[str, Any]] = {}
    for address, (name, size, cc, fingerprint) in expected.items():
        row = _function_row(rows, address)
        _require(row.get("name") == name, f"{address}: function name drift")
        _require(row.get("size") == size, f"{address}: function size drift")
        _require(row.get("calling_convention") == cc, f"{address}: calling convention drift")
        _require(row.get("mnemonic_sha256") == fingerprint, f"{address}: mnemonic fingerprint drift")
        _require(row.get("thunk") is not True and row.get("external") is not True, f"{address}: expected concrete retail function")
        result[address] = row
    return result


def _validate_source_labels(root: Path) -> list[dict[str, Any]]:
    rows = _read_jsonl(root / "strings_xrefs.jsonl")
    result: list[dict[str, Any]] = []
    for value in (INIT_SOURCE_FILE, INIT_SOURCE_LABEL):
        hits = [row for row in rows if row.get("value") == value]
        _require(len(hits) == 1, f"expected exactly one source-label row {value!r}; found {len(hits)}")
        row = hits[0]
        functions = [_norm_address(item) for item in row.get("functions") or []]
        _require(INIT in functions, f"source label {value!r} is not xref-owned by {INIT_NAME}")
        result.append({
            "value": value,
            "address": _norm_address(row.get("address")),
            "xrefs": list(row.get("xrefs") or []),
            "functions": functions,
        })
    return result


def _validate_callgraph(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = _read_jsonl(root / "callgraph.jsonl")
    init_calls = [
        row for row in rows
        if _norm_address(row.get("from_function")) == INIT and row.get("indirect") is False
    ]
    target = [
        row for row in init_calls
        if _norm_address(row.get("instruction")) == DELTA_CALLSITE
        and _norm_address(row.get("to")) == DELTA
    ]
    _require(len(target) == 1, f"expected exact direct call {INIT}:{DELTA_CALLSITE}->{DELTA}; found {len(target)}")
    same_site = [row for row in init_calls if _norm_address(row.get("instruction")) == DELTA_CALLSITE]
    _require(len(same_site) == 1, "InitVehicle delta callsite is ambiguous")
    callers = [
        row for row in rows
        if _norm_address(row.get("to")) == DELTA and row.get("indirect") is False
    ]
    _require(len(callers) == 1, f"expected one direct caller of {DELTA_NAME}; found {len(callers)}")
    _require(_norm_address(callers[0].get("from_function")) == INIT, "delta direct caller is not InitVehicle")
    before = sorted(
        [
            {
                "instruction": _norm_address(row.get("instruction")),
                "to": _norm_address(row.get("to")),
                "to_name": row.get("to_name"),
            }
            for row in init_calls
            if int(_norm_address(row.get("instruction")), 0) < int(DELTA_CALLSITE, 0)
        ],
        key=lambda row: int(row["instruction"], 0),
    )
    return {
        "from_function": INIT,
        "from_name": INIT_NAME,
        "instruction": DELTA_CALLSITE,
        "to": DELTA,
        "to_name": DELTA_NAME,
        "unique_direct_caller": True,
        "callsite_unambiguous": True,
    }, before


def _skip_c_space(text: str, index: int) -> int:
    length = len(text)
    while index < length:
        if text[index].isspace():
            index += 1
            continue
        if text.startswith("//", index):
            end = text.find("\n", index + 2)
            return length if end < 0 else _skip_c_space(text, end + 1)
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            _require(end >= 0, "unterminated C block comment")
            index = end + 2
            continue
        break
    return index


def _match_pair(text: str, start: int, opener: str, closer: str) -> int:
    _require(start < len(text) and text[start] == opener, f"expected {opener!r}")
    depth = 0
    index = start
    quote: str | None = None
    escaped = False
    while index < len(text):
        ch = text[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            index += 1
            continue
        if text.startswith("//", index):
            end = text.find("\n", index + 2)
            if end < 0:
                return -1
            index = end + 1
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            _require(end >= 0, "unterminated C block comment")
            index = end + 2
            continue
        if ch in ('"', "'"):
            quote = ch
            index += 1
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def _function_body(source: str, name: str) -> tuple[int, int, str]:
    definitions: list[tuple[int, int]] = []
    for hit in re.finditer(rf"\b{re.escape(name)}\s*\(", source):
        open_paren = source.find("(", hit.start())
        close_paren = _match_pair(source, open_paren, "(", ")")
        if close_paren < 0:
            continue
        after = _skip_c_space(source, close_paren + 1)
        if after >= len(source) or source[after] != "{":
            continue
        close_brace = _match_pair(source, after, "{", "}")
        _require(close_brace >= 0, f"unterminated function body for {name}")
        definitions.append((after + 1, close_brace))
    _require(len(definitions) == 1, f"expected exactly one source definition for {name}; found {len(definitions)}")
    start, end = definitions[0]
    return start, end, source[start:end]


def _line_rows(source: str, body_start: int, body: str) -> list[dict[str, Any]]:
    base_line = source.count("\n", 0, body_start) + 1
    return [
        {
            "source_line": base_line + index,
            "text": line.strip(),
            "compact": _compact(line),
        }
        for index, line in enumerate(body.splitlines())
    ]


def _callee_addresses(line: str) -> list[str]:
    return sorted({_norm_address(f"0x{match.group(1)}") for match in _FUN_TOKEN.finditer(line)})


def _classify_reference(row: Mapping[str, Any], *, target_line: int) -> dict[str, Any]:
    text = str(row.get("text") or "")
    compact = str(row.get("compact") or "")
    callees = _callee_addresses(text)
    if row.get("source_line") == target_line:
        kind = "target-delta-call"
        producer_candidate = False
    elif _LOCAL_DECL.fullmatch(text):
        kind = "local-declaration"
        producer_candidate = False
    elif _LOCAL_ASSIGN.search(text):
        kind = "direct-local-write"
        producer_candidate = True
    elif callees:
        kind = "direct-function-call-reference"
        producer_candidate = True
    elif any(token not in {"if", "while", "for", "switch", "sizeof"} for token in _CALL_TOKEN.findall(text)):
        kind = "other-call-reference"
        producer_candidate = True
    else:
        kind = "other-local-reference"
        producer_candidate = False
    return {
        "source_line": row.get("source_line"),
        "text": text,
        "compact": compact,
        "kind": kind,
        "producer_candidate": producer_candidate,
        "direct_fun_targets": callees,
    }


def _join_candidate_calls(
    candidates: list[dict[str, Any]],
    calls_before_target: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_target: dict[str, list[dict[str, Any]]] = {}
    for call in calls_before_target:
        by_target.setdefault(str(call["to"]), []).append(call)
    result: list[dict[str, Any]] = []
    for row in candidates:
        joins: list[dict[str, Any]] = []
        for target in row.get("direct_fun_targets") or []:
            hits = by_target.get(str(target), [])
            joins.append({
                "target": target,
                "matching_pre_delta_direct_calls": hits,
                "unique_pre_delta_direct_call": len(hits) == 1,
            })
        result.append({**row, "direct_callgraph_joins": joins})
    return result


def analyze(
    ghidra_root: Path,
    source_path: Path,
    relation_path: Path = DEFAULT_RELATION,
) -> dict[str, Any]:
    relation = _validate_relation(relation_path)
    _validate_binary(ghidra_root)
    functions = _validate_functions(ghidra_root)
    source_labels = _validate_source_labels(ghidra_root)
    target_call, calls_before = _validate_callgraph(ghidra_root)

    source_sha = _sha256_file(source_path)
    _require(source_sha == SOURCE_SHA256, "unexpected retail decompiler source SHA-256")
    source = source_path.read_text(encoding="utf-8", errors="strict")
    body_start, _, body = _function_body(source, INIT_NAME)
    rows = _line_rows(source, body_start, body)
    references = [row for row in rows if DELTA_LOCAL in row["text"]]
    _require(references, f"{INIT_NAME}: no source references to {DELTA_LOCAL}")

    target_refs = [row for row in references if DELTA_NAME in row["text"]]
    _require(len(target_refs) == 1, f"{INIT_NAME}: expected one source delta call reference; found {len(target_refs)}")
    target_row = target_refs[0]
    _require(target_row["compact"] == EXPECTED_CALL_COMPACT, "InitVehicle source delta call statement drift")
    target_line = int(target_row["source_line"])

    pre_refs = [row for row in references if int(row["source_line"]) < target_line]
    post_refs = [row for row in references if int(row["source_line"]) > target_line]
    classified = [_classify_reference(row, target_line=target_line) for row in [*pre_refs, target_row, *post_refs]]
    pre_classified = [row for row in classified if int(row["source_line"]) < target_line]
    producers = [row for row in pre_classified if row["producer_candidate"] is True]
    producers = _join_candidate_calls(producers, calls_before)

    unresolved = [
        row for row in pre_classified
        if row["kind"] == "other-local-reference"
    ]
    direct_fun_targets = sorted({
        target
        for row in producers
        for target in row.get("direct_fun_targets") or []
    }, key=lambda value: int(value, 0))

    blockers: list[dict[str, Any]] = []
    if unresolved:
        blockers.append({
            "id": "initvehicle-local2390-unclassified-precall-reference",
            "count": len(unresolved),
            "required_evidence": "classify whether each remaining local_2390 pre-call reference can affect the value observed by FUN_00795d60",
        })
    blockers.append({
        "id": "initvehicle-local2390-producer-values-not-materialized",
        "producer_candidate_count": len(producers),
        "direct_fun_target_worklist": direct_fun_targets,
        "required_evidence": "trace only these exact local_2390 producer candidates through targeted instructions/source values to the three setup scalars consumed by FUN_00795d60",
    })

    return {
        "format": FORMAT,
        "version": 1,
        "status": "initvehicle-delta-input-frontier-ready",
        "ready": True,
        "BLOCKER": "BMW render-root delta numeric materialization for the selected BMW native session",
        "INPUT": {
            "outer_vehicle_bmw_vhf_root_relation": RELATION_FORMAT,
            "retail_ghidra_database": "SHIFT.GhidraEvidenceDatabase/1",
            "retail_decompiler_source_sha256": SOURCE_SHA256,
        },
        "OUTPUT": "finite pre-call source/value worklist for InitVehicle local_2390 passed to FUN_00795d60 param3",
        "CONSUMER": "Process 1 targeted producer-value slice -> provenance-bearing finite outer->VHF relation matrix",
        "retail": {
            "program": PROGRAM,
            "md5": PE_MD5,
            "source_sha256": source_sha,
            "functions": {
                INIT_NAME: {
                    "address": INIT,
                    "size": INIT_SIZE,
                    "calling_convention": INIT_CC,
                    "mnemonic_sha256": INIT_MNEMONIC_SHA256,
                    "signature": functions[INIT].get("signature"),
                },
                DELTA_NAME: {
                    "address": DELTA,
                    "size": DELTA_SIZE,
                    "calling_convention": DELTA_CC,
                    "mnemonic_sha256": DELTA_MNEMONIC_SHA256,
                    "signature": functions[DELTA].get("signature"),
                },
            },
            "source_labels": source_labels,
        },
        "binding": {
            "caller": INIT_NAME,
            "caller_address": INIT,
            "callsite": DELTA_CALLSITE,
            "callee": DELTA_NAME,
            "callee_address": DELTA,
            "callee_param3_source_local": DELTA_LOCAL,
            "source_call_statement": target_row["text"],
            "source_call_line": target_line,
            "source_call_compact": target_row["compact"],
            "callgraph_witness": target_call,
            "source_to_callsite_binding_ready": True,
            "stack_argument_numeric_value_proven": False,
        },
        "source_reference_frontier": {
            "pre_call_reference_count": len(pre_refs),
            "post_call_reference_count": len(post_refs),
            "producer_candidate_count": len(producers),
            "unclassified_pre_call_reference_count": len(unresolved),
            "references": classified,
            "producer_candidates": producers,
            "direct_fun_target_worklist": direct_fun_targets,
            "lexical_source_order_is_all_path_value_proof": False,
            "pointer_argument_implies_callee_write": False,
        },
        "relation_context": {
            "format": relation.get("format"),
            "kind": (relation.get("relation") or {}).get("kind"),
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": True,
            "outer_vehicle_root_to_VHF_relation_numeric_matrix_ready": False,
        },
        "handoff": {
            "initvehicle_delta_param3_source_local_binding_ready": True,
            "initvehicle_delta_input_reference_frontier_ready": True,
            "initvehicle_delta_input_producer_worklist_ready": bool(producers),
            "selected_BMW_render_root_delta_numeric_ready": False,
            "outer_vehicle_root_to_VHF_relation_numeric_matrix_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "scope": {
            "broad_resource_audit_performed": False,
            "frame_semantics_reopened": False,
            "callgraph_adjacency_used_as_value_proof": False,
            "source_lexical_order_used_as_all_path_proof": False,
            "numeric_delta_invented": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_root", type=Path)
    parser.add_argument("shift_source", type=Path)
    parser.add_argument("--relation", type=Path, default=DEFAULT_RELATION)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = analyze(args.ghidra_root, args.shift_source, args.relation)
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
