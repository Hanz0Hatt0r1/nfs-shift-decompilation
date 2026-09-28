"""Aggregate scalar-reset runtime evidence into one per-frame manifest.

Phase 490 composes the Phase 485 event schema, Phase 486 callsite attribution,
Phase 488 ordering validation and Phase 489 reset→solve counter checks.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from specialized_provider_reset_solve_order_runtime import (
    compare_provider_solve_order,
)
from specialized_provider_scalar_reset_capture_runtime import (
    normalize_scalar_reset_event,
    validate_scalar_reset_events,
)
from specialized_provider_scalar_reset_sequence_runtime import (
    validate_group_event_sequence,
)

FORMAT = "SHIFT.SpecializedProviderResetEvidenceManifestRuntime/1"


def _provider_key(event: Mapping[str, Any]) -> str:
    value = event.get("provider_id")
    if value is None:
        return str(event.get("backend", "unknown"))
    return str(int(value))


def build_frame_manifest(
    events: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[Any, list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        frame = event.get("frame_index")
        grouped[frame].append(event)

    manifests: list[dict[str, Any]] = []
    for frame, frame_events in sorted(
        grouped.items(),
        key=lambda item: (-1 if item[0] is None else int(item[0])),
    ):
        normalized = [
            normalize_scalar_reset_event(event)
            for event in frame_events
        ]
        groups = Counter()
        providers = Counter()
        selectors: list[int] = []
        call_indices: list[int] = []

        for event in normalized:
            selectors.append(int(event["selector"]))
            call_indices.append(int(event["call_index"]))

            callsite = event.get("callsite") or {}
            group = callsite.get("group")
            if group is not None:
                groups[str(group)] += 1

            providers[_provider_key(event)] += 1

        manifests.append(
            {
                "frame_index": frame,
                "event_count": len(normalized),
                "providers": dict(sorted(providers.items())),
                "group_counts": dict(sorted(groups.items())),
                "selectors": selectors,
                "call_indices": call_indices,
                "selector_min": min(selectors, default=None),
                "selector_max": max(selectors, default=None),
            }
        )

    return manifests


def build_reset_evidence_manifest(
    events: Sequence[Mapping[str, Any]],
    *,
    provider_captures: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    event_validation = validate_scalar_reset_events(events)
    sequence_validation = validate_group_event_sequence(events)
    frame_manifest = build_frame_manifest(events)

    solve_reports = [
        compare_provider_solve_order(
            capture,
            events,
        )
        for capture in provider_captures
    ]

    errors = (
        list(event_validation.get("errors") or [])
        + list(sequence_validation.get("errors") or [])
        + [
            f"solve-{index}:{error}"
            for index, report in enumerate(solve_reports)
            for error in report.get("errors") or []
        ]
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not errors else "blocked",
        "ready": not errors,
        "event_count": len(events),
        "frame_count": len(frame_manifest),
        "frames": frame_manifest,
        "event_validation": event_validation,
        "sequence_validation": sequence_validation,
        "provider_solve_order": solve_reports,
        "errors": list(dict.fromkeys(errors)),
    }


def summarize_reset_evidence_manifest(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    providers = Counter()
    groups = Counter()

    for frame in report.get("frames") or []:
        providers.update(frame.get("providers") or {})
        groups.update(frame.get("group_counts") or {})

    return {
        "format": "SHIFT.SpecializedProviderResetEvidenceManifestSummary/1",
        "version": 1,
        "event_count": int(report.get("event_count", 0)),
        "frame_count": int(report.get("frame_count", 0)),
        "provider_event_counts": dict(sorted(providers.items())),
        "group_event_counts": dict(sorted(groups.items())),
        "provider_solve_checks": len(
            report.get("provider_solve_order") or []
        ),
        "provider_solve_ready": sum(
            bool(item.get("ready"))
            for item in report.get("provider_solve_order") or []
        ),
        "ready": bool(report.get("ready")),
    }


def build_reset_evidence_contract(
    events: Sequence[Mapping[str, Any]],
    *,
    provider_captures: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    report = build_reset_evidence_manifest(
        events,
        provider_captures=provider_captures,
    )
    report["summary"] = summarize_reset_evidence_manifest(report)
    return report


__all__ = [
    "FORMAT",
    "build_frame_manifest",
    "build_reset_evidence_manifest",
    "summarize_reset_evidence_manifest",
    "build_reset_evidence_contract",
]
