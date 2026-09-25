"""Preflight an external BMW M3 D3D9 runtime report before shader execution."""
from __future__ import annotations

from typing import Any, Mapping

from bmw_runtime_shader_join import _runtime_draw_states

FORMAT = "SHIFT.BMWRuntimeCapturePreflight/1"
TARGET_MEB = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
PAINT_RANGES = (
    {"primitive_index": 1, "first_index": 150, "index_count": 6294},
    {"primitive_index": 2, "first_index": 6444, "index_count": 7386},
)


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _same_resource(
    binding: Mapping[str, Any],
    expected_resource_sha: str | None,
    expected_resource_path: str,
) -> bool:
    actual_sha = binding.get("resource_sha256")
    if expected_resource_sha and actual_sha:
        return str(actual_sha) == str(expected_resource_sha)
    actual_path = binding.get("resource_path")
    return bool(actual_path and _norm(actual_path) == _norm(expected_resource_path))


def _draw_rows(
    frame: Mapping[str, Any],
    state: Mapping[str, Any],
    source: str,
) -> list[tuple[int | None, Mapping[str, Any]]]:
    if source == "draw-snapshot":
        draw = state.get("draw")
        return [(state.get("draw_index"), draw)] if isinstance(draw, Mapping) else []
    return [
        (index, draw)
        for index, draw in enumerate(state.get("draws") or [])
        if isinstance(draw, Mapping)
    ]


def _candidate_completeness(state: Mapping[str, Any]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    binding = state.get("vertex_declaration") or {}
    if not binding.get("declaration_ptr"):
        missing.append("vertex-declaration")
    for key in ("vertex_shader", "pixel_shader"):
        if not (state.get(key) or {}).get("shader_ptr"):
            missing.append(key)
    if not (state.get("active_stream_sources") or state.get("stream_sources")):
        missing.append("streams")
    if not state.get("index_binding"):
        missing.append("indices")
    return not missing, missing


def preflight_bmw_runtime(
    runtime_report: Mapping[str, Any],
    *,
    expected_resource_sha: str | None = None,
    expected_resource_path: str = TARGET_MEB,
) -> dict[str, Any]:
    if runtime_report.get("format") != "SHIFT.D3D9RuntimeBindingEvidence/1":
        raise ValueError("input is not SHIFT.D3D9RuntimeBindingEvidence/1")

    resource_draws: list[dict[str, Any]] = []
    paint_draws: list[dict[str, Any]] = []

    for frame, state, source in _runtime_draw_states(runtime_report):
        binding = state.get("vertex_declaration") or {}
        same_resource = _same_resource(
            binding,
            expected_resource_sha,
            expected_resource_path,
        )
        for draw_index, draw in _draw_rows(frame, state, source):
            try:
                start_index = int(draw.get("start_index"))
                primitive_count = int(draw.get("primitive_count"))
            except (TypeError, ValueError):
                continue
            complete, missing_components = _candidate_completeness(state)
            row = {
                "frame": frame.get("frame"),
                "draw_index": draw_index,
                "source": source,
                "start_index": start_index,
                "primitive_count": primitive_count,
                "same_target_resource": same_resource,
                "shader_identity": (
                    (state.get("shader_permutation_identity") or {}).get("identity_sha256")
                ),
                "state_complete": complete,
                "missing_components": missing_components,
            }
            if same_resource:
                resource_draws.append(row)
                index_count = primitive_count * 3
                for paint_range in PAINT_RANGES:
                    if (
                        start_index == paint_range["first_index"]
                        and index_count == paint_range["index_count"]
                    ):
                        paint_draws.append(
                            {
                                **row,
                                "primitive_index": paint_range["primitive_index"],
                                "index_count": index_count,
                            }
                        )

    same_instance = runtime_report.get("same_instance_gate") or {}
    integrity = runtime_report.get("integrity") or {}
    proven_draws = {
        (candidate.get("frame"), candidate.get("draw_index"))
        for candidate in (same_instance.get("candidate_frames") or [])
    }
    proven_paint_draws = [
        candidate
        for candidate in paint_draws
        if (candidate.get("frame"), candidate.get("draw_index")) in proven_draws
    ]
    ready = bool(
        integrity.get("status") == "observed"
        and same_instance.get("ready") is True
        and proven_paint_draws
    )
    return {
        "format": FORMAT,
        "status": "ready" if ready else ("partial" if resource_draws else "not-found"),
        "ready": ready,
        "target": {
            "resource": expected_resource_path,
            "resource_sha256": expected_resource_sha,
            "paint_ranges": [dict(row) for row in PAINT_RANGES],
        },
        "runtime": {
            "status": runtime_report.get("status"),
            "integrity_status": integrity.get("status"),
            "same_instance_status": same_instance.get("status"),
            "same_instance_ready": same_instance.get("ready") is True,
        },
        "resource_draw_candidates": resource_draws,
        "paint_draw_candidates": paint_draws,
        "proven_paint_draw_candidates": proven_paint_draws,
        "blocking_reasons": (
            []
            if ready
            else list(
                dict.fromkeys(
                    (
                        ["runtime:integrity-not-proven"]
                        if integrity.get("status") != "observed"
                        else []
                    )
                    + (
                        ["runtime:same-instance-not-proven"]
                        if same_instance.get("ready") is not True
                        else []
                    )
                    + (
                        ["runtime:target-paint-draw-not-observed"]
                        if not paint_draws
                        else []
                    )
                    + (
                        ["runtime:target-paint-draw-not-same-instance"]
                        if paint_draws and not proven_paint_draws
                        else []
                    )
                )
            )
        ),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Preflight an external BMW M3 D3D9 runtime capture"
    )
    parser.add_argument("runtime_report")
    parser.add_argument("output")
    parser.add_argument("--resource-sha256")
    parser.add_argument("--resource-path", default=TARGET_MEB)
    args = parser.parse_args(argv)

    report = preflight_bmw_runtime(
        json.loads(__import__("pathlib").Path(args.runtime_report).read_text(encoding="utf-8")),
        expected_resource_sha=args.resource_sha256,
        expected_resource_path=args.resource_path,
    )
    __import__("pathlib").Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "format": report["format"],
                "status": report["status"],
                "ready": report["ready"],
                "blocking_reasons": report["blocking_reasons"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
