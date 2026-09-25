"""Correlate external D3D9 capture events with SHIFT MEB evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from d3d9_declaration_instance import decode_d3d9_declaration_records
from shader_ir import parse_shader_blobs
from shader_permutation_identity import build_shader_permutation_identity
from d3d9_capture_schema import validate_capture_event
from d3d9_runtime_trace_integrity import validate_runtime_trace_integrity
from d3d9_draw_snapshot_schema import validate_draw_snapshot

FORMAT = "SHIFT.D3D9RuntimeBindingEvidence/1"
EVENTS = {
    "create_vertex_declaration",
    "set_vertex_declaration",
    "set_stream_source",
    "set_indices",
    "set_texture",
    "present_screenshot",
    "present_screenshot_failed",
    "draw_indexed_primitive",
    "create_vertex_shader",
    "create_pixel_shader",
    "set_vertex_shader",
    "set_pixel_shader",
    "set_vertex_shader_constant_f",
    "set_pixel_shader_constant_f",
}


def _ptr(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, int):
        return f"0x{value:x}"
    value = str(value).strip()
    if not value:
        return None
    try:
        return f"0x{int(value, 0):x}"
    except ValueError:
        return value.lower()


def _norm(value: Any) -> str | None:
    return None if value is None else str(value).replace("\\", "/").strip("/").lower()


def load_events(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"trace line {line_no}: invalid JSON") from exc
        if not isinstance(row, dict) or row.get("event") not in EVENTS:
            raise ValueError(f"trace line {line_no}: unsupported event")
        schema_reasons = validate_capture_event(row)
        if schema_reasons:
            raise ValueError(
                f"trace line {line_no}: capture schema invalid: " + ", ".join(schema_reasons)
            )
        row["_line"] = line_no
        rows.append(row)
    return rows


def _decode_declaration(row: Mapping[str, Any]) -> dict[str, Any] | None:
    raw = row.get("bytes_hex")
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError(f"declaration event line {row.get('_line')}: bytes_hex must be a string")
    try:
        payload = bytes.fromhex(raw)
    except ValueError as exc:
        raise ValueError(f"declaration event line {row.get('_line')}: invalid bytes_hex") from exc
    report = decode_d3d9_declaration_records(payload)
    report["payload_sha256"] = hashlib.sha256(payload).hexdigest()
    return report


def _sort_key(value: Any) -> tuple[int, str]:
    try:
        return (0, f"{int(value):020d}")
    except (TypeError, ValueError):
        return (1, str(value))


def build_runtime_binding_evidence(
    events: Iterable[Mapping[str, Any]],
    *,
    meb_resource: Mapping[str, Any] | None = None,
    usage_ordinal_map: Mapping[int, int] | None = None,
) -> dict[str, Any]:
    rows = [dict(row) for row in events]
    integrity = validate_runtime_trace_integrity(rows)
    declarations: dict[str, dict[str, Any]] = {}
    shaders: dict[str, dict[str, Any]] = {}
    frames: defaultdict[str, dict[str, Any]] = defaultdict(lambda: {
        "frame": None, "vertex_declaration": None, "vertex_shader": None, "pixel_shader": None,
        "constant_writes": [], "stream_sources": [], "index_binding": None, "texture_bindings": [], "screenshot_events": [], "draws": [], "draw_snapshots": [],
    })
    blockers: list[dict[str, Any]] = []

    for row in rows:
        frame_key = str(row.get("frame", "unknown"))
        frame = frames[frame_key]
        frame["frame"] = row.get("frame")
        event = row["event"]
        if event == "create_vertex_declaration":
            pointer = _ptr(row.get("declaration_ptr"))
            decoded = _decode_declaration(row)
            if not pointer:
                blockers.append({"line": row.get("_line"), "reason": "declaration-pointer-missing"})
                continue
            declarations[pointer] = {
                "pointer": pointer,
                "line": row.get("_line"),
                "source_sha256": row.get("source_sha256"),
                "raw_bytes_sha256": decoded.get("payload_sha256") if decoded else None,
                "decoded": decoded,
            }
        elif event == "set_vertex_declaration":
            pointer = _ptr(row.get("declaration_ptr"))
            frame["vertex_declaration"] = {
                "declaration_ptr": pointer,
                "line": row.get("_line"),
                "resource_sha256": row.get("resource_sha256"),
                "resource_path": row.get("resource_path"),
                "create_known": bool(pointer and pointer in declarations),
                "declaration_sha256": declarations.get(pointer, {}).get("raw_bytes_sha256") if pointer else None,
            }
        elif event == "set_stream_source":
            frame["stream_sources"].append({
                "stream": row.get("stream"),
                "vertex_buffer_ptr": _ptr(row.get("vertex_buffer_ptr")),
                "offset_in_bytes": row.get("offset_in_bytes"),
                "stride": row.get("stride"),
                "line": row.get("_line"),
            })
        elif event == "set_indices":
            frame["index_binding"] = {
                "index_buffer_ptr": _ptr(row.get("index_buffer_ptr")),
                "line": row.get("_line"),
            }
        elif event == "set_texture":
            binding = {
                "stage": row.get("stage"),
                "texture_ptr": _ptr(row.get("texture_ptr")),
                "line": row.get("_line"),
            }
            descriptor = {
                key: row.get(key)
                for key in (
                    "resource_descriptor_status",
                    "resource_type",
                    "resource_type_name",
                    "width",
                    "height",
                    "depth",
                    "format",
                    "pool",
                    "level_count",
                )
                if key in row
            }
            if descriptor:
                binding["resource_descriptor"] = descriptor
            binding["snapshot_status"] = row.get("snapshot_status")
            binding["snapshot_paths"] = list(row.get("snapshot_paths") or [])
            frame["texture_bindings"].append(binding)
        elif event in {"present_screenshot", "present_screenshot_failed"}:
            frame["screenshot_events"].append({
                "event": event,
                "path": row.get("path"),
                "reason": row.get("reason"),
                "line": row.get("_line"),
            })
        elif event in {"create_vertex_shader", "create_pixel_shader"}:
            pointer = _ptr(row.get("shader_ptr"))
            if not pointer:
                blockers.append({"line": row.get("_line"), "reason": "shader-pointer-missing"})
                continue
            raw = row.get("bytes_hex")
            payload = None
            decoded = None
            if raw is not None:
                if not isinstance(raw, str):
                    raise ValueError(f"shader event line {row.get('_line')}: bytes_hex must be a string")
                try:
                    payload = bytes.fromhex(raw)
                except ValueError as exc:
                    raise ValueError(f"shader event line {row.get('_line')}: invalid bytes_hex") from exc
                blobs = parse_shader_blobs(payload)
                if len(blobs) != 1:
                    raise ValueError(f"shader event line {row.get('_line')}: expected exactly one shader blob")
                decoded = {
                    "stage": blobs[0].stage,
                    "version": [blobs[0].major, blobs[0].minor],
                    "raw_bytes_sha256": hashlib.sha256(payload).hexdigest(),
                }
            shaders[pointer] = {
                "pointer": pointer,
                "stage": "vertex" if event == "create_vertex_shader" else "pixel",
                "line": row.get("_line"),
                "raw_bytes_hex": payload.hex() if payload is not None else None,
                "decoded": decoded,
            }
        elif event in {"set_vertex_shader", "set_pixel_shader"}:
            pointer = _ptr(row.get("shader_ptr"))
            frame["vertex_shader" if event == "set_vertex_shader" else "pixel_shader"] = {
                "shader_ptr": pointer,
                "line": row.get("_line"),
                "create_known": bool(pointer and pointer in shaders),
            }
        elif event in {"set_vertex_shader_constant_f", "set_pixel_shader_constant_f"}:
            start_register = row.get("start_register")
            vector_count = row.get("vector4f_count", row.get("register_count"))
            values = row.get("values")
            if not isinstance(start_register, int) or start_register < 0:
                blockers.append({"line": row.get("_line"), "reason": "shader-constant-start-register-invalid"})
                continue
            if not isinstance(vector_count, int) or vector_count <= 0:
                blockers.append({"line": row.get("_line"), "reason": "shader-constant-vector-count-invalid"})
                continue
            if not isinstance(values, list) or len(values) != vector_count * 4 or not all(isinstance(x, (int, float)) for x in values):
                blockers.append({"line": row.get("_line"), "reason": "shader-constant-values-invalid"})
                continue
            frame["constant_writes"].append({
                "stage": "vertex" if event == "set_vertex_shader_constant_f" else "pixel",
                "start_register": start_register,
                "vector4f_count": vector_count,
                "values": [float(x) for x in values],
                "line": row.get("_line"),
            })
        elif event == "draw_indexed_primitive":
            draw = {
                "primitive_count": row.get("primitive_count"),
                "start_index": row.get("start_index"),
                "base_vertex_index": row.get("base_vertex_index"),
                "line": row.get("_line"),
            }
            frame["draws"].append(draw)
            # Freeze the complete D3D9 state at the exact draw boundary. A
            # frame-level aggregate is insufficient for same-instance proof:
            # later state changes in the same frame must not retroactively
            # change which declaration/shaders/buffers were used by this draw.
            active_streams = {}
            for stream_row in frame["stream_sources"]:
                try:
                    active_streams[int(stream_row.get("stream"))] = dict(stream_row)
                except (TypeError, ValueError):
                    continue

            active_textures = {}
            for texture_row in frame["texture_bindings"]:
                try:
                    active_textures[int(texture_row.get("stage"))] = dict(texture_row)
                except (TypeError, ValueError):
                    continue

            constant_state = {"vertex": {}, "pixel": {}}
            for write in frame["constant_writes"]:
                stage = str(write.get("stage") or "").lower()
                if stage not in constant_state:
                    continue
                try:
                    start = int(write.get("start_register"))
                    count = int(write.get("vector4f_count"))
                    values = list(write.get("values") or [])
                except (TypeError, ValueError):
                    continue
                for offset in range(count):
                    chunk = values[offset * 4:(offset + 1) * 4]
                    if len(chunk) == 4:
                        constant_state[stage][str(start + offset)] = [float(x) for x in chunk]

            snapshot = {
                "frame": frame.get("frame"),
                "draw_index": len(frame["draws"]) - 1,
                "draw": dict(draw),
                "vertex_declaration": dict(frame["vertex_declaration"] or {}),
                "vertex_shader": dict(frame["vertex_shader"] or {}),
                "pixel_shader": dict(frame["pixel_shader"] or {}),
                "stream_sources": [dict(x) for x in frame["stream_sources"]],
                "active_stream_sources": [active_streams[key] for key in sorted(active_streams)],
                "index_binding": dict(frame["index_binding"] or {}),
                "texture_bindings": [dict(x) for x in frame["texture_bindings"]],
                "active_texture_bindings": [active_textures[key] for key in sorted(active_textures)],
                "constant_writes": [dict(x) for x in frame["constant_writes"]],
                "constant_state": constant_state,
            }
            vs = snapshot["vertex_shader"]
            ps = snapshot["pixel_shader"]
            vsp = shaders.get(vs.get("shader_ptr")) if vs.get("shader_ptr") else None
            psp = shaders.get(ps.get("shader_ptr")) if ps.get("shader_ptr") else None
            vraw = bytes.fromhex(vsp["raw_bytes_hex"]) if vsp and vsp.get("raw_bytes_hex") else None
            praw = bytes.fromhex(psp["raw_bytes_hex"]) if psp and psp.get("raw_bytes_hex") else None
            if vraw and praw:
                try:
                    snapshot["shader_permutation_identity"] = build_shader_permutation_identity(
                        vraw + praw,
                        vertex_offset=0,
                        pixel_offset=len(vraw),
                    )
                except Exception as exc:
                    snapshot["shader_permutation_identity"] = {
                        "status": "error",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
            else:
                snapshot["shader_permutation_identity"] = None
            snapshot_reasons = validate_draw_snapshot(snapshot)
            if snapshot_reasons:
                blockers.extend(
                    {"line": row.get("_line"), "reason": f"draw-snapshot:{reason}"}
                    for reason in snapshot_reasons
                )
            frame["draw_snapshots"].append(snapshot)

    correlation: dict[str, Any] = {
        "status": "not-supplied",
        "resource_identity": None,
        "descriptor_matches": [],
    }
    if meb_resource is not None:
        source = meb_resource.get("source") if isinstance(meb_resource.get("source"), Mapping) else {}
        meb_sha = meb_resource.get("resource_sha256") or source.get("resource_sha256")
        meb_path = meb_resource.get("resource") or source.get("root_relative_path")
        correlation["status"] = "not-proven"
        correlation["resource_identity"] = {"resource_sha256": meb_sha, "resource_path": meb_path}
        for descriptor in meb_resource.get("property_descriptors", []):
            if not isinstance(descriptor, Mapping):
                continue
            words = descriptor.get("words")
            if not isinstance(words, list) or len(words) < 3:
                continue
            type_ordinal, usage_ordinal, channel = map(int, words[:3])
            runtime_usage = usage_ordinal_map.get(usage_ordinal) if usage_ordinal_map is not None else None
            matches: list[dict[str, Any]] = []
            for declaration in declarations.values():
                decoded = declaration.get("decoded") or {}
                for record in decoded.get("records", []):
                    if record.get("type") != type_ordinal or record.get("usage_index") != channel:
                        continue
                    if runtime_usage is None or record.get("usage") != runtime_usage:
                        continue
                    matches.append({
                        "declaration_ptr": declaration["pointer"],
                        "record_index": record.get("index"),
                        "type": record.get("type"),
                        "usage": record.get("usage"),
                        "usage_index": record.get("usage_index"),
                    })
            correlation["descriptor_matches"].append({
                "property_id": str(descriptor.get("id")),
                "type_ordinal": type_ordinal,
                "usage_ordinal": usage_ordinal,
                "channel": channel,
                "runtime_usage_required": runtime_usage,
                "status": "match" if matches else ("not-proven" if usage_ordinal_map is None else "not-found"),
                "matches": matches,
            })
        if correlation["descriptor_matches"]:
            correlation["status"] = "observed"

    same_instance_candidates: list[dict[str, Any]] = []
    valid_bound_frames: list[dict[str, Any]] = []
    frame_rows: list[dict[str, Any]] = []
    for frame_key in sorted(frames, key=_sort_key):
        frame = frames[frame_key]
        frame_binding = frame["vertex_declaration"]
        frame_same_resource = None
        if frame_binding and meb_resource is not None:
            identity = correlation["resource_identity"] or {}
            if frame_binding.get("resource_sha256") and identity.get("resource_sha256"):
                frame_same_resource = frame_binding["resource_sha256"] == identity["resource_sha256"]
            elif frame_binding.get("resource_path") and identity.get("resource_path"):
                frame_same_resource = _norm(frame_binding["resource_path"]) == _norm(identity["resource_path"])

        shader_pair_identity = None
        vs = frame.get("vertex_shader") or {}
        ps = frame.get("pixel_shader") or {}
        vsp = shaders.get(vs.get("shader_ptr")) if vs.get("shader_ptr") else None
        psp = shaders.get(ps.get("shader_ptr")) if ps.get("shader_ptr") else None
        vraw = bytes.fromhex(vsp["raw_bytes_hex"]) if vsp and vsp.get("raw_bytes_hex") else None
        praw = bytes.fromhex(psp["raw_bytes_hex"]) if psp and psp.get("raw_bytes_hex") else None
        if vraw and praw:
            try:
                shader_pair_identity = build_shader_permutation_identity(
                    vraw + praw,
                    vertex_offset=0,
                    pixel_offset=len(vraw),
                )
            except Exception as exc:
                shader_pair_identity = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

        # Observational frame summary remains available for compatibility.
        frame_rows.append({
            **frame,
            "shader_permutation_identity": shader_pair_identity,
            "binding": {
                "status": "observed" if frame_binding and frame_binding.get("create_known") else ("partial" if frame_binding else "not-observed"),
                "same_meb_resource": frame_same_resource,
                "declaration_decode_status": (
                    (declarations.get(_ptr((frame_binding or {}).get("declaration_ptr")) if frame_binding else None) or {}).get("decoded", {}) or {}
                ).get("status"),
                "bound_declaration_valid": bool(
                    frame_binding
                    and (declarations.get(_ptr(frame_binding.get("declaration_ptr"))) or {}).get("decoded", {}).get("status") == "match"
                ),
            },
        })

        # Same-instance proof is now draw-local. State observed after a draw
        # cannot be used to authenticate that earlier draw.
        for snapshot in frame.get("draw_snapshots") or []:
            binding = snapshot.get("vertex_declaration") or {}
            same_resource = None
            if binding and meb_resource is not None:
                identity = correlation["resource_identity"] or {}
                if binding.get("resource_sha256") and identity.get("resource_sha256"):
                    same_resource = binding["resource_sha256"] == identity["resource_sha256"]
                elif binding.get("resource_path") and identity.get("resource_path"):
                    same_resource = _norm(binding["resource_path"]) == _norm(identity["resource_path"])

            binding_ptr = binding.get("declaration_ptr")
            bound_decl = declarations.get(binding_ptr) if binding_ptr else None
            bound_decl_decoded = (bound_decl or {}).get("decoded") or {}
            bound_decl_valid = bool(bound_decl and bound_decl_decoded.get("status") == "match")
            snapshot_schema_reasons = validate_draw_snapshot(snapshot)
            snapshot_schema_valid = not snapshot_schema_reasons
            frame_candidate = {
                "frame": frame.get("frame"),
                "draw_index": snapshot.get("draw_index"),
                "draw": dict(snapshot.get("draw") or {}),
                "declaration_ptr": binding_ptr,
                "same_meb_resource": same_resource,
                "declaration_create_known": bool(binding.get("create_known")),
                "declaration_decode_status": bound_decl_decoded.get("status"),
                "bound_declaration_valid": bound_decl_valid,
                "indexed_draw_present": True,
                "snapshot_schema_status": "valid" if snapshot_schema_valid else "invalid",
                "snapshot_schema_blocking_reasons": snapshot_schema_reasons,
                "descriptor_matches": [],
            }

            if snapshot_schema_valid and bound_decl_valid and usage_ordinal_map is not None and same_resource is True and meb_resource is not None:
                bound_records = bound_decl_decoded.get("records", [])
                for descriptor in meb_resource.get("property_descriptors", []):
                    if not isinstance(descriptor, Mapping):
                        continue
                    words = descriptor.get("words")
                    if not isinstance(words, list) or len(words) < 3:
                        continue
                    type_ordinal, usage_ordinal, channel = map(int, words[:3])
                    runtime_usage = usage_ordinal_map.get(usage_ordinal)
                    matched_records = [
                        record for record in bound_records
                        if record.get("type") == type_ordinal
                        and record.get("usage") == runtime_usage
                        and record.get("usage_index") == channel
                    ]
                    if matched_records:
                        frame_candidate["descriptor_matches"].append({
                            "property_id": str(descriptor.get("id")),
                            "type_ordinal": type_ordinal,
                            "usage_ordinal": usage_ordinal,
                            "runtime_usage": runtime_usage,
                            "channel": channel,
                            "record_indices": [record.get("index") for record in matched_records],
                        })

            if snapshot_schema_valid and bound_decl_valid and same_resource is True:
                valid_bound_frames.append(frame_candidate)
            if snapshot_schema_valid and frame_candidate["descriptor_matches"]:
                same_instance_candidates.append(frame_candidate)

    return {
        "format": FORMAT,
        "status": "observed" if declarations and frame_rows else "partial",
        "integrity": integrity,
        "trace": {
            "event_count": len(rows),
            "declaration_instance_count": len(declarations),
            "decoded_declaration_count": sum(1 for x in declarations.values() if x.get("decoded")),
            "shader_object_count": len(shaders),
            "decoded_shader_count": sum(1 for x in shaders.values() if x.get("decoded")),
            "constant_write_count": sum(len(x.get("constant_writes", [])) for x in frame_rows),
            "frame_count": len(frame_rows),
            "source": "external-runtime-capture",
        },
        "declarations": list(declarations.values()),
        "shaders": list(shaders.values()),
        "frames": frame_rows,
        "meb_correlation": correlation,
        "evidence_boundary": {
            "runtime_frame_identity": "observed" if frame_rows else "not-supplied",
            "specific_mesh_instance": "observed" if any(x["binding"].get("same_meb_resource") is True for x in frame_rows) else "not-proven",
            "usage_ordinal_mapping": "observed" if usage_ordinal_map is not None else "not-supplied",
        },
        "same_instance_gate": {
            "status": (
                "proven"
                if same_instance_candidates
                else "not-proven"
            ),
            "ready": bool(same_instance_candidates),
            "candidate_frames": same_instance_candidates,
            "requirements": {
                "same_meb_resource": True,
                "bound_declaration_known": True,
                "bound_declaration_decoder_status": "match",
                "usage_ordinal_mapping": "required",
                "descriptor_match_on_bound_declaration": True,
                "indexed_draw_present": True,
            },
            "blocking_reasons": list(dict.fromkeys(
                (
                    ["frame:same-meb-resource-not-observed"]
                    if not any(x["binding"].get("same_meb_resource") is True for x in frame_rows)
                    else []
                )
                + (
                    ["declaration:bound-instance-not-valid"]
                    if any(
                        x["binding"].get("same_meb_resource") is True
                        and x["binding"].get("bound_declaration_valid") is not True
                        for x in frame_rows
                    )
                    and not valid_bound_frames
                    else []
                )
                + (
                    ["usage-ordinal-map:not-supplied"]
                    if usage_ordinal_map is None
                    else []
                )
                + (
                    # This is intentionally diagnostic only. Proof is never
                    # taken from frame-level aggregate state: a valid BMW
                    # declaration can be bound before/after a different draw.
                    ["descriptor:bound-instance-no-match"]
                    if usage_ordinal_map is not None
                    and not same_instance_candidates
                    and any(
                        x["binding"].get("same_meb_resource") is True
                        and x["binding"].get("bound_declaration_valid") is True
                        for x in frame_rows
                    )
                    and not any(
                        snapshot.get("descriptor_matches")
                        for frame in frame_rows
                        for snapshot in (frame.get("draw_snapshots") or [])
                    )
                    else []
                )
                + (
                    ["draw:same-frame-indexed-draw-not-observed"]
                    if usage_ordinal_map is not None
                    and not same_instance_candidates
                    and any(
                        x["binding"].get("same_meb_resource") is True
                        for x in frame_rows
                    )
                    and not valid_bound_frames
                    else []
                )
            )),
        },
        "blocking_reasons": blockers,
    }


def write_report(report: Mapping[str, Any], output: str | Path) -> None:
    Path(output).write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SHIFT D3D9 runtime binding evidence from JSONL capture")
    parser.add_argument("trace")
    parser.add_argument("output")
    parser.add_argument("--meb-resource")
    parser.add_argument("--usage-map")
    args = parser.parse_args()
    meb = json.loads(Path(args.meb_resource).read_text(encoding="utf-8")) if args.meb_resource else None
    raw_map = json.loads(Path(args.usage_map).read_text(encoding="utf-8")) if args.usage_map else None
    usage_map = {int(k): int(v) for k, v in raw_map.items()} if raw_map else None
    write_report(build_runtime_binding_evidence(load_events(args.trace), meb_resource=meb, usage_ordinal_map=usage_map), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
