"""Normalize and analyze a specialized-provider pre/post capture session.

Phase 470 composes the Phase 462 capture schema, Phase 463 runtime snapshots,
Phase 464 raw mutation diff and Phase 469 reset delta into one provider-session
contract. The session layer does not reinterpret packed storage as a logical
matrix.
"""
from __future__ import annotations

from typing import Any, Mapping

from specialized_provider_capture_runtime import (
    compare_provider_geometry,
    normalize_provider_capture,
)
from specialized_provider_capture_diff_runtime import (
    compare_provider_captures,
)
from specialized_provider_reset_delta_runtime import (
    compare_capture_to_reset,
)
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderCaptureSessionRuntime/1"


def normalize_provider_session(
    pre_solve: Mapping[str, Any],
    post_solve: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pre = normalize_provider_capture(pre_solve)
    post = (
        None
        if post_solve is None
        else normalize_provider_capture(post_solve)
    )
    errors: list[str] = []

    if post is not None:
        if pre["provider_id"] != post["provider_id"]:
            errors.append("provider-id-mismatch")
        if pre["scalar_count"] != post["scalar_count"]:
            errors.append("scalar-count-mismatch")
        if pre["workspace_doubles"] != post["workspace_doubles"]:
            errors.append("workspace-size-mismatch")

        pre_frame = pre.get("frame_index")
        post_frame = post.get("frame_index")
        if (
            pre_frame is not None
            and post_frame is not None
            and int(pre_frame) != int(post_frame)
        ):
            errors.append("frame-index-mismatch")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "normalized" if not errors else "blocked",
        "ready": not errors,
        "provider_id": pre["provider_id"],
        "scalar_count": pre["scalar_count"],
        "pre_solve": pre,
        "post_solve": post,
        "errors": errors,
    }


def analyze_provider_session(
    pre_solve: Mapping[str, Any],
    *,
    post_solve: Mapping[str, Any] | None = None,
    reset_source: str | None = None,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    session = normalize_provider_session(
        pre_solve,
        post_solve,
    )
    provider_id = int(session["provider_id"])
    layout = get_storage_layout(provider_id)

    geometry_pre = compare_provider_geometry(
        session["pre_solve"],
        provider_id=provider_id,
    )
    geometry_post = (
        None
        if session["post_solve"] is None
        else compare_provider_geometry(
            session["post_solve"],
            provider_id=provider_id,
        )
    )

    reset_delta = None
    if reset_source is not None:
        reset_delta = compare_capture_to_reset(
            reset_source,
            session["pre_solve"],
            provider_id=provider_id,
            abs_tol=abs_tol,
            rel_tol=rel_tol,
        )

    mutation_diff = None
    if session["post_solve"] is not None:
        mutation_diff = compare_provider_captures(
            session["pre_solve"],
            session["post_solve"],
            abs_tol=abs_tol,
            rel_tol=rel_tol,
        )

    errors = list(session["errors"])
    for name, report in (
        ("geometry-pre", geometry_pre),
        ("geometry-post", geometry_post),
        ("reset-delta", reset_delta),
        ("mutation-diff", mutation_diff),
    ):
        if report is not None and report.get("ready") is not True:
            errors.append(f"{name}-not-ready")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "analyzed" if not errors else "blocked",
        "ready": not errors,
        "provider_id": provider_id,
        "scalar_count": layout.scalar_count,
        "session": session,
        "geometry": {
            "pre": geometry_pre,
            "post": geometry_post,
        },
        "reset_delta": reset_delta,
        "mutation_diff": mutation_diff,
        "errors": list(dict.fromkeys(errors)),
    }


def summarize_provider_session(report: Mapping[str, Any]) -> dict[str, Any]:
    mutation = report.get("mutation_diff") or {}
    reset_delta = report.get("reset_delta") or {}
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "post_solve_present": report.get("session", {}).get(
            "post_solve"
        ) is not None,
        "workspace_changes": int(
            mutation.get("workspace_change_count", 0)
        ),
        "output_changes": int(
            mutation.get("output_change_count", 0)
        ),
        "reset_zero_slot_deviations": int(
            (reset_delta.get("counts") or {}).get(
                "reset-zero-slot-deviation",
                0,
            )
        ),
        "reset_unit_slot_deviations": int(
            (reset_delta.get("counts") or {}).get(
                "reset-unit-slot-deviation",
                0,
            )
        ),
        "outside_reset_domain_nonzero": int(
            (reset_delta.get("counts") or {}).get(
                "outside-reset-domain-nonzero",
                0,
            )
        ),
        "output_nonzero_before_solve": int(
            (reset_delta.get("counts") or {}).get(
                "output-nonzero",
                0,
            )
        ),
        "ready": bool(report.get("ready")),
    }


def validate_provider_session(report: Mapping[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))
    provider_id = int(report.get("provider_id", -1))

    if provider_id not in (0, 1):
        errors.append("unsupported-provider-id")

    if scalar_count <= 0:
        errors.append("non-positive-scalar-count")

    geometry = report.get("geometry") or {}
    pre_geometry = geometry.get("pre") or {}
    if pre_geometry.get("scalar_count") != scalar_count:
        errors.append("pre-geometry-scalar-count-mismatch")

    post = report.get("session", {}).get("post_solve")
    post_geometry = geometry.get("post")
    if post is not None and post_geometry is None:
        errors.append("post-solve-present-without-post-geometry")

    mutation = report.get("mutation_diff")
    if mutation is not None:
        if mutation.get("provider_id") != provider_id:
            errors.append("mutation-provider-id-mismatch")
        if mutation.get("scalar_count") != scalar_count:
            errors.append("mutation-scalar-count-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderCaptureSessionValidation/1",
        "version": 1,
        "provider_id": provider_id,
        "ready": not errors,
        "errors": list(dict.fromkeys(errors)),
    }


def build_provider_session_contract(
    pre_solve: Mapping[str, Any],
    *,
    post_solve: Mapping[str, Any] | None = None,
    reset_source: str | None = None,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    report = analyze_provider_session(
        pre_solve,
        post_solve=post_solve,
        reset_source=reset_source,
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )
    report["summary"] = summarize_provider_session(report)
    report["validation"] = validate_provider_session(report)
    return report


__all__ = [
    "FORMAT",
    "normalize_provider_session",
    "analyze_provider_session",
    "summarize_provider_session",
    "validate_provider_session",
    "build_provider_session_contract",
]
