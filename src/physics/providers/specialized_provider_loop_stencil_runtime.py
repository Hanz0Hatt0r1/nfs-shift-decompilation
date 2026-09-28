"""Extract loop-based update stencils from specialized SHIFT provider solvers.

A stencil records the source-order loop range, the dVar1 loader form, and the
workspace destinations updated under that loader. Numeric RHS expressions are
not emitted. This phase is deliberately structural because provider workspace
packing has unresolved aliasing between logical cells.
"""
from __future__ import annotations

import re
from typing import Any

from specialized_provider_factor_pattern_runtime import (
    ARRAY_LHS_RE,
    DIRECT_LHS_RE,
    LOOP_HEADER_RE,
    LOOP_LHS_RE,
)
from specialized_provider_solver_fingerprint_runtime import (
    extract_function_body,
    extract_reciprocal_pivots,
)
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderLoopStencilRuntime/1"

SOLVER_SPECS = {
    0: {
        "function": "FUN_007c7200",
        "next_function_marker": "undefined4 * __fastcall FUN_007cd980",
    },
    1: {
        "function": "FUN_007cdfc0",
        "next_function_marker": "undefined * __fastcall FUN_007d2e70",
    },
}

DVAR_ASSIGN_RE = re.compile(r"\bdVar1\s*=\s*(.+?);\s*$")


def _function_spec(provider_id: int) -> dict[str, Any]:
    try:
        return dict(SOLVER_SPECS[provider_id])
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc


def _lhs_match(line: str) -> re.Match[str] | None:
    return (
        LOOP_LHS_RE.search(line)
        or ARRAY_LHS_RE.search(line)
        or DIRECT_LHS_RE.match(line)
    )


def _assignment_statement(
    lines: list[str],
    index: int,
) -> str:
    statement = lines[index].strip()
    cursor = index
    while ";" not in statement and cursor + 1 < len(lines):
        cursor += 1
        statement += " " + lines[cursor].strip()
    return statement


def _scale_source(expression: str) -> dict[str, Any]:
    row_pointer = re.search(
        r"\*\(double \*\)\(\*\(int \*\)\(&DAT_([0-9A-Fa-f]+)"
        r"\s*\+\s*local_10\s*\*\s*4\)\s*\+\s*"
        r"(0x[0-9A-Fa-f]+|\d+)\)",
        expression,
    )
    if row_pointer:
        return {
            "form": "row-pointer-offset",
            "table_base": hex(int(row_pointer.group(1), 16)),
            "offset": hex(int(row_pointer.group(2), 0)),
        }

    flat_pointer = re.search(
        r"\*\(double \*\)\(&DAT_([0-9A-Fa-f]+)"
        r"\s*\+\s*local_10\s*\*\s*8\)",
        expression,
    )
    if flat_pointer:
        return {
            "form": "flat-pointer",
            "base": hex(int(flat_pointer.group(1), 16)),
        }

    direct = re.search(r"(?:_)?DAT_([0-9A-Fa-f]+)", expression)
    if direct:
        return {
            "form": "direct-dat",
            "address": hex(int(direct.group(1), 16)),
        }

    return {
        "form": "opaque",
    }


def _destination_form(
    statement: str,
) -> tuple[str, int] | None:
    match = LOOP_LHS_RE.search(statement)
    if match:
        return "loop-pointer", int(match.group(1), 16)

    match = ARRAY_LHS_RE.search(statement)
    if match:
        return "loop-array", int(match.group(1), 16)

    match = DIRECT_LHS_RE.match(statement)
    if match:
        return "direct", int(match.group(1), 16)

    return None


