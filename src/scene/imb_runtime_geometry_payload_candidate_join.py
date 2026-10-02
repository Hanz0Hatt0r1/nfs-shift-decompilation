"""Narrow runtime IMB geometry candidates with exact captured VB/IB payload bytes.

Phase 616 consumes the Phase 615 geometry-pointer candidate join, a D3D9 JSONL
capture containing full ``buffer_payload`` snapshots, and the static Silverstone
IMB corpus. It reconstructs the retail runtime-interleaved stream-0 vertex
buffer and per-primitive little-endian u16 index buffer directly from source IMB
bytes, then intersects candidate sets only when both runtime payload generations
are stable and every static candidate has a complete exact payload fingerprint.

Exact geometry bytes identify geometry content, not archive path, material,
scene instance, or render admission. Missing/unstable/incomplete evidence fails
open and never removes a static candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable, Mapping

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FORMATS_DIR = _REPO_ROOT / "src" / "formats"
for _path in (_REPO_ROOT, _FORMATS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from imb_format import parse_imb_binary_mesh
from shift_importer import BFF

FORMAT = "SHIFT.IMBRuntimeGeometryPayloadCandidateJoin/1"
POINTER_JOIN_FORMAT = "SHIFT.IMBRuntimeGeometryPointerCandidateJoin/1"


def _valid_sha(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _norm_resource_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip().lstrip("./").lower()


def resolve_input_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate
    repo_candidate = _REPO_ROOT / candidate
    if repo_candidate.exists():
        return repo_candidate
    raise FileNotFoundError(
        f"input file not found: {candidate} (also tried {repo_candidate})"
    )


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _interleaved_vertex_buffer(source: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild the exact retail runtime-interleaved stream-0 VB bytes.

    IMB stores one planar source payload per Type/Usage/Channel descriptor. The
    recovered loader assigns each source stream a deterministic
    ``runtime_element_offset`` and a total ``runtime_vertex_stride``. Exact
    hashing is allowed only when those source records cover every runtime stride
    byte once; padding or overlap is treated as incomplete evidence.
    """
    header = source.get("header")
    streams_root = source.get("streams")
    if not isinstance(header, Mapping) or not isinstance(streams_root, Mapping):
        return {"status": "source-layout-missing", "ready": False}
    try:
        vertex_count = int(header.get("vertex_count"))
        stride = int(streams_root.get("runtime_vertex_stride"))
    except (TypeError, ValueError):
        return {"status": "source-layout-invalid", "ready": False}
    if vertex_count <= 0 or stride <= 0:
        return {"status": "source-layout-invalid", "ready": False}

    records = streams_root.get("records")
    if not isinstance(records, list) or not records:
        return {"status": "source-streams-missing", "ready": False}

    coverage = [0] * stride
    output = bytearray(vertex_count * stride)
    properties: list[dict[str, int]] = []
    for raw_stream in records:
        if not isinstance(raw_stream, Mapping):
            return {"status": "source-stream-invalid", "ready": False}
        try:
            element_size = int(raw_stream.get("element_size_bytes"))
            element_offset = int(raw_stream.get("runtime_element_offset"))
            type_ordinal = int(raw_stream.get("type_ordinal"))
            usage_ordinal = int(raw_stream.get("usage_ordinal"))
            channel = int(raw_stream.get("channel"))
        except (TypeError, ValueError):
            return {"status": "source-stream-invalid", "ready": False}
        if (
            element_size <= 0
            or element_offset < 0
            or element_offset + element_size > stride
        ):
            return {"status": "source-stream-outside-stride", "ready": False}
        try:
            payload = bytes.fromhex(str(raw_stream.get("vertex_payload_hex") or ""))
        except ValueError:
            return {"status": "source-stream-payload-invalid", "ready": False}
        if len(payload) != vertex_count * element_size:
            return {"status": "source-stream-payload-size-mismatch", "ready": False}

        for byte_offset in range(element_offset, element_offset + element_size):
            coverage[byte_offset] += 1
        for vertex_index in range(vertex_count):
            source_start = vertex_index * element_size
            target_start = vertex_index * stride + element_offset
            output[target_start : target_start + element_size] = payload[
                source_start : source_start + element_size
            ]
        properties.append({
            "type_ordinal": type_ordinal,
            "usage_ordinal": usage_ordinal,
            "channel": channel,
            "runtime_element_offset": element_offset,
            "element_size_bytes": element_size,
        })

    if any(value == 0 for value in coverage):
        return {
            "status": "runtime-stride-has-uncovered-bytes",
            "ready": False,
            "vertex_count": vertex_count,
            "stride": stride,
        }
    if any(value > 1 for value in coverage):
        return {
            "status": "runtime-stride-has-overlapping-streams",
            "ready": False,
            "vertex_count": vertex_count,
            "stride": stride,
        }

    payload = bytes(output)
    return {
        "status": "ready",
        "ready": True,
        "sha256": _sha256_bytes(payload),
        "byte_size": len(payload),
        "vertex_count": vertex_count,
        "stride": stride,
        "properties": properties,
    }


