"""Unified BMW M3 retail SDF runtime-probe bundle verification."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from bmw_m3_solver_capture_verify_runtime import (
    verify_bmw_m3_capture_structure,
)
from sdf_runtime_probe_launcher_runtime import resolve_probe_executable
from sdf_runtime_probe_pe_validation import validate_probe_executable_file
from sdf_runtime_probe_session_runtime import (
    load_probe_json,
    normalize_probe_session,
    compare_probe_session,
)
from verify_bmw_m3_solver_capture import verify_bff_domain


FORMAT = "SHIFT.BMWM3RuntimeProbeBundle/1"


def build_bundle_report(
    *,
    shift_input: str | Path,
    bff_path: str | Path,
    pre_path: str | Path | None,
    post_path: str | Path | None = None,
    frame_path: str | Path | None = None,
    expected_session_path: str | Path | None = None,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
    work_dir: str | Path = "out/sdf-runtime-probe-bundle",
) -> dict[str, Any]:
    work = Path(work_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    static: dict[str, Any] = {}
    try:
        executable = resolve_probe_executable(shift_input, work / "retail")
        static["shift"] = validate_probe_executable_file(executable)
    except Exception as exc:
        static["shift"] = {
            "format": "SHIFT.SDFRuntimeProbePEValidation/1",
            "version": 1,
            "ready": False,
            "status": "blocked",
            "errors": [f"input:{exc}"],
        }

    try:
        static["bmw_bff_domain"] = verify_bff_domain(Path(bff_path))
    except Exception as exc:
        static["bmw_bff_domain"] = {
            "ready": False,
            "status": "blocked",
            "errors": [f"bff:{exc}"],
        }

    session: dict[str, Any] | None = None
    comparison: dict[str, Any] | None = None
    capture_structure: dict[str, Any] | None = None

    if pre_path is None:
        errors.append("missing:pre-solve-capture")
    else:
        pre = load_probe_json(pre_path)
        post = load_probe_json(post_path) if post_path is not None else None
        frame = load_probe_json(frame_path) if frame_path is not None else None
        session = normalize_probe_session(pre, post, frame)
        capture_structure = verify_bmw_m3_capture_structure(pre)
        if not session["ready"]:
            errors.extend(f"session:{reason}" for reason in session["errors"])
        if not capture_structure["ready"]:
            errors.extend(f"capture:{reason}" for reason in capture_structure["errors"])

        if expected_session_path is not None:
            expected = load_probe_json(expected_session_path)
            comparison = compare_probe_session(
                {
                    "pre_solve": pre,
                    "post_solve": post,
                    "frame_entry": frame,
                },
                expected,
                abs_tol=abs_tol,
                rel_tol=rel_tol,
            )
            if not comparison["ready"]:
                errors.extend(
                    f"numeric:{reason}" for reason in comparison.get("errors", [])
                )

    if static["shift"].get("ready") is not True:
        errors.extend(f"shift:{reason}" for reason in static["shift"].get("errors", []))
    if static["bmw_bff_domain"].get("ready") is not True:
        errors.extend(
            f"bmw-domain:{reason}"
            for reason in static["bmw_bff_domain"].get("errors", [])
        )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "verified" if not errors else "blocked",
        "ready": not errors,
        "input": {
            "shift": str(Path(shift_input).resolve()),
            "bff": str(Path(bff_path).resolve()),
            "pre": None if pre_path is None else str(Path(pre_path).resolve()),
            "post": None if post_path is None else str(Path(post_path).resolve()),
            "frame": None if frame_path is None else str(Path(frame_path).resolve()),
            "expected_session": (
                None
                if expected_session_path is None
                else str(Path(expected_session_path).resolve())
            ),
        },
        "static": static,
        "capture": {
            "structure": capture_structure,
            "session": session,
            "comparison": comparison,
        },
        "errors": list(dict.fromkeys(errors)),
        "gates": {
            "retail_pe": static["shift"].get("ready") is True,
            "bmw_m3_domain": static["bmw_bff_domain"].get("ready") is True,
            "frame_pre_post": session is not None and session.get("ready") is True,
            "numeric_expected": (
                expected_session_path is None
                or (comparison is not None and comparison.get("ready") is True)
            ),
        },
        "limitations": [
            "Without a real pre_solve capture the bundle is blocked.",
            "Without an expected session, numeric parity is not claimed.",
            "Provider-owned solver execution remains opaque even when frame_entry identifies it.",
        ],
    }


__all__ = ["FORMAT", "build_bundle_report"]
