#!/usr/bin/env python3
"""Reuse launcher validators to classify explicit vertical-slice runtime inputs.

This module does not weaken launcher validation. It calls the same JSON, binary,
scene-set and input-script validators used by run_native_vertical_slice.py and
returns compact SHIFT.OfflineValidatedRuntimeInput/1 records for the Process 3
requirements report.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from offline_runtime_requirements import VALIDATED_INPUT_FORMAT
from offline_vertical_slice_profile import _resolve_under_workspace
from run_native_vertical_slice import (
    BINARY_INPUTS,
    JSON_INPUTS,
    INPUT_SCRIPT_FORMAT,
    ProfileError,
    _require_binary_packet,
    _require_json_contract,
    _validate_input_script,
    _validate_scene_set,
)


def _record(
    name: str,
    *,
    ready: bool,
    artifact: str | None,
    source: str,
    validation: Mapping[str, Any] | None = None,
    blocking_reasons: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "format": VALIDATED_INPUT_FORMAT,
        "version": 1,
        "name": name,
        "ready": ready,
        "artifact": artifact,
        "source": source,
        "validation": dict(validation or {}),
        "blocking_reasons": list(blocking_reasons or []),
        "boundary": {
            "launcher_validator_reused": True,
            "path_presence_is_proof": False,
            "missing_evidence_synthesized": False,
        },
    }


def _resolve(
    root: Path,
    raw: Any,
    *,
    name: str,
    expect_dir: bool = False,
) -> tuple[Path | None, str | None]:
    relative, error = _resolve_under_workspace(
        root,
        raw,
        label=name,
        expect_dir=expect_dir,
    )
    if error or relative is None:
        return None, error or f"{name}:path-unresolved"
    return (root / relative).resolve(), None


def validate_explicit_runtime_inputs(
    *,
    workspace_root: str | Path,
    explicit_inputs: Mapping[str, str | Path | None],
    input_script: str | Path | None = None,
    interactive: bool = False,
    keyboard: bool = False,
) -> dict[str, dict[str, Any]]:
    """Return one validation record for every supplied runtime requirement."""
    root = Path(workspace_root).resolve()
    rows: dict[str, dict[str, Any]] = {}

    for name, raw in explicit_inputs.items():
        text = str(raw or "").strip()
        if not text:
            continue
        path, error = _resolve(
            root,
            raw,
            name=name,
            expect_dir=name == "scene_set",
        )
        if error or path is None:
            rows[name] = _record(
                name,
                ready=False,
                artifact=None,
                source="explicit runtime input",
                blocking_reasons=[error or "path-unresolved"],
            )
            continue

        try:
            if name == "scene_set":
                validation = _validate_scene_set(path)
            elif name in JSON_INPUTS:
                expected_format, require_ready = JSON_INPUTS[name]
                value = _require_json_contract(
                    path,
                    expected_format=expected_format,
                    require_ready=require_ready,
                    label=name.replace("_", " "),
                )
                if name == "participant_boundary":
                    if value.get("registry_selector_identity_join_proven") is not True:
                        raise ProfileError(
                            "participant runtime evidence has no proven registry/selector identity join"
                        )
                    if value.get("participant_instance_ready") is not True:
                        raise ProfileError(
                            "participant runtime evidence has no ready participant instance"
                        )
                validation = {
                    "format": value.get("format"),
                    "ready": True,
                }
            elif name in BINARY_INPUTS:
                magic, packet_format = BINARY_INPUTS[name]
                validation = _require_binary_packet(
                    path,
                    magic=magic,
                    packet_format=packet_format,
                    label=name.replace("_", " "),
                )
            else:
                rows[name] = _record(
                    name,
                    ready=False,
                    artifact=str(path),
                    source="explicit runtime input",
                    blocking_reasons=["unsupported-runtime-input-name"],
                )
                continue
        except (OSError, ProfileError, ValueError) as exc:
            rows[name] = _record(
                name,
                ready=False,
                artifact=str(path),
                source="explicit runtime input",
                blocking_reasons=[f"{type(exc).__name__}:{exc}"],
            )
        else:
            rows[name] = _record(
                name,
                ready=True,
                artifact=str(path),
                source="validated explicit runtime input",
                validation=validation,
            )

    # input_binding is a choice as well as an evidence surface. A keyboard or
    # interactive selection is enough to satisfy this requirement; frame-count
    # policy remains a separate profile/launcher gate. A script is validated
    # through the exact launcher parser before it becomes READY.
    if input_script is not None:
        path, error = _resolve(root, input_script, name="input-script")
        if error or path is None:
            rows["input_binding"] = _record(
                "input_binding",
                ready=False,
                artifact=None,
                source="explicit runtime input script",
                blocking_reasons=[error or "input-script:path-unresolved"],
            )
        else:
            try:
                steps = _validate_input_script(path)
            except (OSError, ProfileError, ValueError) as exc:
                rows["input_binding"] = _record(
                    "input_binding",
                    ready=False,
                    artifact=str(path),
                    source="explicit runtime input script",
                    blocking_reasons=[f"{type(exc).__name__}:{exc}"],
                )
            else:
                rows["input_binding"] = _record(
                    "input_binding",
                    ready=True,
                    artifact=str(path),
                    source="validated explicit runtime input script",
                    validation={
                        "format": INPUT_SCRIPT_FORMAT,
                        "steps": steps,
                        "mode": "script",
                    },
                )
    elif interactive:
        rows["input_binding"] = _record(
            "input_binding",
            ready=True,
            artifact=None,
            source="explicit interactive keyboard input mode",
            validation={"mode": "interactive-keyboard"},
        )
    elif keyboard:
        rows["input_binding"] = _record(
            "input_binding",
            ready=True,
            artifact=None,
            source="explicit bounded keyboard input mode",
            validation={"mode": "keyboard"},
        )

    return rows
