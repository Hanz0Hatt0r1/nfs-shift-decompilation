"""Validator for exact D3D9 state captured at one DrawIndexedPrimitive boundary."""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.D3D9DrawStateSnapshot/1"


def validate_draw_snapshot(snapshot: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if snapshot.get("format") not in (None, FORMAT):
        reasons.append("format:invalid")
    for key in (
        "frame",
        "draw_index",
        "draw",
        "vertex_declaration",
        "vertex_shader",
        "pixel_shader",
        "stream_sources",
        "index_binding",
        "constant_writes",
        "texture_bindings",
        "active_stream_sources",
        "active_texture_bindings",
        "constant_state",
    ):
        if key not in snapshot:
            reasons.append(f"{key}:missing")
    if not isinstance(snapshot.get("draw_index"), int) or snapshot.get("draw_index") < 0:
        reasons.append("draw_index:invalid")
    draw = snapshot.get("draw")
    if not isinstance(draw, Mapping):
        reasons.append("draw:invalid")
    else:
        for key in ("primitive_count", "start_index", "base_vertex_index"):
            if not isinstance(draw.get(key), int):
                reasons.append(f"draw:{key}:invalid")
    for key in (
        "stream_sources",
        "active_stream_sources",
        "constant_writes",
        "texture_bindings",
        "active_texture_bindings",
    ):
        if not isinstance(snapshot.get(key), list):
            reasons.append(f"{key}:invalid")
    if not isinstance(snapshot.get("constant_state"), Mapping):
        reasons.append("constant_state:invalid")
    for stage in ("vertex", "pixel"):
        state = (snapshot.get("constant_state") or {}).get(stage)
        if state is not None and not isinstance(state, Mapping):
            reasons.append(f"constant_state:{stage}:invalid")
    return list(dict.fromkeys(reasons))


def validate_draw_snapshots(snapshots: list[Mapping[str, Any]]) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    rows = []
    for index, snapshot in enumerate(snapshots):
        reasons = validate_draw_snapshot(snapshot)
        rows.append(
            {
                "index": index,
                "status": "valid" if not reasons else "invalid",
                "blocking_reasons": reasons,
            }
        )
        blockers.extend({"index": index, "reason": reason} for reason in reasons)
    return {
        "format": FORMAT,
        "status": "valid" if not blockers else "invalid",
        "ready": not blockers,
        "snapshot_count": len(snapshots),
        "snapshots": rows,
        "blocking_reasons": blockers,
    }
