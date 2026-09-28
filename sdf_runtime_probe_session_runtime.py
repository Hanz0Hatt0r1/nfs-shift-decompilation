"""Session-level normalization and comparison for SDF runtime probe outputs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from sdf_solver_capture_runtime import compare_solver_captures, compare_solver_vectors, normalize_solver_capture

FORMAT = "SHIFT.SDFRuntimeProbeSession/1"


def load_probe_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{source}: expected JSON object")
    return value


def normalize_probe_session(
    pre_solve: Mapping[str, Any],
    post_solve: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pre = normalize_solver_capture(pre_solve)
    post: dict[str, Any] | None = None
    errors: list[str] = []

    if post_solve is not None:
        post_scalar_count = int(post_solve.get("scalar_count", -1))
        post_rhs = [float(value) for value in post_solve.get("rhs", [])]
        if post_scalar_count != pre["scalar_count"]:
            errors.append("post-solve-scalar-count")
        if len(post_rhs) != pre["scalar_count"]:
            errors.append("post-solve-vector-length")
        post = {
            "format": "SHIFT.SDFSolverPostSolveProbe/1",
            "version": 1,
            "ready": not errors,
            "status": "normalized" if not errors else "blocked",
            "scalar_count": post_scalar_count,
            "rhs": post_rhs,
            "frame_index": post_solve.get("frame_index"),
            "source_function": post_solve.get("source_function"),
        }

    pre_frame = pre.get("frame")
    post_frame = None if post is None else post.get("frame_index")
    if pre_frame is not None and post_frame is not None and int(pre_frame) != int(post_frame):
        errors.append("frame-index-mismatch")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "normalized" if not errors else "blocked",
        "ready": not errors and (post is None or post["ready"]),
        "pre_solve": pre,
        "post_solve": post,
        "errors": list(dict.fromkeys(errors)),
        "frame": pre_frame if pre_frame is not None else post_frame,
    }


def compare_probe_session(
    observed: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    obs = normalize_probe_session(
        observed["pre_solve"],
        observed.get("post_solve"),
    )
    exp = normalize_probe_session(
        expected["pre_solve"],
        expected.get("post_solve"),
    )

    pre_compare = compare_solver_captures(
        exp["pre_solve"],
        obs["pre_solve"],
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )
    post_compare = None
    if exp["post_solve"] is not None or obs["post_solve"] is not None:
        if exp["post_solve"] is None or obs["post_solve"] is None:
            post_compare = {
                "format": "SHIFT.SDFPostSolveComparison/1",
                "version": 1,
                "ready": False,
                "status": "blocked",
                "errors": [{"kind": "missing-post-solve"}],
            }
        else:
            post_compare = compare_solver_vectors(
                exp["post_solve"]["rhs"],
                obs["post_solve"]["rhs"],
                abs_tol=abs_tol,
                rel_tol=rel_tol,
            )

    ready = (
        obs["ready"]
        and exp["ready"]
        and pre_compare["ready"]
        and (post_compare is None or post_compare["ready"])
    )
    return {
        "format": "SHIFT.SDFRuntimeProbeSessionComparison/1",
        "version": 1,
        "status": "matched" if ready else "diverged-or-blocked",
        "ready": ready,
        "observed": obs,
        "expected": exp,
        "pre_solve": pre_compare,
        "post_solve": post_compare,
        "errors": list(dict.fromkeys(obs["errors"] + exp["errors"])),
    }


def describe_sdf_runtime_probe_session_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed-session-contract",
        "ready": True,
        "inputs": {
            "pre_solve": "SHIFT.SDFRuntimeProbe/1 JSON from FUN_007b0f20",
            "post_solve": "optional SHIFT.SDFSolverPostSolveProbe/1 JSON from FUN_007b4110",
        },
        "checks": [
            "scalar_count consistency",
            "pre/post frame index consistency",
            "pre-solve RHS/matrix comparison",
            "post-solve solved-vector comparison",
        ],
        "limitations": [
            "Session pairing depends on matching frame_index values from the runtime probe.",
            "Provider-owned pre-solve state remains unavailable when FUN_007b0f20 is bypassed.",
        ],
    }


__all__ = [
    "load_probe_json",
    "normalize_probe_session",
    "compare_probe_session",
    "describe_sdf_runtime_probe_session_contract",
]