def extract_loop_stencils(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    spec = _function_spec(provider_id)
    body, source_start_line = extract_function_body(
        source,
        spec["function"],
        next_function_marker=spec["next_function_marker"],
    )
    lines = body.splitlines()
    pivots = extract_reciprocal_pivots(
        lines,
        first_source_line=source_start_line,
    )
    layout = get_storage_layout(provider_id)

    errors: list[str] = []
    if len(pivots) != layout.scalar_count:
        errors.append(
            f"pivot-count:expected={layout.scalar_count}:actual={len(pivots)}"
        )

    stencils: list[dict[str, Any]] = []
    for pivot_index, pivot in enumerate(pivots):
        next_line = (
            pivots[pivot_index + 1].source_line
            if pivot_index + 1 < len(pivots)
            else source_start_line + len(lines)
        )
        block_start = pivot.source_line - source_start_line
        block_end = next_line - source_start_line
        block = lines[block_start:block_end]

        active_range: tuple[int, int] | None = None
        active_depth: int | None = None
        brace_depth = 0
        scale_source: dict[str, Any] | None = None

        for local_index, line in enumerate(block):
            loop = LOOP_HEADER_RE.search(line)
            if loop:
                active_range = (
                    int(loop.group(1), 0),
                    int(loop.group(2), 0),
                )
                active_depth = brace_depth + 1

            dvar = DVAR_ASSIGN_RE.search(line.strip())
            if dvar:
                scale_source = _scale_source(dvar.group(1))

            match = _lhs_match(line)
            if match is not None:
                statement = _assignment_statement(block, local_index)
                destination = _destination_form(statement)
                if destination is not None and scale_source is not None:
                    form, base = destination
                    loop_values = (
                        tuple(range(*active_range))
                        if active_range is not None
                        and form in {"loop-pointer", "loop-array"}
                        else (None,)
                    )

                    for loop_index in loop_values:
                        if form in {"loop-pointer", "loop-array"}:
                            assert loop_index is not None
                            address = base + loop_index * 8
                        else:
                            address = base

                        if (
                            layout.output_vector_base
                            <= address
                            < layout.output_vector_base + layout.output_vector_bytes
                        ):
                            continue

                        if form in {"loop-pointer", "loop-array"} and loop_index is not None:
                            if loop_index < 0 or loop_index >= layout.scalar_count:
                                errors.append(
                                    f"pivot-{pivot_index}-loop-index-out-of-domain:{loop_index}"
                                )

                        stencils.append(
                            {
                                "pivot_index": pivot_index,
                                "source_line": pivot.source_line + local_index,
                                "loop_index": (
                                    None
                                    if loop_index is None
                                    else int(loop_index)
                                ),
                                "loop_range": (
                                    None
                                    if active_range is None
                                    else {
                                        "start": active_range[0],
                                        "end": active_range[1],
                                    }
                                ),
                                "scale_source": dict(scale_source),
                                "destination": {
                                    "form": form,
                                    "address": hex(address),
                                },
                            }
                        )

            brace_depth += line.count("{") - line.count("}")
            if (
                active_range is not None
                and active_depth is not None
                and brace_depth < active_depth
            ):
                active_range = None
                active_depth = None

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "function": spec["function"],
        "source_start_line": source_start_line,
        "source_line_count": len(lines),
        "scalar_count": layout.scalar_count,
        "stencils": stencils,
        "ready": not errors,
        "errors": errors,
    }


def summarize_loop_stencils(report: dict[str, Any]) -> dict[str, Any]:
    stencils = report.get("stencils") or []
    forms: dict[str, int] = {}
    scales: dict[str, int] = {}
    for stencil in stencils:
        destination_form = str(
            (stencil.get("destination") or {}).get("form")
        )
        forms[destination_form] = forms.get(destination_form, 0) + 1
        scale_form = str(
            (stencil.get("scale_source") or {}).get("form")
        )
        scales[scale_form] = scales.get(scale_form, 0) + 1

    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "stencil_count": len(stencils),
        "destination_forms": dict(sorted(forms.items())),
        "scale_source_forms": dict(sorted(scales.items())),
        "ready": bool(report.get("ready")),
    }


def validate_loop_stencils(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))

    for index, stencil in enumerate(report.get("stencils") or []):
        destination = stencil.get("destination") or {}
        if destination.get("address") is None:
            errors.append(f"stencil-{index}-missing-destination-address")

        loop_index = stencil.get("loop_index")
        if loop_index is not None:
            loop_index = int(loop_index)
            if loop_index < 0 or loop_index >= scalar_count:
                errors.append(f"stencil-{index}-loop-index-out-of-domain")

        if not (stencil.get("scale_source") or {}).get("form"):
            errors.append(f"stencil-{index}-missing-scale-form")

    return {
        "format": "SHIFT.SpecializedProviderLoopStencilValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
        "stencils": len(report.get("stencils") or []),
    }


def build_loop_stencil_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = extract_loop_stencils(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_loop_stencils(report)
        report["validation"] = validate_loop_stencils(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "scope": {
            "representation": "loop-indexed workspace update stencil",
            "dVar1": "source form classified but numeric expression text omitted",
            "destination": "absolute workspace address per expanded loop iteration",
        },
        "limitations": [
            "This phase does not assign semantic matrix roles to workspace addresses.",
            "Loop-local dVar1 loaders are classified structurally; their numeric RHS expression is omitted.",
            "Destination address aliasing across packed provider storage remains unresolved.",
        ],
        "status": "source-backed-loop-update-stencils",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_loop_stencil_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
