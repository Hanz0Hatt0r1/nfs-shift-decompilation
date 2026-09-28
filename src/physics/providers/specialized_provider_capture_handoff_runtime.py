"""Join runtime provider captures to source-derived solver programs.

The handoff layer keeps runtime observation authoritative for provider identity.
It attaches a source-derived solver program only after an observed provider id
is supplied or a capture bundle explicitly records that provider id.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from specialized_provider_capture_bundle_runtime import (
    build_capture_bundle_contract,
)
from specialized_provider_runtime_selection_runtime import (
    build_runtime_selection_contract,
    validate_runtime_selection,
)
from specialized_provider_solver_program_runtime import (
    build_solver_program,
    summarize_solver_program,
    validate_solver_program,
)

FORMAT = "SHIFT.SpecializedProviderCaptureHandoffRuntime/1"


def _solver_by_provider(
    source: str,
) -> dict[int, dict[str, Any]]:
    programs: dict[int, dict[str, Any]] = {}
    for provider_id in (0, 1):
        report = build_solver_program(source, provider_id=provider_id)
        report["summary"] = summarize_solver_program(report)
        report["validation"] = validate_solver_program(report)
        programs[provider_id] = report
    return programs


def _attach_observed_solver(
    bundle: Mapping[str, Any],
    programs: Mapping[int, Mapping[str, Any]],
    *,
    observed_provider_id: int | None,
) -> dict[str, Any]:
    provider_id = int(bundle["provider_id"])
    attached: dict[str, Any] = {
        "observed_provider_id": observed_provider_id,
        "attached_provider_id": None,
        "status": "not-attached",
        "solver_program": None,
    }

    if observed_provider_id is None:
        return attached

    if provider_id != int(observed_provider_id):
        attached["status"] = "provider-id-mismatch"
        return attached

    program = programs.get(provider_id)
    if program is None:
        attached["status"] = "missing-source-program"
        return attached

    attached["attached_provider_id"] = provider_id
    attached["status"] = "attached"
    attached["solver_program"] = {
        "format": program["format"],
        "version": program["version"],
        "provider_id": provider_id,
        "function": program.get("function"),
        "scalar_count": program.get("scalar_count"),
        "summary": program.get("summary"),
        "validation": program.get("validation"),
    }
    return attached


def build_capture_handoff_contract(
    source: str,
    capture_directory: str | Path,
    *,
    reset_events_path: str | Path | None = None,
    observed_provider_id: int | None = None,
) -> dict[str, Any]:
    selection = build_runtime_selection_contract(source)
    selection_validation = validate_runtime_selection(
        selection,
        observed_provider_id=observed_provider_id,
    )
    captures = build_capture_bundle_contract(
        capture_directory,
        reset_events_path=reset_events_path,
    )
    programs = _solver_by_provider(source)

    bundles: list[dict[str, Any]] = []
    errors = list(selection_validation.get("errors") or [])
    for bundle in captures.get("bundles") or []:
        attached = _attach_observed_solver(
            bundle,
            programs,
            observed_provider_id=observed_provider_id,
        )
        row = dict(bundle)
        row["source_handoff"] = attached
        if attached["status"] == "provider-id-mismatch":
            errors.append(
                f"capture-provider-mismatch:{bundle['provider_id']}:{observed_provider_id}"
            )
        elif attached["status"] == "missing-source-program":
            errors.append(
                f"source-program-missing:{bundle['provider_id']}"
            )
        bundles.append(row)

    if observed_provider_id is not None:
        matching_ready = [
            bundle
            for bundle in bundles
            if bundle["provider_id"] == int(observed_provider_id)
            and bundle.get("ready") is True
        ]
        if not matching_ready:
            errors.append("observed-provider-has-no-ready-capture")

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "capture_directory": str(capture_directory),
        "observed_provider_id": observed_provider_id,
        "selection": selection,
        "selection_validation": selection_validation,
        "capture_bundle": {
            "format": captures.get("format"),
            "version": captures.get("version"),
            "directory": captures.get("directory"),
            "bundle_count": captures.get("bundle_count"),
            "summary": captures.get("summary"),
            "ready": captures.get("ready"),
            "errors": captures.get("errors", []),
        },
        "bundles": bundles,
        "source_programs": {
            str(provider_id): {
                "summary": programs[provider_id]["summary"],
                "validation": programs[provider_id]["validation"],
            }
            for provider_id in (0, 1)
        },
        "validation": {
            "selection": selection_validation,
            "capture_ready": captures.get("ready") is True,
            "attached_bundle_count": sum(
                bundle["source_handoff"]["status"] == "attached"
                for bundle in bundles
            ),
            "observed_provider_attached": (
                observed_provider_id is None
                or any(
                    bundle["source_handoff"]["status"] == "attached"
                    and bundle["provider_id"] == int(observed_provider_id)
                    for bundle in bundles
                )
            ),
        },
        "ready": (
            not errors
            and selection_validation.get("ready") is True
            and captures.get("ready") is True
            and all(
                program["validation"]["ready"]
                for program in programs.values()
            )
        ),
        "errors": list(dict.fromkeys(errors)),
        "limitations": [
            "Observed provider identity remains runtime evidence; source analysis never chooses it.",
            "A source program is attached to a capture only when provider ids match.",
            "The handoff still does not claim numeric retail/provider equivalence.",
        ],
    }


__all__ = [
    "FORMAT",
    "build_capture_handoff_contract",
]
