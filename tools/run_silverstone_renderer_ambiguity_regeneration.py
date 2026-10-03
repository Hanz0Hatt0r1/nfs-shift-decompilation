#!/usr/bin/env python3
"""Regenerate the Silverstone Phase 618 ambiguity audit offline.

The stage uses only the existing historical D3D9 JSONL plus static game-resource
corpora. It composes the already implemented Phase 605/609/610/611/613/615/617
builders; it does not launch the game, infer a winning candidate, or request a
new capture when historical observations are absent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TOOLS = ROOT / "tools"
if SRC.is_dir():
    paths = [ROOT, SRC]
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
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from audit_imb_corpus import audit_imb_corpus
from d3d9_target_draw_signatures import catalog_target_draw_signatures
from d3d9_target_pointer_observations import build_target_pointer_observations
from imb_draw_local_ambiguity_audit import build_draw_local_ambiguity_audit
from imb_draw_local_static_candidate_join import build_draw_local_static_candidate_join
from imb_runtime_geometry_pointer_candidate_join import (
    build_runtime_geometry_pointer_candidate_join,
)
from imb_runtime_geometry_shape_candidate_join import (
    build_runtime_geometry_shape_candidate_join,
)
from imb_runtime_material_descriptor_candidate_join import (
    validate_files as validate_material_descriptor_files,
)
from imb_runtime_pipeline_candidate_join import build_runtime_pipeline_candidate_join

FORMAT = "SHIFT.SilverstoneRendererAmbiguityRegeneration/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"
DRAW_LOCAL_FORMAT = "SHIFT.D3D9TargetDrawLocalEvidence/1"
OUTPUT_NAMES = {
    "runtime_catalog": "d3d9_target_draw_signature_catalog.json",
    "pointer_observations": "d3d9_target_pointer_observations.json",
    "corpus_audit": "imb_corpus_audit.json",
    "pipeline_join": "imb_runtime_pipeline_candidate_join.json",
    "geometry_shape_join": "imb_runtime_geometry_shape_candidate_join.json",
    "material_descriptor_join": "imb_runtime_material_descriptor_candidate_join.json",
    "geometry_pointer_join": "imb_runtime_geometry_pointer_candidate_join.json",
    "static_candidate_join": "imb_draw_local_static_candidate_join.json",
    "ambiguity_audit": "imb_draw_local_ambiguity_audit.json",
}
STAGE_ORDER = tuple(OUTPUT_NAMES)


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


def _file_record(path: str | Path, *, label: str) -> tuple[Path, dict[str, Any], list[str]]:
    source = Path(path).expanduser()
    record = {
        "label": label,
        "path": str(source),
        "present": source.is_file(),
        "size": source.stat().st_size if source.is_file() else None,
        "sha256": _sha256_file(source) if source.is_file() else None,
    }
    blockers = [] if source.is_file() else [f"input:{label}:file-not-found:{source}"]
    return source, record, blockers


def _json_input(
    path: str | Path,
    *,
    label: str,
    expected_format: str,
) -> tuple[Path, dict[str, Any], Mapping[str, Any] | None, list[str]]:
    source, record, blockers = _file_record(path, label=label)
    record["expected_format"] = expected_format
    record["format"] = None
    if blockers:
        return source, record, None, blockers
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except Exception as exc:
        blockers.append(
            f"input:{label}:json-read-failed:{type(exc).__name__}:{exc}"
        )
        return source, record, None, blockers
    if not isinstance(value, Mapping):
        blockers.append(f"input:{label}:json-root-not-object")
        return source, record, None, blockers
    record["format"] = value.get("format")
    if value.get("format") != expected_format:
        blockers.append(
            f"input:{label}:format-mismatch:{value.get('format')!r}"
        )
        return source, record, None, blockers
    return source, record, value, blockers


def _stage(name: str, out: Path) -> dict[str, Any]:
    return {
        "name": name,
        "status": "pending",
        "output": str(out / OUTPUT_NAMES[name]),
        "format": None,
        "sha256": None,
        "summary": None,
        "blocking_reasons": [],
    }


def _complete(
    row: dict[str, Any],
    output: Path,
    report: Mapping[str, Any],
) -> None:
    row["status"] = "completed"
    row["format"] = report.get("format")
    row["sha256"] = _write_json_atomic(output, report)
    summary = report.get("summary")
    row["summary"] = dict(summary) if isinstance(summary, Mapping) else None


def _block(
    row: dict[str, Any],
    blockers: list[str],
    reasons: list[str],
    *,
    error: bool = False,
) -> None:
    row["status"] = "blocked-error" if error else "blocked-missing-input"
    row["blocking_reasons"] = list(reasons)
    blockers.extend(f"{row['name']}:{reason}" for reason in reasons)


def _materialize_render_bff(
    source: Path,
    stack: ExitStack,
) -> tuple[Path, dict[str, Any]]:
    if source.suffix.lower() != ".zip":
        return source, {
            "source_kind": "bff",
            "selected_entry": None,
            "selection_policy": "direct-file",
        }

    archive = zipfile.ZipFile(source)
    stack.callback(archive.close)
    candidates = [
        info
        for info in archive.infolist()
        if not info.is_dir()
        and Path(info.filename.replace("\\", "/")).name.lower() == "render.bff"
    ]
    if len(candidates) != 1:
        raise ValueError(
            "render ZIP must contain exactly one basename render.bff; "
            f"found {len(candidates)}"
        )
    info = candidates[0]
    root = Path(
        stack.enter_context(
            tempfile.TemporaryDirectory(prefix="shift-render-bff-")
        )
    )
    target = root / "render.bff"
    target.write_bytes(archive.read(info))
    return target, {
        "source_kind": "zip",
        "selected_entry": info.filename,
        "selected_entry_size": info.file_size,
        "selected_entry_sha256": _sha256_file(target),
        "selection_policy": "exactly-one-basename-render.bff",
    }


def regenerate_renderer_ambiguity(
    *,
    capture_jsonl: str | Path,
    runtime_shader_targets: str | Path,
    draw_local: str | Path,
    source_archive: str | Path,
    render_archive: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    capture_path, capture_record, capture_blockers = _file_record(
        capture_jsonl, label="capture"
    )
    _, target_record, targets, target_blockers = _json_input(
        runtime_shader_targets,
        label="runtime_shader_targets",
        expected_format=TARGET_FORMAT,
    )
    _, draw_record, draw_value, draw_blockers = _json_input(
        draw_local,
        label="draw_local",
        expected_format=DRAW_LOCAL_FORMAT,
    )
    source_path, source_record, source_blockers = _file_record(
        source_archive, label="source_archive"
    )
    render_path, render_record, render_blockers = _file_record(
        render_archive, label="render_archive"
    )
    blockers: list[str] = [
        *capture_blockers,
        *target_blockers,
        *draw_blockers,
        *source_blockers,
        *render_blockers,
    ]
    stages = {
        name: _stage(name, out)
        for name in STAGE_ORDER
    }
    reports: dict[str, Mapping[str, Any] | None] = {
        name: None for name in STAGE_ORDER
    }

    capture_target_ready = capture_path.is_file() and targets is not None
    if capture_target_ready:
        try:
            with capture_path.open("r", encoding="utf-8") as stream:
                report = catalog_target_draw_signatures(
                    stream,
                    target_inventory=targets,
                )
            reports["runtime_catalog"] = report
            _complete(
                stages["runtime_catalog"],
                out / OUTPUT_NAMES["runtime_catalog"],
                report,
            )
            target_draw_count = int(
                (report.get("summary") or {}).get("target_draw_count") or 0
            )
            if target_draw_count <= 0:
                blockers.append("runtime_catalog:no-target-draws-observed")
        except Exception as exc:
            _block(
                stages["runtime_catalog"],
                blockers,
                [f"{type(exc).__name__}:{exc}"],
                error=True,
            )

        if reports["runtime_catalog"] is not None:
            try:
                with capture_path.open("r", encoding="utf-8") as stream:
                    report = build_target_pointer_observations(
                        stream,
                        target_inventory=targets,
                        target_catalog=reports["runtime_catalog"],
                    )
                reports["pointer_observations"] = report
                _complete(
                    stages["pointer_observations"],
                    out / OUTPUT_NAMES["pointer_observations"],
                    report,
                )
                alignment = report.get("catalog_alignment")
                if not isinstance(alignment, Mapping) or alignment.get("status") != "exact":
                    blockers.append(
                        "pointer_observations:catalog-alignment-not-exact"
                    )
            except Exception as exc:
                _block(
                    stages["pointer_observations"],
                    blockers,
                    [f"{type(exc).__name__}:{exc}"],
                    error=True,
                )
        else:
            _block(
                stages["pointer_observations"],
                blockers,
                ["runtime-catalog-unavailable"],
            )
    else:
        reasons = []
        if not capture_path.is_file():
            reasons.append("capture-unavailable")
        if targets is None:
            reasons.append("runtime-shader-targets-unavailable")
        _block(stages["runtime_catalog"], blockers, list(reasons))
        _block(stages["pointer_observations"], blockers, list(reasons))

    if source_path.is_file():
        try:
            report = audit_imb_corpus([source_path])
            reports["corpus_audit"] = report
            _complete(
                stages["corpus_audit"],
                out / OUTPUT_NAMES["corpus_audit"],
                report,
            )
            if report.get("ready") is not True:
                blockers.append("corpus_audit:not-all-selected-imbs-ready")
        except Exception as exc:
            _block(
                stages["corpus_audit"],
                blockers,
                [f"{type(exc).__name__}:{exc}"],
                error=True,
            )
    else:
        _block(stages["corpus_audit"], blockers, ["source-archive-unavailable"])

    if reports["runtime_catalog"] is not None and targets is not None:
        try:
            report = build_runtime_pipeline_candidate_join(
                reports["runtime_catalog"],
                targets,
            )
            reports["pipeline_join"] = report
            _complete(
                stages["pipeline_join"],
                out / OUTPUT_NAMES["pipeline_join"],
                report,
            )
        except Exception as exc:
            _block(
                stages["pipeline_join"],
                blockers,
                [f"{type(exc).__name__}:{exc}"],
                error=True,
            )
    else:
        reasons = []
        if reports["runtime_catalog"] is None:
            reasons.append("runtime-catalog-unavailable")
        if targets is None:
            reasons.append("runtime-shader-targets-unavailable")
        _block(stages["pipeline_join"], blockers, reasons)

    corpus_ready = (
        isinstance(reports["corpus_audit"], Mapping)
        and reports["corpus_audit"].get("ready") is True
    )
    if (
        reports["runtime_catalog"] is not None
        and reports["pipeline_join"] is not None
        and corpus_ready
    ):
        try:
            report = build_runtime_geometry_shape_candidate_join(
                reports["runtime_catalog"],
                reports["pipeline_join"],
                reports["corpus_audit"],
            )
            reports["geometry_shape_join"] = report
            _complete(
                stages["geometry_shape_join"],
                out / OUTPUT_NAMES["geometry_shape_join"],
                report,
            )
        except Exception as exc:
            _block(
                stages["geometry_shape_join"],
                blockers,
                [f"{type(exc).__name__}:{exc}"],
                error=True,
            )
    else:
        reasons = []
        if reports["runtime_catalog"] is None:
            reasons.append("runtime-catalog-unavailable")
        if reports["pipeline_join"] is None:
            reasons.append("pipeline-join-unavailable")
        if not corpus_ready:
            reasons.append("corpus-audit-not-ready")
        _block(stages["geometry_shape_join"], blockers, reasons)

    render_selection: dict[str, Any] | None = None
    if (
        reports["runtime_catalog"] is not None
        and reports["geometry_shape_join"] is not None
        and source_path.is_file()
        and render_path.is_file()
    ):
        try:
            with ExitStack() as stack:
                render_bff, render_selection = _materialize_render_bff(
                    render_path,
                    stack,
                )
                report = validate_material_descriptor_files(
                    out / OUTPUT_NAMES["runtime_catalog"],
                    out / OUTPUT_NAMES["geometry_shape_join"],
                    source_path,
                    render_bff,
                )
            reports["material_descriptor_join"] = report
            _complete(
                stages["material_descriptor_join"],
                out / OUTPUT_NAMES["material_descriptor_join"],
                report,
            )
        except Exception as exc:
            _block(
                stages["material_descriptor_join"],
                blockers,
                [f"{type(exc).__name__}:{exc}"],
                error=True,
            )
    else:
        reasons = []
        if reports["runtime_catalog"] is None:
            reasons.append("runtime-catalog-unavailable")
        if reports["geometry_shape_join"] is None:
            reasons.append("geometry-shape-join-unavailable")
        if not source_path.is_file():
            reasons.append("source-archive-unavailable")
        if not render_path.is_file():
            reasons.append("render-archive-unavailable")
        _block(stages["material_descriptor_join"], blockers, reasons)

    if (
        reports["pointer_observations"] is not None
        and reports["material_descriptor_join"] is not None
    ):
        try:
            report = build_runtime_geometry_pointer_candidate_join(
                reports["pointer_observations"],
                reports["material_descriptor_join"],
            )
            reports["geometry_pointer_join"] = report
            _complete(
                stages["geometry_pointer_join"],
                out / OUTPUT_NAMES["geometry_pointer_join"],
                report,
            )
        except Exception as exc:
            _block(
                stages["geometry_pointer_join"],
                blockers,
                [f"{type(exc).__name__}:{exc}"],
                error=True,
            )
    else:
        reasons = []
        if reports["pointer_observations"] is None:
            reasons.append("pointer-observations-unavailable")
        if reports["material_descriptor_join"] is None:
            reasons.append("material-descriptor-join-unavailable")
        _block(stages["geometry_pointer_join"], blockers, reasons)

    if draw_value is not None and reports["geometry_pointer_join"] is not None:
        try:
            report = build_draw_local_static_candidate_join(
                draw_value,
                reports["geometry_pointer_join"],
            )
            reports["static_candidate_join"] = report
            _complete(
                stages["static_candidate_join"],
                out / OUTPUT_NAMES["static_candidate_join"],
                report,
            )
        except Exception as exc:
            _block(
                stages["static_candidate_join"],
                blockers,
                [f"{type(exc).__name__}:{exc}"],
                error=True,
            )
    else:
        reasons = []
        if draw_value is None:
            reasons.append("draw-local-unavailable")
        if reports["geometry_pointer_join"] is None:
            reasons.append("geometry-pointer-join-unavailable")
        _block(stages["static_candidate_join"], blockers, reasons)

    if reports["static_candidate_join"] is not None:
        try:
            report = build_draw_local_ambiguity_audit(
                reports["static_candidate_join"]
            )
            reports["ambiguity_audit"] = report
            _complete(
                stages["ambiguity_audit"],
                out / OUTPUT_NAMES["ambiguity_audit"],
                report,
            )
        except Exception as exc:
            _block(
                stages["ambiguity_audit"],
                blockers,
                [f"{type(exc).__name__}:{exc}"],
                error=True,
            )
    else:
        _block(
            stages["ambiguity_audit"],
            blockers,
            ["static-candidate-join-unavailable"],
        )

    unique_blockers = list(dict.fromkeys(str(value) for value in blockers))
    ready = reports["ambiguity_audit"] is not None and not unique_blockers
    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": "completed" if ready else "blocked",
        "ready": ready,
        "summary": {
            "completed_stage_count": sum(
                row["status"] == "completed" for row in stages.values()
            ),
            "blocked_stage_count": sum(
                str(row["status"]).startswith("blocked")
                for row in stages.values()
            ),
            "target_draw_count": (
                int(
                    ((reports["runtime_catalog"] or {}).get("summary") or {}).get(
                        "target_draw_count"
                    )
                    or 0
                )
                if isinstance(reports["runtime_catalog"], Mapping)
                else None
            ),
            "corpus_ready": corpus_ready,
            "ambiguity_audit_available": reports["ambiguity_audit"] is not None,
            "blocking_reason_count": len(unique_blockers),
        },
        "inputs": {
            "capture": capture_record,
            "runtime_shader_targets": target_record,
            "draw_local": draw_record,
            "source_archive": source_record,
            "render_archive": {
                **render_record,
                "materialization": render_selection,
            },
        },
        "stages": [stages[name] for name in STAGE_ORDER],
        "outputs": {
            name: (
                str(out / OUTPUT_NAMES[name])
                if reports[name] is not None
                else None
            )
            for name in STAGE_ORDER
        },
        "blocking_reasons": unique_blockers,
        "boundary": {
            "execution_mode": "offline-static-plus-existing-capture",
            "raw_capture_is_historical_input": True,
            "source_archive_is_static_input": True,
            "render_archive_is_static_input": True,
            "pointer_identity_scope": "capture-local-only",
            "static_candidates_are_render_admission": False,
            "candidate_ranking_is_proof": False,
            "zero_match_invents_candidate": False,
            "missing_capture_event_implies_recapture": False,
            "original_game_execution_required": False,
            "new_capture_required": False,
            "portable_resource_identity_claimed": False,
            "buffer_payload_required_now": False,
        },
    }
    _write_json_atomic(
        out / "silverstone_renderer_ambiguity_regeneration.json",
        manifest,
    )
    return manifest


def _default_targets() -> str:
    return str(ROOT / "evidence" / "silverstone_era3_runtime_shader_targets.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-jsonl", required=True)
    parser.add_argument("--draw-local", required=True)
    parser.add_argument("--source-archive", required=True)
    parser.add_argument("--render-archive", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--runtime-shader-targets",
        default=_default_targets(),
    )
    args = parser.parse_args(argv)

    manifest = regenerate_renderer_ambiguity(
        capture_jsonl=args.capture_jsonl,
        runtime_shader_targets=args.runtime_shader_targets,
        draw_local=args.draw_local,
        source_archive=args.source_archive,
        render_archive=args.render_archive,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "format": manifest["format"],
                "status": manifest["status"],
                "summary": manifest["summary"],
                "blocking_reasons": manifest["blocking_reasons"],
                "ambiguity_audit": manifest["outputs"]["ambiguity_audit"],
                "manifest": str(
                    Path(args.output_dir)
                    / "silverstone_renderer_ambiguity_regeneration.json"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