def _primitive_index_payloads(source: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    primitives = source.get("primitives")
    if not isinstance(primitives, Mapping):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for raw in primitives.get("records") or []:
        if not isinstance(raw, Mapping):
            continue
        try:
            primitive_index = int(raw.get("index"))
            indices = [int(value) for value in (raw.get("indices_u16") or [])]
            triangle_count = int(raw.get("triangle_count"))
        except (TypeError, ValueError):
            continue
        if (
            primitive_index < 0
            or not indices
            or any(value < 0 or value > 0xFFFF for value in indices)
        ):
            continue
        if len(indices) != triangle_count * 3:
            continue
        payload = struct.pack("<" + "H" * len(indices), *indices)
        result[str(primitive_index)] = {
            "status": "ready",
            "sha256": _sha256_bytes(payload),
            "byte_size": len(payload),
            "index_count": len(indices),
            "primitive_count": triangle_count,
            "index_format": 101,
        }
    return result


def build_static_geometry_payload_fingerprint(data: bytes) -> dict[str, Any]:
    digest = _sha256_bytes(data)
    try:
        source = parse_imb_binary_mesh(data, decode_primitives=True)
    except Exception as exc:
        return {
            "status": "decode-failed",
            "ready": False,
            "imb_sha256": digest,
            "error_kind": type(exc).__name__,
            "error": str(exc),
        }
    vertex = _interleaved_vertex_buffer(source)
    primitives = _primitive_index_payloads(source)
    ready = vertex.get("ready") is True and bool(primitives)
    return {
        "status": "ready" if ready else "incomplete",
        "ready": ready,
        "imb_sha256": digest,
        "vertex_buffer": vertex,
        "primitives": primitives,
    }


def _candidate_requests(
    pointer_join: Mapping[str, Any],
) -> tuple[set[str], dict[str, set[str]]]:
    wanted_shas: set[str] = set()
    wanted_paths: dict[str, set[str]] = defaultdict(set)
    for shape in pointer_join.get("resource_shapes") or []:
        if not isinstance(shape, Mapping):
            continue
        for identity in shape.get("geometry_pointer_identities") or []:
            if not isinstance(identity, Mapping):
                continue
            for group in identity.get("candidate_content_groups") or []:
                if not isinstance(group, Mapping):
                    continue
                digest = _valid_sha(group.get("imb_sha256"))
                if not digest:
                    continue
                wanted_shas.add(digest)
                for path in group.get("imb_paths") or []:
                    normalized = _norm_resource_path(path)
                    if normalized:
                        wanted_paths[normalized].add(digest)
    return wanted_shas, wanted_paths


def _materialize_bffs(
    inputs: Iterable[str | Path],
    stack: ExitStack,
) -> list[Path]:
    paths: list[Path] = []
    for source in inputs:
        path = resolve_input_path(source)
        if path.suffix.lower() != ".zip":
            paths.append(path)
            continue
        archive = zipfile.ZipFile(path)
        stack.callback(archive.close)
        root = Path(
            stack.enter_context(
                tempfile.TemporaryDirectory(prefix="shift-phase616-corpus-")
            )
        )
        for name in archive.namelist():
            if not name.lower().endswith(".bff") or name.endswith("/"):
                continue
            target = root / Path(name).name
            target.write_bytes(archive.read(name))
            paths.append(target)
    return paths


def build_static_payload_inventory(
    pointer_join: Mapping[str, Any],
    corpus_inputs: Iterable[str | Path],
) -> dict[str, Any]:
    wanted_shas, wanted_paths = _candidate_requests(pointer_join)
    by_sha: dict[str, dict[str, Any]] = {}
    occurrences: dict[str, list[dict[str, Any]]] = defaultdict(list)
    path_digest_mismatches: list[dict[str, Any]] = []

    with ExitStack() as stack:
        for bff_path in _materialize_bffs(corpus_inputs, stack):
            with BFF(bff_path) as archive:
                for entry in archive.entries:
                    logical = _norm_resource_path(entry.path)
                    expected = wanted_paths.get(logical)
                    if not expected:
                        continue
                    try:
                        payload = archive.extract_entry(entry, type2="lzx")
                    except Exception as exc:
                        path_digest_mismatches.append({
                            "archive": archive.path.name,
                            "path": logical,
                            "status": "extract-failed",
                            "error_kind": type(exc).__name__,
                            "error": str(exc),
                        })
                        continue
                    digest = _sha256_bytes(payload)
                    if digest not in expected:
                        path_digest_mismatches.append({
                            "archive": archive.path.name,
                            "path": logical,
                            "status": "decoded-sha-mismatch",
                            "observed_sha256": digest,
                            "expected_sha256s": sorted(expected),
                        })
                        continue
                    fingerprint = by_sha.get(digest)
                    if fingerprint is None:
                        fingerprint = build_static_geometry_payload_fingerprint(payload)
                        by_sha[digest] = fingerprint
                    occurrences[digest].append({
                        "archive": archive.path.name,
                        "path": logical,
                    })

    for digest, fingerprint in by_sha.items():
        fingerprint["occurrences"] = sorted(
            occurrences[digest],
            key=lambda row: (
                str(row["archive"]).lower(),
                str(row["path"]).lower(),
            ),
        )

    missing = sorted(wanted_shas - set(by_sha))
    ready_count = sum(
        1 for row in by_sha.values() if row.get("ready") is True
    )
    return {
        "candidate_imb_sha256_count": len(wanted_shas),
        "found_imb_sha256_count": len(by_sha),
        "ready_imb_sha256_count": ready_count,
        "missing_imb_sha256s": missing,
        "path_digest_mismatches": path_digest_mismatches,
        "by_imb_sha256": by_sha,
    }


def _buffer_generation_key(
    kind: str,
    pointer: str,
    creation_event_index: int,
) -> str:
    return f"{kind}|{pointer.lower()}|{creation_event_index}"


def _payload_path_candidates(
    raw_value: Any,
    *,
    capture_path: Path,
    payload_root: Path | None,
) -> list[Path]:
    text = str(raw_value or "").strip()
    if not text:
        return []
    raw = Path(text).expanduser()
    basename = PureWindowsPath(text.replace("/", "\\")).name
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append(capture_path.parent / raw)
        candidates.append(raw)
    if payload_root is not None:
        candidates.append(payload_root / raw)
        if basename:
            candidates.append(payload_root / basename)
    if basename:
        candidates.append(capture_path.parent / "buffers" / basename)
        candidates.append(capture_path.parent / basename)
    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            deduped.append(candidate)
    return deduped


def collect_runtime_buffer_payloads(
    capture_path: str | Path,
    *,
    payload_root: str | Path | None = None,
) -> dict[str, Any]:
    capture = resolve_input_path(capture_path)
    root = Path(payload_root).expanduser() if payload_root is not None else None
    current_generation: dict[tuple[str, str], int] = {}
    raw: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "sha256s": set(),
            "payload_paths": set(),
            "event_count": 0,
            "captured_byte_sizes": set(),
            "buffer_lengths": set(),
        }
    )
    source_line_count = 0
    invalid_json_count = 0
    non_object_count = 0
    payload_event_count = 0
    accepted_payload_event_count = 0
    missing_generation_count = 0
    missing_payload_file_count = 0
    rejected_partial_payload_count = 0

    with capture.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            source_line_count += 1
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError:
                invalid_json_count += 1
                continue
            if not isinstance(row, dict):
                non_object_count += 1
                continue
            event = str(row.get("event") or "")
            if event in {"create_vertex_buffer", "create_index_buffer"}:
                kind = (
                    "vertex_buffer"
                    if event == "create_vertex_buffer"
                    else "index_buffer"
                )
                pointer_key = (
                    "vertex_buffer_ptr"
                    if kind == "vertex_buffer"
                    else "index_buffer_ptr"
                )
                pointer = str(row.get(pointer_key) or "").strip().lower()
                event_index = row.get("event_index")
                if pointer and isinstance(event_index, int):
                    current_generation[(kind, pointer)] = event_index
                continue
            if event != "buffer_payload":
                continue
            payload_event_count += 1
            kind = str(row.get("resource_type_name") or "")
            pointer = str(row.get("buffer_ptr") or "").strip().lower()
            if kind not in {"vertex_buffer", "index_buffer"} or not pointer:
                continue
            generation = current_generation.get((kind, pointer))
            if generation is None:
                missing_generation_count += 1
                continue
            try:
                offset = int(row.get("offset"))
                buffer_length = int(row.get("buffer_length"))
                captured_size = int(row.get("captured_byte_size"))
            except (TypeError, ValueError):
                rejected_partial_payload_count += 1
                continue
            if (
                row.get("snapshot_status") != "captured"
                or offset != 0
                or buffer_length <= 0
                or captured_size != buffer_length
            ):
                rejected_partial_payload_count += 1
                continue
            payload_file = next(
                (
                    candidate
                    for candidate in _payload_path_candidates(
                        row.get("payload_path"),
                        capture_path=capture,
                        payload_root=root,
                    )
                    if candidate.is_file()
                ),
                None,
            )
            if payload_file is None:
                missing_payload_file_count += 1
                continue
            payload = payload_file.read_bytes()
            if len(payload) != captured_size:
                rejected_partial_payload_count += 1
                continue
            digest = _sha256_bytes(payload)
            key = _buffer_generation_key(kind, pointer, generation)
            target = raw[key]
            target["sha256s"].add(digest)
            target["payload_paths"].add(str(payload_file))
            target["event_count"] += 1
            target["captured_byte_sizes"].add(captured_size)
            target["buffer_lengths"].add(buffer_length)
            accepted_payload_event_count += 1

    buffers: dict[str, dict[str, Any]] = {}
    stable_count = 0
    unstable_count = 0
    for key, source in raw.items():
        hashes = sorted(source["sha256s"])
        status = "stable" if len(hashes) == 1 else "unstable"
        if status == "stable":
            stable_count += 1
        else:
            unstable_count += 1
        kind, pointer, generation_text = key.split("|", 2)
        buffers[key] = {
            "status": status,
            "resource_type_name": kind,
            "buffer_ptr": pointer,
            "creation_event_index": int(generation_text),
            "sha256": hashes[0] if len(hashes) == 1 else None,
            "sha256s": hashes,
            "event_count": int(source["event_count"]),
            "payload_paths": sorted(source["payload_paths"]),
            "captured_byte_sizes": sorted(source["captured_byte_sizes"]),
            "buffer_lengths": sorted(source["buffer_lengths"]),
        }

    return {
        "summary": {
            "source_line_count": source_line_count,
            "invalid_json_count": invalid_json_count,
            "non_object_count": non_object_count,
            "buffer_payload_event_count": payload_event_count,
            "accepted_full_payload_event_count": accepted_payload_event_count,
            "stable_buffer_generation_count": stable_count,
            "unstable_buffer_generation_count": unstable_count,
            "missing_generation_payload_event_count": missing_generation_count,
            "missing_payload_file_count": missing_payload_file_count,
            "rejected_partial_payload_event_count": rejected_partial_payload_count,
        },
        "buffers": buffers,
    }


