#!/usr/bin/env python3
"""Run the existing exact Silverstone renderer evidence stages as one pipeline.

This module adds orchestration only.  It does not rank candidates, infer missing
resource identity, or weaken any Phase 619-626 proof gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.is_dir():
    paths = [SRC]
    paths.extend(sorted(
        (path for path in SRC.rglob("*") if path.is_dir()),
        key=lambda path: (len(path.parts), str(path)),
    ))
    for path in reversed(paths):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from d3d9_renderer_frontier_audit import build_renderer_frontier_audit
from imb_fxo_pair_provenance import build_report as build_fxo_report
from imb_material_constant_candidate_join import build_report as build_material_constant_report
from imb_material_texture_candidate_join import build_report as build_material_texture_report
from imb_repeated_scene_instance_transform_join import build_repeated_scene_instance_transform_join
from imb_runtime_resource_draw_candidate_join import build_runtime_resource_draw_candidate_join
from imb_static_scene_reference_candidate_join import build_report as build_scene_reference_report

FORMAT = "SHIFT.SilverstoneRendererProductionRun/1"
INPUT_FORMATS = {
    "base_audit": "SHIFT.D3D9RendererRequirementAudit/1",
    "ambiguity_audit": "SHIFT.IMBDrawLocalAmbiguityAudit/1",
    "runtime_shader_targets": "SHIFT.IMBRuntimeShaderTargetSet/1",
    "draw_local": "SHIFT.D3D9TargetDrawLocalEvidence/1",
    "capture_pipeline": "SHIFT.IMBRuntimeCapturePipeline/1",
    "object_candidate_join": "SHIFT.SGBRuntimeObjectCandidateJoin/1",
}
OUTPUT_NAMES = {
    "phase619_fxo": "silverstone_fxo_pair_provenance.json",
    "phase620_material_constants": "silverstone_material_constant_candidate_join.json",
    "phase622_material_textures": "silverstone_material_texture_candidate_join.json",
    "phase623_scene_geometry": "silverstone_static_scene_reference_candidate_join.json",
    "phase624_runtime_resource_draw": "silverstone_runtime_resource_draw_candidate_join.json",
    "phase625_repeated_instance": "silverstone_repeated_scene_instance_transform_join.json",
    "phase626_frontier": "silverstone_renderer_frontier_audit.json",
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
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
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


def _input_record(path: Path | None, expected_format: str, *, optional: bool) -> tuple[dict[str, Any], Mapping[str, Any] | None, list[str]]:
    record: dict[str, Any] = {
        "path": str(path) if path is not None else None,
        "expected_format": expected_format,
        "optional": optional,
        "present": False,
        "format": None,
        "sha256": None,
        "size": None,
    }
    blockers: list[str] = []
    if path is None:
        if not optional:
            blockers.append("input-path-not-specified")
        return record, None, blockers
    path = path.expanduser()
    record["path"] = str(path)
    if not path.is_file():
        if not optional:
            blockers.append("file-not-found")
        return record, None, blockers
    record["present"] = True
    record["size"] = path.stat().st_size
    record["sha256"] = _sha256_file(path)
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


def _corpus_records(corpus: list[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    blockers: list[str] = []
    for ordinal, raw in enumerate(corpus):
        path = raw.expanduser()
        row: dict[str, Any] = {
            "ordinal": ordinal,
            "path": str(path),
            "present": path.is_file(),
            "size": path.stat().st_size if path.is_file() else None,
            "sha256": _sha256_file(path) if path.is_file() else None,
        }
        rows.append(row)
        if not path.is_file():
            blockers.append(f"corpus-{ordinal}:file-not-found:{path}")
    if not corpus:
        blockers.append("corpus:no-inputs")
    return rows, blockers


def _stage_row(name: str, phase: int, output: Path | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "phase": phase,
        "status": "pending",
        "output": str(output) if output is not None else None,
        "format": None,
        "sha256": None,
        "summary": None,
        "blocking_reasons": [],
    }


def _execute_stage(
    row: dict[str, Any],
    output_path: Path,
    builder: Callable[[], Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    try:
        report = builder()
        if not isinstance(report, Mapping):
            raise ValueError("stage builder did not return a mapping")
        output_sha = _write_json_atomic(output_path, report)
    except Exception as exc:
        row["status"] = "blocked-error"
        row["blocking_reasons"] = [f"{type(exc).__name__}:{exc}"]
        return None
    row["status"] = "completed"
    row["format"] = report.get("format")
    row["sha256"] = output_sha
    summary = report.get("summary")
    row["summary"] = dict(summary) if isinstance(summary, Mapping) else None
    return report


def run_production(
    *,
    output_dir: str | Path,
    corpus: list[str | Path],
    base_audit: str | Path | None,
    ambiguity_audit: str | Path | None,
    runtime_shader_targets: str | Path | None,
    draw_local: str | Path | None,
    capture_pipeline: str | Path | None,
    object_candidate_join: str | Path | None = None,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    raw_inputs = {
        "base_audit": Path(base_audit) if base_audit is not None else None,
        "ambiguity_audit": Path(ambiguity_audit) if ambiguity_audit is not None else None,
        "runtime_shader_targets": Path(runtime_shader_targets) if runtime_shader_targets is not None else None,
        "draw_local": Path(draw_local) if draw_local is not None else None,
        "capture_pipeline": Path(capture_pipeline) if capture_pipeline is not None else None,
        "object_candidate_join": Path(object_candidate_join) if object_candidate_join is not None else None,
    }
    inputs: dict[str, dict[str, Any]] = {}
    values: dict[str, Mapping[str, Any] | None] = {}
    blockers: list[str] = []
    for name, path in raw_inputs.items():
        optional = name == "object_candidate_join"
        record, value, reasons = _input_record(path, INPUT_FORMATS[name], optional=optional)
        inputs[name] = record
        values[name] = value
        blockers.extend(f"input:{name}:{reason}" for reason in reasons)

    corpus_paths = [Path(value) for value in corpus]
    corpus_rows, corpus_blockers = _corpus_records(corpus_paths)
    blockers.extend(corpus_blockers)
    corpus_ready = bool(corpus_paths) and not corpus_blockers

    stages: dict[str, dict[str, Any]] = {
        name: _stage_row(name, phase, out / OUTPUT_NAMES[name])
        for name, phase in (
            ("phase619_fxo", 619),
            ("phase620_material_constants", 620),
            ("phase622_material_textures", 622),
            ("phase623_scene_geometry", 623),
            ("phase624_runtime_resource_draw", 624),
            ("phase625_repeated_instance", 625),
            ("phase626_frontier", 626),
        )
    }
    reports: dict[str, Mapping[str, Any] | None] = {name: None for name in stages}

    def block_stage(name: str, reasons: list[str]) -> None:
        row = stages[name]
        row["status"] = "blocked-missing-input"
        row["blocking_reasons"] = reasons
        blockers.extend(f"{name}:{reason}" for reason in reasons)

    fxo_reasons = []
    for key in ("runtime_shader_targets", "ambiguity_audit"):
        if values[key] is None:
            fxo_reasons.append(f"{key}-unavailable")
    if not corpus_ready:
        fxo_reasons.append("corpus-unavailable")
    if fxo_reasons:
        block_stage("phase619_fxo", fxo_reasons)
    else:
        reports["phase619_fxo"] = _execute_stage(
            stages["phase619_fxo"], out / OUTPUT_NAMES["phase619_fxo"],
            lambda: build_fxo_report(
                values["runtime_shader_targets"],
                corpus_paths,
                ambiguity=values["ambiguity_audit"],
            ),
        )

    constant_reasons = []
    for key in ("ambiguity_audit", "draw_local"):
        if values[key] is None:
            constant_reasons.append(f"{key}-unavailable")
    if reports["phase619_fxo"] is None:
        constant_reasons.append("phase619-fxo-unavailable")
    if not corpus_ready:
        constant_reasons.append("corpus-unavailable")
    if constant_reasons:
        block_stage("phase620_material_constants", constant_reasons)
    else:
        reports["phase620_material_constants"] = _execute_stage(
            stages["phase620_material_constants"], out / OUTPUT_NAMES["phase620_material_constants"],
            lambda: build_material_constant_report(
                values["ambiguity_audit"],
                values["draw_local"],
                reports["phase619_fxo"],
                corpus_paths,
            ),
        )

    texture_reasons = []
    if values["draw_local"] is None:
        texture_reasons.append("draw_local-unavailable")
    if reports["phase619_fxo"] is None:
        texture_reasons.append("phase619-fxo-unavailable")
    if reports["phase620_material_constants"] is None:
        texture_reasons.append("phase620-material-constants-unavailable")
    if not corpus_ready:
        texture_reasons.append("corpus-unavailable")
    if texture_reasons:
        block_stage("phase622_material_textures", texture_reasons)
    else:
        reports["phase622_material_textures"] = _execute_stage(
            stages["phase622_material_textures"], out / OUTPUT_NAMES["phase622_material_textures"],
            lambda: build_material_texture_report(
                reports["phase620_material_constants"],
                values["draw_local"],
                reports["phase619_fxo"],
                corpus_paths,
            ),
        )

    scene_reasons = []
    if values["ambiguity_audit"] is None:
        scene_reasons.append("ambiguity_audit-unavailable")
    if not corpus_ready:
        scene_reasons.append("corpus-unavailable")
    if scene_reasons:
        block_stage("phase623_scene_geometry", scene_reasons)
    else:
        reports["phase623_scene_geometry"] = _execute_stage(
            stages["phase623_scene_geometry"], out / OUTPUT_NAMES["phase623_scene_geometry"],
            lambda: build_scene_reference_report(values["ambiguity_audit"], corpus_paths),
        )

    runtime_reasons = []
    if reports["phase623_scene_geometry"] is None:
        runtime_reasons.append("phase623-scene-geometry-unavailable")
    if values["capture_pipeline"] is None:
        runtime_reasons.append("capture_pipeline-unavailable")
    if runtime_reasons:
        block_stage("phase624_runtime_resource_draw", runtime_reasons)
    else:
        reports["phase624_runtime_resource_draw"] = _execute_stage(
            stages["phase624_runtime_resource_draw"], out / OUTPUT_NAMES["phase624_runtime_resource_draw"],
            lambda: build_runtime_resource_draw_candidate_join(
                reports["phase623_scene_geometry"], values["capture_pipeline"]
            ),
        )

    runtime_draw = reports["phase624_runtime_resource_draw"]
    repeated_count = 0
    if isinstance(runtime_draw, Mapping):
        runtime_summary = runtime_draw.get("summary")
        if isinstance(runtime_summary, Mapping):
            value = runtime_summary.get("repeated_scene_instance_draw_count")
            if isinstance(value, int) and not isinstance(value, bool):
                repeated_count = value
    if runtime_draw is None:
        block_stage("phase625_repeated_instance", ["phase624-runtime-resource-draw-unavailable"])
    elif repeated_count == 0:
        stages["phase625_repeated_instance"].update({
            "status": "not-needed",
            "blocking_reasons": [],
        })
    elif values["object_candidate_join"] is None:
        block_stage(
            "phase625_repeated_instance",
            ["object_candidate_join-required-for-repeated-instances"],
        )
    elif values["capture_pipeline"] is None:
        block_stage("phase625_repeated_instance", ["capture_pipeline-unavailable"])
    else:
        reports["phase625_repeated_instance"] = _execute_stage(
            stages["phase625_repeated_instance"], out / OUTPUT_NAMES["phase625_repeated_instance"],
            lambda: build_repeated_scene_instance_transform_join(
                runtime_draw,
                values["object_candidate_join"],
                values["capture_pipeline"],
            ),
        )

    if values["base_audit"] is None:
        block_stage("phase626_frontier", ["base_audit-unavailable"])
    else:
        reports["phase626_frontier"] = _execute_stage(
            stages["phase626_frontier"], out / OUTPUT_NAMES["phase626_frontier"],
            lambda: build_renderer_frontier_audit(
                values["base_audit"],
                fxo_provenance=reports["phase619_fxo"],
                material_constants=reports["phase620_material_constants"],
                material_textures=reports["phase622_material_textures"],
                scene_geometry=reports["phase623_scene_geometry"],
                runtime_resource_draw=reports["phase624_runtime_resource_draw"],
                repeated_instance_transforms=reports["phase625_repeated_instance"],
            ),
        )

    # Stage exceptions are blockers too; _execute_stage records them on the row.
    for name, row in stages.items():
        if row["status"] == "blocked-error":
            blockers.extend(f"{name}:{reason}" for reason in row["blocking_reasons"])

    frontier = reports["phase626_frontier"]
    frontier_summary = frontier.get("summary") if isinstance(frontier, Mapping) else {}
    frontier_requirements = frontier.get("requirements") if isinstance(frontier, Mapping) else []
    requirement_status_counts = Counter(
        str(row.get("status"))
        for row in (frontier_requirements or [])
        if isinstance(row, Mapping)
    )
    unique_blockers = list(dict.fromkeys(blockers))
    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": "blocked" if unique_blockers else "completed",
        "summary": {
            "completed_stage_count": sum(row["status"] == "completed" for row in stages.values()),
            "not_needed_stage_count": sum(row["status"] == "not-needed" for row in stages.values()),
            "blocked_stage_count": sum(str(row["status"]).startswith("blocked") for row in stages.values()),
            "renderer_capture_required_now": bool(
                isinstance(frontier_summary, Mapping)
                and frontier_summary.get("capture_required_now") is True
            ),
            "frontier_requirement_status_counts": dict(sorted(requirement_status_counts.items())),
        },
        "inputs": inputs,
        "corpus": corpus_rows,
        "stages": [stages[name] for name in stages],
        "blocking_reasons": unique_blockers,
        "renderer_frontier": {
            "status": frontier.get("status") if isinstance(frontier, Mapping) else None,
            "existing_data_requiring_tooling": list(frontier.get("existing_data_requiring_tooling") or []) if isinstance(frontier, Mapping) else [],
            "genuinely_absent_capture_observations": list(frontier.get("genuinely_absent_capture_observations") or []) if isinstance(frontier, Mapping) else [],
            "capture_blockers": list(frontier.get("capture_blockers") or []) if isinstance(frontier, Mapping) else [],
            "conditional_minimal_capture": list(frontier.get("conditional_minimal_capture") or []) if isinstance(frontier, Mapping) else [],
        },
        "boundary": {
            "orchestration_only": True,
            "adds_new_proof_semantics": False,
            "ranking_is_proof": False,
            "missing_input_is_candidate_contradiction": False,
            "missing_capture_event_implies_recapture": False,
            "buffer_payload_is_last_conditional_fallback": True,
            "original_game_execution_required": False,
        },
    }
    manifest_path = out / "silverstone_renderer_production_run.json"
    _write_json_atomic(manifest_path, manifest)
    return manifest


def _default_shader_targets() -> str:
    return str(ROOT / "evidence" / "silverstone_era3_runtime_shader_targets.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--corpus", action="append", default=[], help="BFF or ZIP corpus input; repeatable")
    parser.add_argument("--base-audit", required=True)
    parser.add_argument("--ambiguity-audit", required=True)
    parser.add_argument("--runtime-shader-targets", default=_default_shader_targets())
    parser.add_argument("--draw-local", required=True)
    parser.add_argument("--capture-pipeline", required=True)
    parser.add_argument("--object-candidate-join")
    args = parser.parse_args(argv)

    manifest = run_production(
        output_dir=args.output_dir,
        corpus=args.corpus,
        base_audit=args.base_audit,
        ambiguity_audit=args.ambiguity_audit,
        runtime_shader_targets=args.runtime_shader_targets,
        draw_local=args.draw_local,
        capture_pipeline=args.capture_pipeline,
        object_candidate_join=args.object_candidate_join,
    )
    print(json.dumps({
        "format": manifest["format"],
        "status": manifest["status"],
        "summary": manifest["summary"],
        "blocking_reasons": manifest["blocking_reasons"],
        "renderer_frontier": manifest["renderer_frontier"],
        "manifest": str(Path(args.output_dir) / "silverstone_renderer_production_run.json"),
    }, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
