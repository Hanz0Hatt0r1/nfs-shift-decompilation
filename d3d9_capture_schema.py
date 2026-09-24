"""Versioned validator for external SHIFT D3D9 runtime capture events."""
from __future__ import annotations

import math
import re
from typing import Any, Mapping

FORMAT = "SHIFT.D3D9RuntimeCaptureSchema/1"
EVENT_SPECS = {
    "create_vertex_declaration": {"pointer": "declaration_ptr"},
    "set_vertex_declaration": {"pointer": "declaration_ptr"},
    "set_stream_source": {"pointer": "vertex_buffer_ptr"},
    "set_indices": {"pointer": "index_buffer_ptr"},
    "create_vertex_shader": {"pointer": "shader_ptr"},
    "create_pixel_shader": {"pointer": "shader_ptr"},
    "set_vertex_shader": {"pointer": "shader_ptr"},
    "set_pixel_shader": {"pointer": "shader_ptr"},
    "draw_indexed_primitive": {"pointer": None},
    "set_vertex_shader_constant_f": {"pointer": None},
    "set_pixel_shader_constant_f": {"pointer": None},
}
_HEX_RE = re.compile(r"^[0-9a-fA-F]*$")


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def validate_capture_event(row: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    event = row.get("event")
    if event not in EVENT_SPECS:
        return ["event:unsupported"]

    if "frame" not in row:
        reasons.append("frame:missing")
    elif isinstance(row.get("frame"), int) and row["frame"] < 0:
        reasons.append("frame:negative")

    if "event_index" in row:
        if not isinstance(row.get("event_index"), int) or row["event_index"] < 0:
            reasons.append("event-index:invalid")

    if "thread_id" in row and (not isinstance(row.get("thread_id"), int) or row["thread_id"] < 0):
        reasons.append("thread-id:invalid")

    if "device_ptr" in row and row.get("device_ptr") in (None, ""):
        reasons.append("device-ptr:empty")

    pointer_key = EVENT_SPECS[event]["pointer"]
    if pointer_key:
        value = row.get(pointer_key)
        if value in (None, ""):
            reasons.append(f"{pointer_key}:missing")

    if event == "create_vertex_declaration" and row.get("bytes_hex") is not None:
        raw = row.get("bytes_hex")
        if not isinstance(raw, str) or len(raw) % 2 or not _HEX_RE.fullmatch(raw):
            reasons.append("declaration-bytes:invalid-hex")
        elif not raw:
            reasons.append("declaration-bytes:empty")

    if event in {"create_vertex_shader", "create_pixel_shader"} and row.get("bytes_hex") is not None:
        raw = row.get("bytes_hex")
        if not isinstance(raw, str) or len(raw) % 2 or not _HEX_RE.fullmatch(raw):
            reasons.append("shader-bytes:invalid-hex")
        elif not raw:
            reasons.append("shader-bytes:empty")

    if event == "set_stream_source":
        if not isinstance(row.get("stream"), int) or row["stream"] < 0:
            reasons.append("stream:invalid")
        if not isinstance(row.get("offset_in_bytes"), int) or row["offset_in_bytes"] < 0:
            reasons.append("stream-offset:invalid")
        if not isinstance(row.get("stride"), int) or row["stride"] <= 0:
            reasons.append("stream-stride:invalid")

    if event == "draw_indexed_primitive":
        for key in ("primitive_count", "start_index", "base_vertex_index"):
            if key in row and not isinstance(row.get(key), int):
                reasons.append(f"draw:{key}:invalid")
        if isinstance(row.get("primitive_count"), int) and row["primitive_count"] < 0:
            reasons.append("draw:primitive-count-negative")

    if event in {"set_vertex_shader_constant_f", "set_pixel_shader_constant_f"}:
        start = row.get("start_register")
        count = row.get("vector4f_count", row.get("register_count"))
        values = row.get("values")
        if not isinstance(start, int) or start < 0:
            reasons.append("constant:start-register-invalid")
        if not isinstance(count, int) or count <= 0:
            reasons.append("constant:vector-count-invalid")
        if not isinstance(values, list) or not all(_finite_number(x) for x in values):
            reasons.append("constant:values-invalid")
            if isinstance(values, list) and all(isinstance(x, (int, float)) for x in values):
                reasons.append("constant:values-nonfinite")
        elif isinstance(count, int) and count > 0 and len(values) != count * 4:
            reasons.append("constant:values-length-mismatch")

    if event in {"set_vertex_declaration", "create_vertex_declaration"}:
        if row.get("resource_sha256") is not None and not isinstance(row.get("resource_sha256"), str):
            reasons.append("resource-sha256:invalid")
        if row.get("resource_path") is not None and not isinstance(row.get("resource_path"), str):
            reasons.append("resource-path:invalid")

    return list(dict.fromkeys(reasons))


def validate_capture_events(events: list[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    blockers = []
    previous_event_index: int | None = None
    previous_frame: int | None = None

    for idx, row in enumerate(events):
        reasons = validate_capture_event(row)

        event_index = row.get("event_index")
        if isinstance(event_index, int):
            if previous_event_index is not None and event_index != previous_event_index + 1:
                reasons.append("event-index:sequence-gap")
            previous_event_index = event_index

        frame = row.get("frame")
        if isinstance(frame, int):
            if previous_frame is not None and frame < previous_frame:
                reasons.append("frame:sequence-regression")
            previous_frame = frame

        reasons = list(dict.fromkeys(reasons))
        rows.append({
            "event_index": idx,
            "event": row.get("event"),
            "status": "valid" if not reasons else "invalid",
            "blocking_reasons": reasons,
        })
        blockers.extend({"event_index": idx, "reason": x} for x in reasons)

    return {
        "format": FORMAT,
        "status": "valid" if not blockers else "invalid",
        "ready": not blockers,
        "event_count": len(events),
        "events": rows,
        "blocking_reasons": blockers,
    }