def _runtime_payload_pair(
    identity: Mapping[str, Any],
    runtime_inventory: Mapping[str, Any],
) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    buffers = runtime_inventory.get("buffers")
    if not isinstance(buffers, Mapping):
        return "runtime-payload-missing", None, None
    try:
        vb_ptr = str(identity.get("stream0_vertex_buffer_ptr") or "").lower()
        vb_generation = int(
            identity.get("stream0_vertex_buffer_creation_event_index")
        )
        ib_ptr = str(identity.get("index_buffer_ptr") or "").lower()
        ib_generation = int(identity.get("index_buffer_creation_event_index"))
    except (TypeError, ValueError):
        return "runtime-payload-missing", None, None
    if not vb_ptr or not ib_ptr:
        return "runtime-payload-missing", None, None
    vb = buffers.get(
        _buffer_generation_key("vertex_buffer", vb_ptr, vb_generation)
    )
    ib = buffers.get(
        _buffer_generation_key("index_buffer", ib_ptr, ib_generation)
    )
    if not isinstance(vb, Mapping) or not isinstance(ib, Mapping):
        return (
            "runtime-payload-missing",
            dict(vb) if isinstance(vb, Mapping) else None,
            dict(ib) if isinstance(ib, Mapping) else None,
        )
    if vb.get("status") != "stable" or ib.get("status") != "stable":
        return "runtime-payload-unstable", dict(vb), dict(ib)
    if not _valid_sha(vb.get("sha256")) or not _valid_sha(ib.get("sha256")):
        return "runtime-payload-missing", dict(vb), dict(ib)
    return "ready", dict(vb), dict(ib)


