"""Source-backed root-transform state for SGB MultiMatrix owners.

A freshly constructed LOD/HIERARCHY MultiMatrix copies each serialized local
matrix into its matching world slot, so world slot 0 initially equals local
slot 0. Later SceneGraph transform updates replace world slot 0 with the exact
4x4 matrix supplied to the runtime object's vfunc +0x2c before the remaining
MultiMatrix slots are reevaluated.

The important distinction is update-history knowledge:

* ``scenegraph_updates is None`` means the current runtime state is unknown.
* ``scenegraph_updates == []`` means a caller has established that no transform
  update occurred after construction, so local slot 0 is the current root.
* one or more matrices means the last update is the current root.

This avoids silently treating constructor state as current runtime state.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from sgb_multimatrix import matrix_from_record

FORMAT = "SHIFT.SGBRootTransformState/1"
OBJECT_FORMAT = "SHIFT.SGBObjectRuntime/1"
OWNER_KINDS = {"LOD", "HIERARCHY"}


def _kind(report: Mapping[str, Any]) -> str | None:
    value = report.get("kind") or {}
    return value.get("text") if isinstance(value, Mapping) else None


def _matrix(value: Any, label: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 16:
        raise ValueError(f"{label} must contain 16 values")
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc


def constructor_root_matrix(owner_report: Mapping[str, Any]) -> list[float]:
    """Return world slot 0 immediately after retail MultiMatrix construction."""
    if owner_report.get("format") != OBJECT_FORMAT:
        raise ValueError("owner input must be SHIFT.SGBObjectRuntime/1")
    if _kind(owner_report) not in OWNER_KINDS:
        raise ValueError("root owner must be LOD or HIERARCHY")
    records = owner_report.get("matrix_records") or []
    if not records or not isinstance(records[0], Mapping):
        raise ValueError("owner has no MATRIX slot 0")
    return matrix_from_record(records[0])


def build_root_transform_state(
    owner_report: Mapping[str, Any],
    *,
    scenegraph_updates: Sequence[Sequence[float]] | None = None,
) -> dict[str, Any]:
    """Resolve the current root only when SceneGraph update history is known."""
    blockers: list[str] = []
    try:
        initial = constructor_root_matrix(owner_report)
    except ValueError as exc:
        initial = None
        blockers.append(f"sgb-root:{exc}")

    updates: list[list[float]] | None
    if scenegraph_updates is None:
        updates = None
        blockers.append("sgb-root:scenegraph-update-history-unknown")
    else:
        updates = []
        for index, value in enumerate(scenegraph_updates):
            try:
                updates.append(_matrix(value, f"scenegraph_updates[{index}]"))
            except ValueError as exc:
                blockers.append(f"sgb-root:{exc}")

    current = None
    source = None
    if initial is not None and updates is not None and not blockers:
        if updates:
            current = list(updates[-1])
            source = "scenegraph-transform-update"
        else:
            current = list(initial)
            source = "constructor-initial-world-slot-0"

    ready = current is not None and not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "owner_kind": _kind(owner_report),
        "constructor_root_matrix": initial,
        "scenegraph_update_history_known": scenegraph_updates is not None,
        "scenegraph_update_count": None if updates is None else len(updates),
        "scenegraph_updates": updates,
        "current_root_world_matrix": current,
        "current_root_source": source,
        "source": {
            "sgb_node_loader": "FUN_006a4b40",
            "multimatrix_local_initializer": "FUN_0068cbb0",
            "multimatrix_constructor": "FUN_006b144b",
            "hierarchy_root_update": "FUN_006ab710",
            "lod_root_update": "FUN_006b4280",
            "scenegraph_transform_dispatch": "FUN_0068bc60",
            "scenegraph_update_enqueue": "FUN_0068ba90",
            "scenegraph_update_flush": "FUN_0068b840",
            "matrix_copy": "FUN_00401d10",
            "scenegraph_source_file": ".\\Source\\SceneGraph\\CSceneGraph.cpp",
            "transport": (
                "SceneGraph copies 0x40 bytes for queued update type 4, then "
                "replays object vfunc +0x2c with that copied matrix in EDX"
            ),
            "constructor_state": (
                "FUN_0068cbb0 copies local MATRIX slot into matching world slot"
            ),
        },
    }
