"""Prepare an exact builtin solver frame for the native FUN_007b2210→FUN_007b0f20 path.

The input must explicitly prove every runtime-only prerequisite. This module
does not derive provider absence, matrix/RHS contents, reset-node selection or
the sparse graph from static vehicle assets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any, Mapping, Sequence

from sdf_builtin_sparse_solver_runtime import solve_builtin_sparse_in_place
from sdf_constraint_solver_frame_runtime import apply_builtin_diagonal_reset

FORMAT = "SHIFT.NativeBuiltinSolverFrame/1"
INPUT_FORMAT = "SHIFT.NativeBuiltinSolverFrameInput/1"
PACKET_FORMAT = "SHIFT.NativeBuiltinSolverFramePacket/1"
PACKET_MAGIC = b"SBFR"
PACKET_VERSION = 1

PROOF_PROVIDER_ABSENT = 1 << 0
PROOF_MATRIX_RHS = 1 << 1
PROOF_RESET_SELECTION = 1 << 2
PROOF_SPARSE_GRAPH = 1 << 3
REQUIRED_PROOF_FLAGS = (
    PROOF_PROVIDER_ABSENT
    | PROOF_MATRIX_RHS
    | PROOF_RESET_SELECTION
    | PROOF_SPARSE_GRAPH
)

_HEADER = struct.Struct("<4s7I")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _finite_number(value: Any, *, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _normalize_matrix(value: Any) -> list[list[float]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("matrix must be a sequence")
    rows = list(value)
    n = len(rows)
    if n < 1 or n > 4096:
        raise ValueError("matrix dimension must be in range 1..4096")
    matrix: list[list[float]] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
            raise ValueError(f"matrix row {row_index} must be a sequence")
        values = list(row)
        if len(values) != n:
            raise ValueError("matrix must be square")
        matrix.append([
            _finite_number(item, label=f"matrix[{row_index}][{column}]")
            for column, item in enumerate(values)
        ])
    return matrix


def _normalize_rhs(value: Any, n: int) -> list[float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("rhs must be a sequence")
    values = list(value)
    if len(values) != n:
        raise ValueError("rhs length must match matrix dimension")
    return [
        _finite_number(item, label=f"rhs[{index}]")
        for index, item in enumerate(values)
    ]


def _normalize_reset_nodes(value: Any, n: int) -> list[int]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("reset_nodes must be a sequence")
    nodes = sorted({int(item) for item in value})
    for node in nodes:
        if node < 0 or node >= n:
            raise ValueError(f"reset node out of range: {node}")
    return nodes


def _normalize_forward_records(
    value: Any,
    n: int,
) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("forward_records must be a sequence")
    records = list(value)
    if len(records) != n + 1:
        raise ValueError("forward_records must contain n+1 records")

    normalized: list[dict[str, Any]] = []
    for record_index, raw_record in enumerate(records):
        if not isinstance(raw_record, Mapping):
            raise ValueError(f"forward record {record_index} must be an object")
        raw_items = raw_record.get("items")
        if not isinstance(raw_items, Sequence) or isinstance(
            raw_items, (str, bytes)
        ):
            raise ValueError(
                f"forward record {record_index} items must be a sequence"
            )
        items: list[dict[str, Any]] = []
        for item_index, raw_item in enumerate(raw_items):
            if not isinstance(raw_item, Mapping):
                raise ValueError(
                    f"forward item {record_index}:{item_index} must be an object"
                )
            node = int(raw_item.get("node", -1))
            raw_deps = raw_item.get("dependencies") or []
            if not isinstance(raw_deps, Sequence) or isinstance(
                raw_deps, (str, bytes)
            ):
                raise ValueError(
                    f"forward dependencies {record_index}:{item_index} "
                    "must be a sequence"
                )
            deps = [int(dep) for dep in raw_deps]
            if any(dep < 0 or dep >= n for dep in deps):
                raise ValueError(
                    f"forward dependency out of range at "
                    f"{record_index}:{item_index}"
                )
            items.append({
                "node": node,
                "dependencies": deps,
            })
        normalized.append({"items": items})

    terminal = normalized[n]["items"]
    if len(terminal) != n:
        raise ValueError(
            "terminal forward record must contain one item per scalar row"
        )

    for pivot in range(n):
        items = normalized[pivot]["items"]
        if not items:
            raise ValueError(f"forward record {pivot} has no pivot item")
        if items[0]["node"] != pivot:
            raise ValueError(
                f"forward record {pivot} pivot node must equal its index"
            )
        for dep in items[0]["dependencies"]:
            if dep >= pivot:
                raise ValueError(
                    f"invalid pivot dependency {dep} at row {pivot}"
                )
        for item in items[1:]:
            target = int(item["node"])
            if target <= pivot or target >= n:
                raise ValueError(
                    f"invalid forward target {target} for pivot {pivot}"
                )
            for dep in item["dependencies"]:
                if dep >= pivot:
                    raise ValueError(
                        f"invalid forward dependency {dep} "
                        f"for target {target}"
                    )

        terminal_item = terminal[pivot]
        if int(terminal_item["node"]) != pivot:
            raise ValueError(
                f"terminal forward item {pivot} node mismatch"
            )
        for dep in terminal_item["dependencies"]:
            if dep >= pivot:
                raise ValueError(
                    f"invalid terminal dependency {dep} at row {pivot}"
                )

    return normalized


def _normalize_reverse_records(
    value: Any,
    n: int,
) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("reverse_records must be a sequence")
    records = list(value)
    if len(records) != n:
        raise ValueError("reverse_records must contain n records")

    normalized: list[dict[str, Any]] = []
    for index, raw_record in enumerate(records):
        if not isinstance(raw_record, Mapping):
            raise ValueError(f"reverse record {index} must be an object")
        node = int(raw_record.get("node", -1))
        if node != index:
            raise ValueError(f"reverse record {index} node mismatch")
        raw_deps = raw_record.get("dependencies") or []
        if not isinstance(raw_deps, Sequence) or isinstance(
            raw_deps, (str, bytes)
        ):
            raise ValueError(
                f"reverse dependencies {index} must be a sequence"
            )
        deps = [int(dep) for dep in raw_deps]
        for dep in deps:
            if dep <= index or dep >= n:
                raise ValueError(
                    f"invalid reverse dependency {dep} at row {index}"
                )
        normalized.append({
            "node": node,
            "dependencies": deps,
        })
    return normalized


def _require_proof(source: Mapping[str, Any], key: str) -> None:
    if source.get(key) is not True:
        raise ValueError(f"{key} must be explicitly true")


def _serialize_graph_item(
    output: bytearray,
    node: int,
    dependencies: Sequence[int],
) -> None:
    output += struct.pack("<II", int(node), len(dependencies))
    if dependencies:
        output += struct.pack(
            "<" + "I" * len(dependencies),
            *[int(value) for value in dependencies],
        )


def _serialize_packet(
    matrix: Sequence[Sequence[float]],
    rhs: Sequence[float],
    reset_nodes: Sequence[int],
    forward_records: Sequence[Mapping[str, Any]],
    reverse_records: Sequence[Mapping[str, Any]],
    expected_solution: Sequence[float],
) -> bytes:
    n = len(matrix)
    output = bytearray(
        _HEADER.pack(
            PACKET_MAGIC,
            PACKET_VERSION,
            n,
            len(reset_nodes),
            len(forward_records),
            len(reverse_records),
            REQUIRED_PROOF_FLAGS,
            0,
        )
    )

    for row in matrix:
        output += struct.pack("<" + "d" * n, *row)
    output += struct.pack("<" + "d" * n, *rhs)

    if reset_nodes:
        output += struct.pack(
            "<" + "I" * len(reset_nodes),
            *reset_nodes,
        )

    for record in forward_records:
        items = list(record.get("items") or [])
        output += struct.pack("<I", len(items))
        for item in items:
            _serialize_graph_item(
                output,
                int(item.get("node", -1)),
                [int(dep) for dep in (item.get("dependencies") or [])],
            )

    for record in reverse_records:
        _serialize_graph_item(
            output,
            int(record.get("node", -1)),
            [int(dep) for dep in (record.get("dependencies") or [])],
        )

    output += struct.pack(
        "<" + "d" * n,
        *[float(value) for value in expected_solution],
    )
    return bytes(output)


def build_native_builtin_solver_frame(
    source: Mapping[str, Any],
) -> dict[str, Any]:
    if source.get("format") != INPUT_FORMAT:
        raise ValueError(
            f"input must be {INPUT_FORMAT}"
        )

    for key in (
        "provider_absent_proven",
        "matrix_rhs_ready",
        "reset_selection_ready",
        "sparse_graph_ready",
    ):
        _require_proof(source, key)

    matrix = _normalize_matrix(source.get("matrix"))
    n = len(matrix)
    rhs = _normalize_rhs(source.get("rhs"), n)
    reset_nodes = _normalize_reset_nodes(
        source.get("reset_nodes") or [],
        n,
    )
    forward_records = _normalize_forward_records(
        source.get("forward_records"),
        n,
    )
    reverse_records = _normalize_reverse_records(
        source.get("reverse_records"),
        n,
    )

    reset_result = apply_builtin_diagonal_reset(
        matrix,
        rhs,
        reset_nodes,
    )
    solve_result = solve_builtin_sparse_in_place(
        reset_result["matrix"],
        reset_result["rhs"],
        forward_records,
        reverse_records,
    )
    solution = [
        _finite_number(value, label=f"solution[{index}]")
        for index, value in enumerate(solve_result["solution"])
    ]

    packet = _serialize_packet(
        matrix,
        rhs,
        reset_nodes,
        forward_records,
        reverse_records,
        solution,
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "verification_scope": source.get("verification_scope"),
        "scalar_count": n,
        "reset_node_count": len(reset_nodes),
        "reset_nodes": reset_nodes,
        "proofs": {
            "provider_absent_proven": True,
            "matrix_rhs_ready": True,
            "reset_selection_ready": True,
            "sparse_graph_ready": True,
        },
        "dispatch": {
            "provider_present": False,
            "builtin_reset": "FUN_007b2210",
            "builtin_solve": "FUN_007b0f20",
            "execution_order": [
                "FUN_007b2210",
                "FUN_007b0f20",
            ],
        },
        "graph": {
            "forward_record_count": len(forward_records),
            "reverse_record_count": len(reverse_records),
        },
        "oracle": {
            "format": "SHIFT.NativeBuiltinSolverFrameOracle/1",
            "solution": solution,
            "solution_sha256": _sha256_bytes(
                struct.pack("<" + "d" * n, *solution)
            ),
            "source": "Python source-backed FUN_007b2210 + FUN_007b0f20",
        },
        "packet": {
            "format": PACKET_FORMAT,
            "magic": PACKET_MAGIC.decode("ascii"),
            "version": PACKET_VERSION,
            "size": len(packet),
            "sha256": _sha256_bytes(packet),
            "bytes": packet,
        },
        "boundary": {
            "derives_provider_absence": False,
            "derives_matrix_rhs": False,
            "derives_reset_selection": False,
            "derives_sparse_graph": False,
            "executes_post_solve_body_state": False,
            "provider_path_supported": False,
            "fixed_step_runtime_integration": False,
        },
    }


def build_native_builtin_solver_frame_file(
    input_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    source = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(source, Mapping):
        raise ValueError("input JSON must be an object")

    report = build_native_builtin_solver_frame(source)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    packet = bytes(report["packet"].pop("bytes"))
    packet_path = root / "solver_frame.sbfr"
    packet_path.write_bytes(packet)
    report["packet"]["path"] = packet_path.name

    manifest_path = root / "solver_frame_manifest.json"
    manifest_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output_dir")
    args = parser.parse_args(argv)

    report = build_native_builtin_solver_frame_file(
        args.input,
        args.output_dir,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "scalar_count": report["scalar_count"],
        "reset_node_count": report["reset_node_count"],
        "packet_sha256": report["packet"]["sha256"],
        "verification_scope": report["verification_scope"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