def _candidate_static_payload(
    group: Mapping[str, Any],
    static_inventory: Mapping[str, Any],
) -> dict[str, Any] | None:
    by_sha = static_inventory.get("by_imb_sha256")
    if not isinstance(by_sha, Mapping):
        return None
    imb_sha = _valid_sha(group.get("imb_sha256"))
    if not imb_sha:
        return None
    source = by_sha.get(imb_sha)
    if not isinstance(source, Mapping) or source.get("ready") is not True:
        return None
    vertex = source.get("vertex_buffer")
    primitives = source.get("primitives")
    if not isinstance(vertex, Mapping) or not isinstance(primitives, Mapping):
        return None
    try:
        primitive_index = int(group.get("primitive_index"))
    except (TypeError, ValueError):
        return None
    primitive = primitives.get(str(primitive_index))
    if not isinstance(primitive, Mapping):
        return None
    vb_sha = _valid_sha(vertex.get("sha256"))
    ib_sha = _valid_sha(primitive.get("sha256"))
    if not vb_sha or not ib_sha:
        return None

    static_stride = group.get("static_vertex_stride")
    if static_stride is not None:
        try:
            if int(static_stride) != int(vertex.get("stride")):
                return None
        except (TypeError, ValueError):
            return None
    draw_range = group.get("draw_range")
    if isinstance(draw_range, Mapping):
        try:
            if int(draw_range.get("index_count")) != int(
                primitive.get("index_count")
            ):
                return None
            if int(draw_range.get("primitive_count")) != int(
                primitive.get("primitive_count")
            ):
                return None
        except (TypeError, ValueError):
            return None
    return {
        "imb_sha256": imb_sha,
        "primitive_index": primitive_index,
        "vertex_buffer_sha256": vb_sha,
        "vertex_buffer_byte_size": vertex.get("byte_size"),
        "vertex_stride": vertex.get("stride"),
        "vertex_count": vertex.get("vertex_count"),
        "index_buffer_sha256": ib_sha,
        "index_buffer_byte_size": primitive.get("byte_size"),
        "index_count": primitive.get("index_count"),
        "primitive_count": primitive.get("primitive_count"),
        "index_format": primitive.get("index_format"),
    }


