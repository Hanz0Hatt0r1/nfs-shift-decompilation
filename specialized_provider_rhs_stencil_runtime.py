"""Normalize source-level RHS reference patterns for specialized SHIFT solvers.

Phase 441 stays one boundary beyond Phase 440: it resolves assignment LHS/RHS
references without copying the proprietary numeric expressions. Loop-indexed
references are expanded to concrete provider workspace/output coordinates.

The output is intended as a reconstruction aid for a later fixed-layout numeric
solver, not as a claim about undocumented semantic names or units.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from specialized_provider_row_storage_runtime import build_row_segments
from specialized_provider_storage_runtime import get_storage_layout
from specialized_provider_solver_fingerprint_runtime import (
    extract_function_body,
    extract_reciprocal_pivots,
)
from specialized_provider_update_graph_runtime import extract_update_graph

FORMAT = "SHIFT.SpecializedProviderRHSStencilRuntime/1"

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

LOOP_HEADER_RE = re.compile(
    r"for\s*\(\s*local_10\s*=\s*(0x[0-9A-Fa-f]+|\d+)\s*;\s*"
    r"local_10\s*<\s*(0x[0-9A-Fa-f]+|\d+)\s*;"
)

LOOP_PTR_LHS_RE = re.compile(
    r"\*\(double \*\)\(&DAT_([0-9A-Fa-f]+)\s*\+\s*"
    r"local_10\s*\*\s*8\)\s*="
)

ARRAY_LHS_RE = re.compile(
    r"\(&DAT_([0-9A-Fa-f]+)\)\[local_10\]\s*="
)

DIRECT_LHS_RE = re.compile(
    r"^\s*(?:_)?DAT_([0-9A-Fa-f]+)\s*="
)

ROWPTR_OFFSET_RE = re.compile(
    r"\*\(double \*\)\(\*\(int \*\)\(&DAT_([0-9A-Fa-f]+)\s*\+\s*"
    r"local_10\s*\*\s*4\)\s*\+\s*(0x[0-9A-Fa-f]+|\d+)\)"
)

ROWPTR_BASE_RE = re.compile(
    r"\*\*\(double \*\*\)\(&DAT_([0-9A-Fa-f]+)\s*\+\s*local_10\s*\*\s*4\)"
)

DYNAMIC_PTR_RE = re.compile(
    r"\*\(double \*\)\(&DAT_([0-9A-Fa-f]+)\s*\+\s*local_10\s*\*\s*8\)"
)

ARRAY_REF_RE = re.compile(
    r"\(&DAT_([0-9A-Fa-f]+)\)\[local_10\]"
)

DIRECT_ADDR_RE = re.compile(r"(?:_)?DAT_([0-9A-Fa-f]+)")


@dataclass(frozen=True)
class Reference:
    domain: str
    form: str
    address: int | None = None
    row: int | None = None
    column: int | None = None
    index: int | None = None

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "domain": self.domain,
            "form": self.form,
        }
        if self.address is not None:
            data["address"] = hex(self.address)
        if self.row is not None:
            data["row"] = self.row
        if self.column is not None:
            data["column"] = self.column
        if self.index is not None:
            data["index"] = self.index
        return data


@dataclass(frozen=True)
class AssignmentStencil:
    pivot_index: int
    source_line: int
    loop_index: int | None
    destination: Reference
    rhs: tuple[Reference, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "pivot_index": self.pivot_index,
            "source_line": self.source_line,
            "loop_index": self.loop_index,
            "destination": self.destination.as_dict(),
            "rhs": [reference.as_dict() for reference in self.rhs],
        }


def _parse_int(value: str) -> int:
    return int(value, 0)


def _function_spec(provider_id: int) -> dict[str, Any]:
    try:
        return dict(SOLVER_SPECS[provider_id])
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc


def _locate_address(address: int, provider_id: int) -> Reference:
    layout = get_storage_layout(provider_id)
    for segment in build_row_segments(provider_id):
        if segment.start <= address < segment.end:
            delta = address - segment.start
            if delta % 8:
                return Reference("global", "unaligned", address=address)
            return Reference(
                "workspace",
                "direct",
                address=address,
                row=segment.row,
                column=delta // 8,
            )

    output_start = layout.output_vector_base
    output_end = output_start + layout.output_vector_bytes
    if output_start <= address < output_end and (address - output_start) % 8 == 0:
        return Reference(
            "output_vector",
            "direct",
            address=address,
            index=(address - output_start) // 8,
        )

    return Reference("global", "direct", address=address)


def _resolve_loop_address(
    base: int,
    loop_index: int,
    *,
    provider_id: int,
    form: str,
) -> Reference:
    address = base + loop_index * 8
    reference = _locate_address(address, provider_id)
    return Reference(
        domain=reference.domain,
        form=form,
        address=address,
        row=reference.row,
        column=reference.column,
        index=reference.index,
    )


def _rhs_references(
    rhs: str,
    *,
    provider_id: int,
    loop_index: int,
) -> tuple[Reference, ...]:
    references: list[Reference] = []
    masked = list(rhs)
    segments = build_row_segments(provider_id)

    def consume(match: re.Match[str]) -> None:
        start, end = match.span()
        for offset in range(start, end):
            masked[offset] = " "

    for match in ROWPTR_OFFSET_RE.finditer(rhs):
        row = loop_index
        if row >= len(segments):
            raise ValueError(f"row-pointer index out of range: {row}")
        offset = _parse_int(match.group(2))
        address = segments[row].start + offset
        reference = _locate_address(address, provider_id)
        references.append(
            Reference(
                domain=reference.domain,
                form="row-pointer-offset",
                address=address,
                row=reference.row,
                column=reference.column,
                index=reference.index,
            )
        )
        consume(match)

    for match in ROWPTR_BASE_RE.finditer(rhs):
        row = loop_index
        if row >= len(segments):
            raise ValueError(f"row-pointer index out of range: {row}")
        address = segments[row].start
        reference = _locate_address(address, provider_id)
        references.append(
            Reference(
                domain=reference.domain,
                form="row-pointer-base",
                address=address,
                row=reference.row,
                column=reference.column,
                index=reference.index,
            )
        )
        consume(match)

    for regex, form in (
        (DYNAMIC_PTR_RE, "flat-pointer"),
        (ARRAY_REF_RE, "flat-array"),
    ):
        for match in regex.finditer(rhs):
            references.append(
                _resolve_loop_address(
                    int(match.group(1), 16),
                    loop_index,
                    provider_id=provider_id,
                    form=form,
                )
            )
            consume(match)

    masked_rhs = "".join(masked)
    for match in DIRECT_ADDR_RE.finditer(masked_rhs):
        references.append(
            _locate_address(int(match.group(1), 16), provider_id)
        )

    return tuple(references)


def _assignment_statements(
    lines: list[str],
) -> tuple[tuple[int, str, tuple[int, int] | None], ...]:
    statements: list[tuple[int, str, tuple[int, int] | None]] = []
    active_range: tuple[int, int] | None = None
    brace_depth = 0
    active_depth: int | None = None

    for index, line in enumerate(lines):
        loop_match = LOOP_HEADER_RE.search(line)
        if loop_match:
            active_range = (
                _parse_int(loop_match.group(1)),
                _parse_int(loop_match.group(2)),
            )
            active_depth = brace_depth + 1

        if (
            LOOP_PTR_LHS_RE.search(line)
            or ARRAY_LHS_RE.search(line)
            or DIRECT_LHS_RE.match(line)
        ):
            statement = line.strip()
            cursor = index
            while ";" not in statement and cursor + 1 < len(lines):
                cursor += 1
                statement += " " + lines[cursor].strip()
            statements.append((index, statement, active_range))

        brace_depth += line.count("{") - line.count("}")
        if (
            active_range is not None
            and active_depth is not None
            and brace_depth < active_depth
        ):
            active_range = None
            active_depth = None

    return tuple(statements)


def _find_lhs_match(statement: str) -> re.Match[str]:
    match = (
        LOOP_PTR_LHS_RE.search(statement)
        or ARRAY_LHS_RE.search(statement)
        or DIRECT_LHS_RE.match(statement)
    )
    if match is None:
        raise ValueError("assignment LHS form is unsupported")
    return match


def _destination_for_statement(
    statement: str,
    *,
    provider_id: int,
    loop_index: int | None,
) -> Reference:
    match = _find_lhs_match(statement)
    if LOOP_PTR_LHS_RE.fullmatch(statement[:match.end()]):
        if loop_index is None:
            raise ValueError("loop-pointer LHS without local_10 loop range")
        return _resolve_loop_address(
            int(match.group(1), 16),
            loop_index,
            provider_id=provider_id,
            form="loop-pointer-lhs",
        )
    if ARRAY_LHS_RE.fullmatch(statement[:match.end()]):
        if loop_index is None:
            raise ValueError("array LHS without local_10 loop range")
        return _resolve_loop_address(
            int(match.group(1), 16),
            loop_index,
            provider_id=provider_id,
            form="loop-array-lhs",
        )

    reference = _locate_address(
        int(match.group(1), 16),
        provider_id,
    )
    return Reference(
        domain=reference.domain,
        form="direct-lhs",
        address=reference.address,
        row=reference.row,
        column=reference.column,
        index=reference.index,
    )


def extract_rhs_stencils(
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
    body_lines = body.splitlines()
    pivots = extract_reciprocal_pivots(
        body_lines,
        first_source_line=source_start_line,
    )
    layout = get_storage_layout(provider_id)
    errors: list[str] = []

    if len(pivots) != layout.scalar_count:
        errors.append(
            f"pivot-count:expected={layout.scalar_count}:actual={len(pivots)}"
        )

    stencils: list[AssignmentStencil] = []
    for pivot_index, pivot in enumerate(pivots):
        next_line = (
            pivots[pivot_index + 1].source_line
            if pivot_index + 1 < len(pivots)
            else source_start_line + len(body_lines)
        )
        block_start = pivot.source_line - source_start_line
        block_end = next_line - source_start_line
        block = body_lines[block_start:block_end]

        for local_line, statement, loop_range in _assignment_statements(block):
            absolute_line = pivot.source_line + local_line
            loop_values = (
                tuple(range(*loop_range))
                if loop_range is not None
                else (None,)
            )
            lhs_match = _find_lhs_match(statement)
            rhs_text = statement[lhs_match.end():]

            for loop_index in loop_values:
                try:
                    destination = _destination_for_statement(
                        statement,
                        provider_id=provider_id,
                        loop_index=(
                            None
                            if loop_index is None
                            else int(loop_index)
                        ),
                    )
                    rhs = _rhs_references(
                        rhs_text,
                        provider_id=provider_id,
                        loop_index=(
                            0
                            if loop_index is None
                            else int(loop_index)
                        ),
                    )
                except ValueError as exc:
                    errors.append(
                        f"pivot-{pivot_index}-line-{absolute_line}:{exc}"
                    )
                    continue

                stencils.append(
                    AssignmentStencil(
                        pivot_index=pivot_index,
                        source_line=absolute_line,
                        loop_index=(
                            None
                            if loop_index is None
                            else int(loop_index)
                        ),
                        destination=destination,
                        rhs=rhs,
                    )
                )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "function": spec["function"],
        "source_start_line": source_start_line,
        "source_line_count": len(body_lines),
        "scalar_count": layout.scalar_count,
        "stencils": [stencil.as_dict() for stencil in stencils],
        "ready": not errors,
        "errors": errors,
    }


def summarize_rhs_stencils(report: dict[str, Any]) -> dict[str, Any]:
    stencils = report.get("stencils") or []
    workspace = sum(
        stencil.get("destination", {}).get("domain") == "workspace"
        for stencil in stencils
    )
    output = sum(
        stencil.get("destination", {}).get("domain") == "output_vector"
        for stencil in stencils
    )
    global_count = len(stencils) - workspace - output

    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "stencil_count": len(stencils),
        "workspace_destination_stencils": workspace,
        "output_destination_stencils": output,
        "global_destination_stencils": global_count,
        "max_rhs_reference_count": max(
            (len(stencil.get("rhs") or []) for stencil in stencils),
            default=0,
        ),
        "ready": bool(report.get("ready")),
    }


def validate_rhs_stencils(
    report: dict[str, Any],
    *,
    source: str | None = None,
) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    provider_id = int(report.get("provider_id", -1))
    rows = int(report.get("scalar_count", 0))

    if source is not None:
        update_graph = extract_update_graph(
            source,
            provider_id=provider_id,
        )
        expected = {
            int(row["pivot_index"]): int(row["workspace_write_site_count"])
            for row in update_graph.get("rows") or []
        }
        actual: dict[int, int] = {}
        for stencil in report.get("stencils") or []:
            if stencil.get("destination", {}).get("domain") == "workspace":
                pivot = int(stencil.get("pivot_index", -1))
                actual[pivot] = actual.get(pivot, 0) + 1
        for pivot in range(rows):
            if actual.get(pivot, 0) != expected.get(pivot, 0):
                errors.append(
                    f"pivot-{pivot}-workspace-site-count-mismatch:"
                    f"expected={expected.get(pivot, 0)}:actual={actual.get(pivot, 0)}"
                )

    for stencil in report.get("stencils") or []:
        destination = stencil.get("destination") or {}
        if destination.get("domain") == "workspace":
            if (
                destination.get("row") is None
                or destination.get("column") is None
            ):
                errors.append("workspace-destination-missing-row-column")
        for reference in stencil.get("rhs") or []:
            if reference.get("domain") == "workspace":
                if (
                    reference.get("row") is None
                    or reference.get("column") is None
                ):
                    errors.append("workspace-rhs-reference-missing-row-column")

    return {
        "format": "SHIFT.SpecializedProviderRHSStencilValidation/1",
        "version": 1,
        "provider_id": provider_id,
        "ready": not errors,
        "errors": errors,
        "stencil_count": len(report.get("stencils") or []),
    }


def build_rhs_stencil_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = extract_rhs_stencils(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_rhs_stencils(report)
        report["validation"] = validate_rhs_stencils(
            report,
            source=source,
        )
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "scope": {
            "representation": "assignment-level RHS reference stencil",
            "dynamic_index": "local_10 loop iterations are expanded",
            "unknown_static_references": "kept as direct global addresses when they do not resolve into provider workspace or output vector",
        },
        "limitations": [
            "The proprietary arithmetic expression text is not emitted.",
            "Reference order follows the decompiler source expression order; it is not a claim about compiler evaluation ordering.",
            "This phase identifies numeric data dependencies at the address level; semantic matrix names and physical units remain unresolved.",
        ],
        "status": "source-backed-rhs-reference-stencils",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_rhs_stencil_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
