"""Offline correlation for Phase 635/636 relation-state mutation captures.

The correlator consumes only already-recorded runtime_event_sequence values and
capture metadata. It does not infer scheduler semantics or mutate runtime state.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

FORMAT = "SHIFT.ConstraintRelationStateMutationTimelineCorrelation/1"
MUTATION_FORMAT = "SHIFT.ConstraintRelationStateMutationCaptureRuntime/1"

_JSON_ANCHOR_PATTERNS = (
    ("frame-entry", "frame_entry_*.json"),
    ("builtin-solver-entry", "pre_solve_*.json"),
    ("provider-solver-entry", "provider_pre_*_*.json"),
    ("provider-solver-return", "provider_post_*_*.json"),
    ("post-solve", "post_solve_*.json"),
)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _event_sequence(row: Mapping[str, Any]) -> int | None:
    direct = _as_int(row.get("runtime_event_sequence"))
    if direct is not None:
        return direct
    metadata = row.get("metadata")
    if isinstance(metadata, Mapping):
        return _as_int(metadata.get("runtime_event_sequence"))
    return None


def _frame_index(row: Mapping[str, Any]) -> int | None:
    direct = _as_int(row.get("frame_index"))
    if direct is not None:
        return direct
    metadata = row.get("metadata")
    if isinstance(metadata, Mapping):
        return _as_int(metadata.get("frame_index"))
    return None


def _read_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("top-level JSON value must be an object")
    return payload


def _read_jsonl(path: Path) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, Mapping):
            raise ValueError(
                f"line {line_number}: top-level JSON value must be an object"
            )
        rows.append(payload)
    return rows


def _normalize_anchor(
    *,
    kind: str,
    row: Mapping[str, Any],
    source: str,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "runtime_event_sequence": _event_sequence(row),
        "frame_index": _frame_index(row),
        "source": source,
    }


def _load_capture_directory(
    capture_directory: Path,
) -> tuple[list[Mapping[str, Any]], list[dict[str, Any]], list[str]]:
    root = Path(capture_directory)
    errors: list[str] = []
    mutations: list[Mapping[str, Any]] = []
    anchors: list[dict[str, Any]] = []

    mutation_path = root / "relation_state_mutation_events.jsonl"
    if not mutation_path.is_file():
        errors.append("missing-relation-state-mutation-events")
    else:
        try:
            mutations = _read_jsonl(mutation_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(
                f"invalid-relation-state-mutation-events:{exc}"
            )

    for kind, pattern in _JSON_ANCHOR_PATTERNS:
        for path in sorted(root.glob(pattern)):
            try:
                row = _read_json(path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"invalid-anchor:{path.name}:{exc}")
                continue
            anchors.append(
                _normalize_anchor(
                    kind=kind,
                    row=row,
                    source=path.name,
                )
            )

    reset_path = root / "scalar_reset_events.jsonl"
    if reset_path.is_file():
        try:
            reset_rows = _read_jsonl(reset_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"invalid-scalar-reset-events:{exc}")
        else:
            for index, row in enumerate(reset_rows, 1):
                anchors.append(
                    _normalize_anchor(
                        kind="scalar-reset",
                        row=row,
                        source=f"{reset_path.name}:{index}",
                    )
                )

    return mutations, anchors, errors


def _validate_anchor_rows(
    anchors: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    normalized: list[dict[str, Any]] = []
    errors: list[str] = []

    for index, anchor in enumerate(anchors):
        sequence = _as_int(anchor.get("runtime_event_sequence"))
        kind = anchor.get("kind")
        source = anchor.get("source", f"anchor:{index}")
        if not isinstance(kind, str) or not kind:
            errors.append(f"anchor-kind-invalid:{source}")
            continue
        if sequence is None or sequence <= 0:
            errors.append(f"anchor-sequence-invalid:{source}")
            continue
        normalized.append(
            {
                "kind": kind,
                "runtime_event_sequence": sequence,
                "frame_index": _as_int(anchor.get("frame_index")),
                "source": str(source),
            }
        )

    normalized.sort(key=lambda row: row["runtime_event_sequence"])
    return normalized, errors


def _anchor_view(anchor: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if anchor is None:
        return None
    return {
        "kind": anchor["kind"],
        "runtime_event_sequence": anchor["runtime_event_sequence"],
        "frame_index": anchor.get("frame_index"),
        "source": anchor.get("source"),
    }


def _nearest_anchors(
    anchors: Sequence[Mapping[str, Any]],
    sequence: int,
) -> tuple[Mapping[str, Any] | None, Mapping[str, Any] | None]:
    previous = None
    following = None
    for anchor in anchors:
        anchor_sequence = int(anchor["runtime_event_sequence"])
        if anchor_sequence < sequence:
            previous = anchor
            continue
        if anchor_sequence > sequence:
            following = anchor
            break
    return previous, following


def correlate_relation_state_mutation_events(
    mutations: Sequence[Mapping[str, Any]],
    anchors: Sequence[Mapping[str, Any]],
    *,
    loader_errors: Sequence[str] = (),
) -> dict[str, Any]:
    """Correlate mutation events with captured timeline anchors, fail closed."""
    normalized_anchors, anchor_errors = _validate_anchor_rows(anchors)
    errors = list(loader_errors) + anchor_errors

    if not mutations:
        errors.append("no-relation-state-mutation-events")
    if not normalized_anchors:
        errors.append("no-runtime-timeline-anchors")

    frame_entries: dict[int, dict[str, Any]] = {}
    for anchor in normalized_anchors:
        if anchor["kind"] != "frame-entry":
            continue
        frame_index = anchor.get("frame_index")
        if frame_index is None:
            errors.append(f"frame-entry-index-missing:{anchor['source']}")
            continue
        if frame_index in frame_entries:
            errors.append(f"duplicate-frame-entry-index:{frame_index}")
            continue
        frame_entries[frame_index] = anchor

    seen_sequences: dict[int, str] = {}
    for anchor in normalized_anchors:
        sequence = int(anchor["runtime_event_sequence"])
        prior = seen_sequences.get(sequence)
        if prior is not None:
            errors.append(
                f"duplicate-runtime-event-sequence:{sequence}:{prior}:{anchor['source']}"
            )
        else:
            seen_sequences[sequence] = str(anchor["source"])

    first_frame_entry = (
        min(
            (
                anchor
                for anchor in normalized_anchors
                if anchor["kind"] == "frame-entry"
            ),
            key=lambda row: row["runtime_event_sequence"],
            default=None,
        )
    )

    correlated: list[dict[str, Any]] = []
    setup_count = 0
    runtime_count = 0
    unclassified_count = 0

    for index, mutation in enumerate(mutations, 1):
        event_errors: list[str] = []
        sequence = _as_int(mutation.get("runtime_event_sequence"))
        frame_index = _as_int(mutation.get("frame_index"))
        frame_sequence = _as_int(
            mutation.get("frame_entry_runtime_event_sequence")
        )
        component_slot = _as_int(mutation.get("component_slot"))
        callsite = mutation.get("caller_classification")
        callsite_map = callsite if isinstance(callsite, Mapping) else {}
        callsite_ready = (
            mutation.get("callsite_ready") is True
            and callsite_map.get("ready") is True
            and callsite_map.get("known_callsite") is True
        )
        callsite_kind = callsite_map.get("kind")
        source_function = callsite_map.get("source_function")

        if mutation.get("format") != MUTATION_FORMAT:
            event_errors.append("mutation-format-invalid")
        if sequence is None or sequence <= 0:
            event_errors.append("mutation-sequence-invalid")
        if component_slot is None or not 0 <= component_slot < 4:
            event_errors.append("mutation-component-slot-invalid")
        if not callsite_ready:
            event_errors.append("mutation-callsite-not-ready")

        if callsite_kind == "vehicle-setup-slot":
            setup_count += 1
        elif callsite_kind == "runtime-threshold-slot":
            runtime_count += 1
        else:
            unclassified_count += 1

        if sequence is not None and sequence > 0:
            prior = seen_sequences.get(sequence)
            if prior is not None:
                event_errors.append(
                    f"duplicate-runtime-event-sequence:{sequence}:{prior}"
                )
            else:
                seen_sequences[sequence] = f"mutation:{index}"

        matching_frame = None
        if frame_index is None:
            if frame_sequence is not None:
                event_errors.append(
                    "mutation-frame-sequence-without-frame-index"
                )
        else:
            matching_frame = frame_entries.get(frame_index)
            if matching_frame is None:
                event_errors.append(
                    f"mutation-frame-entry-missing:{frame_index}"
                )
            else:
                expected_sequence = int(
                    matching_frame["runtime_event_sequence"]
                )
                if frame_sequence != expected_sequence:
                    event_errors.append(
                        "mutation-frame-entry-sequence-mismatch"
                    )
                if sequence is not None and sequence <= expected_sequence:
                    event_errors.append(
                        "mutation-not-after-frame-entry"
                    )

        previous = None
        following = None
        timeline_position = "unknown"
        if sequence is not None and sequence > 0 and normalized_anchors:
            previous, following = _nearest_anchors(
                normalized_anchors,
                sequence,
            )
            if frame_index is None:
                if (
                    first_frame_entry is not None
                    and sequence
                    < int(first_frame_entry["runtime_event_sequence"])
                ):
                    timeline_position = "before-first-frame-entry"
                else:
                    timeline_position = "unanchored-to-frame"
                    event_errors.append(
                        "mutation-without-frame-anchor-after-frame-start"
                    )
            else:
                timeline_position = "after-frame-entry"

        if previous is None and following is None:
            event_errors.append("mutation-has-no-timeline-neighbor")

        anchor_window = (
            f"{previous['kind'] if previous is not None else 'capture-start'}"
            "->"
            f"{following['kind'] if following is not None else 'capture-end'}"
        )

        correlated.append(
            {
                "event_index": index,
                "ready": not event_errors,
                "errors": event_errors,
                "runtime_event_sequence": sequence,
                "component_slot": component_slot,
                "component_slot_name": mutation.get(
                    "component_slot_name"
                ),
                "source_branch": mutation.get("source_branch"),
                "caller_kind": callsite_kind,
                "caller_source_function": source_function,
                "caller_return_address": mutation.get(
                    "caller_return_address"
                ),
                "frame_index": frame_index,
                "frame_entry_runtime_event_sequence": frame_sequence,
                "frame_anchor_consistent": (
                    frame_index is None
                    or (
                        matching_frame is not None
                        and frame_sequence
                        == matching_frame["runtime_event_sequence"]
                    )
                ),
                "timeline_position": timeline_position,
                "previous_anchor": _anchor_view(previous),
                "next_anchor": _anchor_view(following),
                "anchor_window": anchor_window,
            }
        )
        errors.extend(
            f"mutation:{index}:{error}"
            for error in event_errors
        )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not errors else "blocked",
        "ready": not errors,
        "errors": errors,
        "mutation_event_count": len(mutations),
        "timeline_anchor_count": len(normalized_anchors),
        "frame_entry_count": len(frame_entries),
        "summary": {
            "vehicle_setup_mutation_count": setup_count,
            "runtime_threshold_mutation_count": runtime_count,
            "unclassified_mutation_count": unclassified_count,
            "correlated_ready_count": sum(
                1 for event in correlated if event["ready"]
            ),
        },
        "events": correlated,
        "evidence_boundary": {
            "static_callsite_classification_required": True,
            "runtime_event_sequence_only": True,
            "native_scheduler_admission": False,
            "semantic_event_inference": False,
        },
    }


def analyze_relation_state_mutation_capture_directory(
    capture_directory: Path,
) -> dict[str, Any]:
    mutations, anchors, loader_errors = _load_capture_directory(
        Path(capture_directory)
    )
    report = correlate_relation_state_mutation_events(
        mutations,
        anchors,
        loader_errors=loader_errors,
    )
    report["capture_directory"] = str(Path(capture_directory))
    return report


__all__ = [
    "FORMAT",
    "MUTATION_FORMAT",
    "correlate_relation_state_mutation_events",
    "analyze_relation_state_mutation_capture_directory",
]