def build_runtime_geometry_payload_candidate_join(
    pointer_join: Mapping[str, Any],
    runtime_inventory: Mapping[str, Any],
    static_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    if pointer_join.get("format") != POINTER_JOIN_FORMAT:
        raise ValueError(
            "pointer join must be SHIFT.IMBRuntimeGeometryPointerCandidateJoin/1"
        )

    rows: list[dict[str, Any]] = []
    gate_counts: Counter[str] = Counter()
    candidate_status_counts: Counter[str] = Counter()
    identity_count = 0
    identity_draw_count = 0
    complete_runtime_identity_count = 0
    complete_runtime_identity_draw_count = 0
    reduced_identity_count = 0
    reduced_identity_draw_count = 0
    newly_single_identity_count = 0
    newly_single_identity_draw_count = 0
    payload_conflict_identity_count = 0
    payload_conflict_draw_count = 0
    removed_candidate_count = 0

    for shape in pointer_join.get("resource_shapes") or []:
        if not isinstance(shape, Mapping):
            continue
        identity_rows: list[dict[str, Any]] = []
        resolved_contents: set[str] = set()
        all_single = True

        for identity_row in shape.get("geometry_pointer_identities") or []:
            if not isinstance(identity_row, Mapping):
                continue
            identity_count += 1
            draw_count = int(identity_row.get("draw_count") or 0)
            identity_draw_count += draw_count
            base_groups = [
                dict(group)
                for group in (identity_row.get("candidate_content_groups") or [])
                if isinstance(group, Mapping)
            ]
            base_count = len(base_groups)
            runtime_status, vb_runtime, ib_runtime = _runtime_payload_pair(
                identity_row.get("geometry_pointer_identity") or {},
                runtime_inventory,
            )
            if runtime_status == "ready":
                complete_runtime_identity_count += 1
                complete_runtime_identity_draw_count += draw_count

            static_rows: list[dict[str, Any]] = []
            static_complete = True
            for group in base_groups:
                payload = _candidate_static_payload(group, static_inventory)
                enriched = dict(group)
                enriched["static_geometry_payload"] = payload
                if payload is None:
                    static_complete = False
                static_rows.append(enriched)

            selected = list(static_rows)
            gate_status = (
                "no-base-candidates"
                if not base_groups
                else "already-single"
                if base_count == 1
                else runtime_status
            )
            exact_match_count = 0
            if base_count > 1 and runtime_status == "ready":
                if not static_complete:
                    gate_status = "static-payload-inventory-incomplete"
                else:
                    vb_sha = _valid_sha((vb_runtime or {}).get("sha256"))
                    ib_sha = _valid_sha((ib_runtime or {}).get("sha256"))
                    matches = [
                        group
                        for group in static_rows
                        if isinstance(
                            group.get("static_geometry_payload"), Mapping
                        )
                        and group["static_geometry_payload"].get(
                            "vertex_buffer_sha256"
                        )
                        == vb_sha
                        and group["static_geometry_payload"].get(
                            "index_buffer_sha256"
                        )
                        == ib_sha
                    ]
                    exact_match_count = len(matches)
                    if not matches:
                        gate_status = "exact-payload-no-static-match"
                        payload_conflict_identity_count += 1
                        payload_conflict_draw_count += draw_count
                    elif len(matches) < base_count:
                        selected = matches
                        gate_status = "reduced-by-exact-geometry-payload"
                        reduced_identity_count += 1
                        reduced_identity_draw_count += draw_count
                        removed_candidate_count += base_count - len(matches)
                        if len(matches) == 1:
                            newly_single_identity_count += 1
                            newly_single_identity_draw_count += draw_count
                    else:
                        gate_status = "payload-non-discriminating"
            elif base_count == 1 and runtime_status == "ready" and static_complete:
                payload = static_rows[0].get("static_geometry_payload")
                vb_sha = _valid_sha((vb_runtime or {}).get("sha256"))
                ib_sha = _valid_sha((ib_runtime or {}).get("sha256"))
                if (
                    isinstance(payload, Mapping)
                    and payload.get("vertex_buffer_sha256") == vb_sha
                    and payload.get("index_buffer_sha256") == ib_sha
                ):
                    gate_status = "already-single-payload-confirmed"
                    exact_match_count = 1
                else:
                    gate_status = "already-single-payload-mismatch"
                    payload_conflict_identity_count += 1
                    payload_conflict_draw_count += draw_count

            gate_counts[gate_status] += 1
            if len(selected) == 1:
                candidate_status = "single-content-candidate"
                content_sha = _valid_sha(
                    selected[0].get("content_group_sha256")
                )
                if content_sha:
                    resolved_contents.add(content_sha)
            elif selected:
                candidate_status = "ambiguous-content-candidates"
                all_single = False
            else:
                candidate_status = "no-content-candidates"
                all_single = False
            candidate_status_counts[candidate_status] += 1

            identity_rows.append({
                "geometry_pointer_identity_sha256": identity_row.get(
                    "geometry_pointer_identity_sha256"
                ),
                "geometry_pointer_identity": dict(
                    identity_row.get("geometry_pointer_identity") or {}
                ),
                "draw_count": draw_count,
                "first_frame": identity_row.get("first_frame"),
                "last_frame": identity_row.get("last_frame"),
                "source_candidate_content_group_count": base_count,
                "runtime_payload_status": runtime_status,
                "runtime_vertex_buffer_payload": vb_runtime,
                "runtime_index_buffer_payload": ib_runtime,
                "static_payload_complete_for_all_candidates": static_complete,
                "exact_payload_match_count": exact_match_count,
                "geometry_payload_gate_status": gate_status,
                "candidate_content_status": candidate_status,
                "candidate_content_group_count": len(selected),
                "candidate_content_group_sha256s": sorted({
                    str(group.get("content_group_sha256"))
                    for group in selected
                    if group.get("content_group_sha256")
                }),
                "candidate_content_groups": selected,
            })

        if not identity_rows:
            resource_status = "no-geometry-identities"
        elif all_single:
            resource_status = (
                "single-content-across-geometry-identities"
                if len(resolved_contents) == 1
                else "multiple-single-contents-by-geometry-identity"
            )
        else:
            resource_status = "geometry-identities-still-ambiguous"

        rows.append({
            "resource_shape_sha256": shape.get("resource_shape_sha256"),
            "geometry_shape_sha256": shape.get("geometry_shape_sha256"),
            "pipeline_signature_sha256": shape.get(
                "pipeline_signature_sha256"
            ),
            "families": list(shape.get("families") or []),
            "resource_shape_draw_count": int(
                shape.get("resource_shape_draw_count") or 0
            ),
            "source_candidate_content_status": shape.get(
                "source_candidate_content_status"
            ),
            "source_candidate_content_group_count": shape.get(
                "source_candidate_content_group_count"
            ),
            "geometry_payload_resource_status": resource_status,
            "resolved_content_group_sha256s": sorted(resolved_contents),
            "geometry_pointer_identity_count": len(identity_rows),
            "geometry_pointer_identities": identity_rows,
        })

    rows.sort(
        key=lambda row: (
            -int(row.get("resource_shape_draw_count") or 0),
            str(row.get("resource_shape_sha256") or ""),
        )
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "observed" if rows else "not-observed",
        "summary": {
            "runtime_resource_shape_count": len(rows),
            "runtime_resource_shape_draw_count": sum(
                int(row.get("resource_shape_draw_count") or 0)
                for row in rows
            ),
            "geometry_pointer_identity_count": identity_count,
            "geometry_pointer_identity_draw_count": identity_draw_count,
            "runtime_payload_complete_identity_count": (
                complete_runtime_identity_count
            ),
            "runtime_payload_complete_identity_draw_count": (
                complete_runtime_identity_draw_count
            ),
            "payload_reduced_identity_count": reduced_identity_count,
            "payload_reduced_identity_draw_count": reduced_identity_draw_count,
            "newly_single_payload_identity_count": newly_single_identity_count,
            "newly_single_payload_identity_draw_count": (
                newly_single_identity_draw_count
            ),
            "payload_conflict_identity_count": payload_conflict_identity_count,
            "payload_conflict_draw_count": payload_conflict_draw_count,
            "removed_candidate_count": removed_candidate_count,
            "geometry_payload_gate_status_counts": dict(
                sorted(gate_counts.items())
            ),
            "candidate_status_counts": dict(
                sorted(candidate_status_counts.items())
            ),
        },
        "runtime_payload_capture_summary": dict(
            runtime_inventory.get("summary") or {}
        ),
        "static_payload_inventory_summary": {
            key: static_inventory.get(key)
            for key in (
                "candidate_imb_sha256_count",
                "found_imb_sha256_count",
                "ready_imb_sha256_count",
                "missing_imb_sha256s",
                "path_digest_mismatches",
            )
        },
        "resource_shapes": rows,
        "boundary": {
            "candidate_only": True,
            "exact_geometry_payload_equality": (
                "full stream-0 runtime-interleaved VB bytes plus per-primitive "
                "little-endian u16 IB bytes"
            ),
            "runtime_payload_generation": (
                "capture-local COM pointer + creation event index; only stable "
                "full-buffer captured snapshots are used"
            ),
            "static_vertex_payload": (
                "reconstructed from source IMB planar stream bytes using the "
                "source-backed runtime element offsets/stride; uncovered or "
                "overlapping stride bytes are rejected"
            ),
            "failure_policy": (
                "missing, unstable, incomplete, or zero-match payload evidence "
                "never removes existing static candidates"
            ),
            "resource_path_identity": False,
            "material_identity": False,
            "scene_instance_identity": False,
            "render_admission": False,
            "required_for_promotion": (
                "exact runtime logical resource identity and existing Phase 572 "
                "same-instance/shader admission gates remain independent"
            ),
        },
    }


def validate_files(
    pointer_join_path: str | Path,
    capture_path: str | Path,
    corpus_inputs: Iterable[str | Path],
    *,
    payload_root: str | Path | None = None,
) -> dict[str, Any]:
    pointer_path = resolve_input_path(pointer_join_path)
    pointer_join = json.loads(pointer_path.read_text(encoding="utf-8"))
    if not isinstance(pointer_join, Mapping):
        raise ValueError("pointer join input must be a JSON object")
    if pointer_join.get("format") != POINTER_JOIN_FORMAT:
        raise ValueError(
            "pointer join must be SHIFT.IMBRuntimeGeometryPointerCandidateJoin/1"
        )
    runtime_inventory = collect_runtime_buffer_payloads(
        capture_path,
        payload_root=payload_root,
    )
    static_inventory = build_static_payload_inventory(
        pointer_join,
        corpus_inputs,
    )
    return build_runtime_geometry_payload_candidate_join(
        pointer_join,
        runtime_inventory,
        static_inventory,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("geometry_pointer_join")
    parser.add_argument("capture_jsonl")
    parser.add_argument("output")
    parser.add_argument(
        "--corpus",
        action="append",
        required=True,
        help="Silverstone .zip or .bff corpus input; may be repeated",
    )
    parser.add_argument(
        "--payload-root",
        help=(
            "optional directory containing buffer payload files; relative and "
            "Windows capture paths also fall back to capture-dir/buffers"
        ),
    )
    args = parser.parse_args(argv)

    result = validate_files(
        args.geometry_pointer_join,
        args.capture_jsonl,
        args.corpus,
        payload_root=args.payload_root,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
