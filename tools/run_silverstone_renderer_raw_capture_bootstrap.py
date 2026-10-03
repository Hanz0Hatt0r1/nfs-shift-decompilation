#!/usr/bin/env python3
"""Build exact Silverstone renderer compact inputs from an existing raw D3D9 capture.

This stage never launches the game. It derives the D3D9 Usage ordinal map from
static PE evidence, then reuses one parsed historical JSONL event stream for the
draw-local target evidence and the existing Phase 573 runtime attribution
pipeline. Missing evidence remains a blocker rather than an inferred mapping.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.is_dir():
    paths = [SRC]
    paths.extend(
        sorted(
            (path for path in SRC.rglob("*") if path.is_dir()),
            key=lambda path: (len(path.parts), str(path)),
        )
    )
    for path in reversed(paths):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from d3d9_runtime_trace import load_events
from d3d9_target_draw_local_evidence import build_target_draw_local_evidence
from d3d9_usage_map import build_d3d9_usage_map
from imb_runtime_capture_pipeline import build_imb_runtime_capture_pipeline

FORMAT = "SHIFT.SilverstoneRendererRawCaptureBootstrap/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"
PE_FORMAT = "SHIFT.PEImageEvidence/1"
OUTPUT_NAMES = {
    "usage_map": "d3d9_usage_map.json",
    "draw_local": "d3d9_target_draw_local_evidence.json",
    "capture_pipeline": "silverstone_imb_runtime_capture_pipeline.json",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> str:
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        temp = Path(stream.name)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)
    return hashlib.sha256(payload).hexdigest()


def _load_json_input(path: Path, expected_format: str) -> tuple[dict[str, Any], Mapping[str, Any] | None, list[str]]:
    record = {
        "path": str(path),
        "expected_format": expected_format,
        "present": path.is_file(),
        "size": path.stat().st_size if path.is_file() else None,
        "sha256": _sha256_file(path) if path.is_file() else None,
        "format": None,
    }
    blockers: list[str] = []
    if not path.is_file():
        blockers.append("file-not-found")
        return record, None, blockers
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        blockers.append(f"json-read-failed:{type(exc).__name__}:{exc}")
        return record, None, blockers
    if not isinstance(value, Mapping):
        blockers.append("json-root-not-object")
        return record, None, blockers
    record["format"] = value.get("format")
    if value.get("format") != expected_format:
        blockers.append(f"format-mismatch:{value.get('format')!r}")
        return record, None, blockers
    return record, value, blockers


def _capture_input(path: Path) -> tuple[dict[str, Any], list[str]]:
    record = {
        "path": str(path),
        "present": path.is_file(),
        "size": path.stat().st_size if path.is_file() else None,
        "sha256": _sha256_file(path) if path.is_file() else None,
    }
    blockers = [] if path.is_file() else ["file-not-found"]
    return record, blockers


def _stage(name: str, output: Path) -> dict[str, Any]:
    return {
        "name": name,
        "status": "pending",
        "output": str(output),
        "format": None,
        "sha256": None,
        "summary": None,
        "blocking_reasons": [],
    }


def _complete_stage(row: dict[str, Any], output: Path, report: Mapping[str, Any]) -> None:
    row["status"] = "completed"
    row["format"] = report.get("format")
    row["sha256"] = _write_json_atomic(output, report)
    summary = report.get("summary")
    if isinstance(summary, Mapping):
        row["summary"] = dict(summary)


def run_raw_capture_bootstrap(
    *,
    capture_jsonl: str | Path,
    pe_evidence: str | Path,
    runtime_shader_targets: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    capture_path = Path(capture_jsonl).expanduser()
    pe_path = Path(pe_evidence).expanduser()
    targets_path = Path(runtime_shader_targets).expanduser()

    capture_record, capture_blockers = _capture_input(capture_path)
    pe_record, pe_value, pe_blockers = _load_json_input(pe_path, PE_FORMAT)
    target_record, target_value, target_blockers = _load_json_input(
        targets_path, TARGET_FORMAT
    )
    blockers = [
        *(f"input:capture:{reason}" for reason in capture_blockers),
        *(f"input:pe_evidence:{reason}" for reason in pe_blockers),
        *(f"input:runtime_shader_targets:{reason}" for reason in target_blockers),
    ]

    stages = {
        name: _stage(name, out / OUTPUT_NAMES[name])
        for name in ("usage_map", "draw_local", "capture_pipeline")
    }
    usage_report: Mapping[str, Any] | None = None
    draw_report: Mapping[str, Any] | None = None
    pipeline_report: Mapping[str, Any] | None = None

    if pe_value is None:
        stages["usage_map"].update(
            status="blocked-missing-input",
            blocking_reasons=["pe-evidence-unavailable"],
        )
    else:
        try:
            usage_report = build_d3d9_usage_map(pe_value)
            _complete_stage(
                stages["usage_map"], out / OUTPUT_NAMES["usage_map"], usage_report
            )
            if usage_report.get("ready") is not True:
                reasons = list(usage_report.get("blocking_reasons") or [])
                blockers.extend(f"usage_map:{reason}" for reason in reasons)
        except Exception as exc:
            stages["usage_map"].update(
                status="blocked-error",
                blocking_reasons=[f"{type(exc).__name__}:{exc}"],
            )
            blockers.extend(
                f"usage_map:{reason}"
                for reason in stages["usage_map"]["blocking_reasons"]
            )

    events: list[Mapping[str, Any]] | None = None
    if capture_record["present"] and target_value is not None:
        try:
            events = [
                dict(row)
                for row in load_events(capture_path, skip_unsupported=True)
                if isinstance(row, Mapping)
            ]
        except Exception as exc:
            reason = f"capture-read-failed:{type(exc).__name__}:{exc}"
            blockers.append(reason)
    else:
        if not capture_record["present"]:
            blockers.append("capture-events:capture-unavailable")
        if target_value is None:
            blockers.append("capture-events:runtime-shader-targets-unavailable")

    if events is None or target_value is None:
        reasons = []
        if events is None:
            reasons.append("capture-events-unavailable")
        if target_value is None:
            reasons.append("runtime-shader-targets-unavailable")
        stages["draw_local"].update(
            status="blocked-missing-input", blocking_reasons=reasons
        )
    else:
        try:
            draw_report = build_target_draw_local_evidence(
                events, target_inventory=target_value
            )
            _complete_stage(
                stages["draw_local"], out / OUTPUT_NAMES["draw_local"], draw_report
            )
        except Exception as exc:
            stages["draw_local"].update(
                status="blocked-error",
                blocking_reasons=[f"{type(exc).__name__}:{exc}"],
            )
            blockers.extend(
                f"draw_local:{reason}"
                for reason in stages["draw_local"]["blocking_reasons"]
            )

    usage_ready = isinstance(usage_report, Mapping) and usage_report.get("ready") is True
    if events is None or target_value is None or not usage_ready:
        reasons = []
        if events is None:
            reasons.append("capture-events-unavailable")
        if target_value is None:
            reasons.append("runtime-shader-targets-unavailable")
        if not usage_ready:
            reasons.append("usage-map-not-ready")
        stages["capture_pipeline"].update(
            status="blocked-missing-input", blocking_reasons=reasons
        )
        blockers.extend(
            f"capture_pipeline:{reason}"
            for reason in reasons
        )
    else:
        try:
            raw_map = usage_report.get("usage_map")
            usage_map = {
                int(key): int(value)
                for key, value in raw_map.items()
            } if isinstance(raw_map, Mapping) else {}
            pipeline_report = build_imb_runtime_capture_pipeline(
                target_value,
                events,
                usage_ordinal_map=usage_map,
            )
            _complete_stage(
                stages["capture_pipeline"],
                out / OUTPUT_NAMES["capture_pipeline"],
                pipeline_report,
            )
            if pipeline_report.get("pipeline_ready") is not True:
                reasons = list(pipeline_report.get("blocking_reasons") or [])
                blockers.extend(
                    f"capture_pipeline:{reason}" for reason in reasons
                )
        except Exception as exc:
            stages["capture_pipeline"].update(
                status="blocked-error",
                blocking_reasons=[f"{type(exc).__name__}:{exc}"],
            )
            blockers.extend(
                f"capture_pipeline:{reason}"
                for reason in stages["capture_pipeline"]["blocking_reasons"]
            )

    unique_blockers = list(dict.fromkeys(blockers))
    completed = sum(row["status"] == "completed" for row in stages.values())
    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": "completed" if completed == 3 and not unique_blockers else "blocked",
        "ready": completed == 3 and not unique_blockers,
        "summary": {
            "completed_stage_count": completed,
            "blocked_stage_count": sum(
                str(row["status"]).startswith("blocked")
                for row in stages.values()
            ),
            "capture_event_count": len(events) if events is not None else None,
            "usage_map_ready": usage_ready,
            "draw_local_available": draw_report is not None,
            "capture_pipeline_available": pipeline_report is not None,
            "capture_pipeline_ready": (
                pipeline_report.get("pipeline_ready") is True
                if isinstance(pipeline_report, Mapping)
                else False
            ),
        },
        "inputs": {
            "capture": capture_record,
            "pe_evidence": pe_record,
            "runtime_shader_targets": target_record,
        },
        "stages": [stages[name] for name in ("usage_map", "draw_local", "capture_pipeline")],
        "outputs": {
            "usage_map": str(out / OUTPUT_NAMES["usage_map"]) if usage_report is not None else None,
            "draw_local": str(out / OUTPUT_NAMES["draw_local"]) if draw_report is not None else None,
            "capture_pipeline": str(out / OUTPUT_NAMES["capture_pipeline"]) if pipeline_report is not None else None,
        },
        "blocking_reasons": unique_blockers,
        "boundary": {
            "usage_map_source": "SHIFT.PEImageEvidence/1:decoded_tables.usage",
            "usage_map_allows_inference": False,
            "raw_capture_reused_for_both_runtime_outputs": True,
            "draw_local_can_survive_usage_map_blocker": True,
            "missing_usage_map_is_declaration_contradiction": False,
            "runtime_attribution_requires_ready_usage_map": True,
            "missing_capture_event_implies_recapture": False,
            "original_game_execution_required": False,
            "new_capture_required": False,
        },
    }
    _write_json_atomic(
        out / "silverstone_renderer_raw_capture_bootstrap.json", manifest
    )
    return manifest


def _default_shader_targets() -> str:
    return str(ROOT / "evidence" / "silverstone_era3_runtime_shader_targets.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_jsonl")
    parser.add_argument("pe_evidence")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--runtime-shader-targets",
        default=_default_shader_targets(),
    )
    args = parser.parse_args(argv)

    manifest = run_raw_capture_bootstrap(
        capture_jsonl=args.capture_jsonl,
        pe_evidence=args.pe_evidence,
        runtime_shader_targets=args.runtime_shader_targets,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "format": manifest["format"],
                "status": manifest["status"],
                "summary": manifest["summary"],
                "blocking_reasons": manifest["blocking_reasons"],
                "outputs": manifest["outputs"],
                "manifest": str(
                    Path(args.output_dir)
                    / "silverstone_renderer_raw_capture_bootstrap.json"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
