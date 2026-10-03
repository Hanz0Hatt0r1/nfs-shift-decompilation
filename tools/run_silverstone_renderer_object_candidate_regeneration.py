#!/usr/bin/env python3
"""Regenerate SGB runtime object candidates from corpus and capture evidence.

Phase 638 scans every source SGB occurrence instead of selecting a scene by
filename. Each SGB is decoded independently and joined to exact runtime resource
evidence through the existing IR manifest and SGB candidate contracts. A scene
is selected only when exactly one distinct SGB payload + canonical candidate
join is ready. Exact duplicate occurrences are retained as provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TOOLS = ROOT / "tools"
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
for path in (TOOLS, ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from offline_resource_pipeline import materialize_bff_inputs
from offline_scene_ir import build_scene_ir
from sgb_multimatrix_root_consensus import build_multimatrix_root_consensus
from sgb_object_render_handoff import build_sgb_object_render_handoff_set
from sgb_placement_join import build_sgb_placement_join
from sgb_runtime import parse_sgb_runtime
from sgb_runtime_object_candidate_join import build_runtime_object_candidate_join
from sgb_scene_placement import build_sgb_scene_placement
from shift_importer import BFF

FORMAT = "SHIFT.SilverstoneRendererObjectCandidateRegeneration/1"
CAPTURE_FORMAT = "SHIFT.IMBRuntimeCapturePipeline/1"
OBJECT_JOIN_FORMAT = "SHIFT.SGBRuntimeObjectCandidateJoin/1"
ROOT_CONSENSUS_FORMAT = "SHIFT.SGBMultiMatrixRootConsensus/1"


def _canonical_sha(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _write_json_atomic(path: Path, value: Any) -> str:
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


def _load_json_map(path: str | Path, expected: str) -> Mapping[str, Any]:
    source = Path(path).expanduser()
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"JSON object expected: {source}")
    if value.get("format") != expected:
        raise ValueError(
            f"{source} must be {expected}, got {value.get('format')!r}"
        )
    return value


def _discover_sgb_occurrences(inputs: Sequence[str | Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with materialize_bff_inputs(inputs) as materialized:
        for archive_ordinal, materialized_archive in enumerate(materialized):
            with BFF(materialized_archive.path) as archive:
                for entry in archive.entries:
                    path = str(entry.path).replace("\\", "/")
                    if not path.lower().endswith(".sgb"):
                        continue
                    try:
                        payload = archive.extract_entry(entry, type2="lzx")
                    except Exception as exc:
                        rows.append({
                            "status": "extract-failed",
                            "archive_ordinal": archive_ordinal,
                            "archive": archive.path.name,
                            "source": materialized_archive.source,
                            "source_member": materialized_archive.member,
                            "entry_index": int(entry.index),
                            "path": path,
                            "error": f"{type(exc).__name__}:{exc}",
                            "payload": None,
                            "sha256": None,
                        })
                        continue
                    rows.append({
                        "status": "extracted",
                        "archive_ordinal": archive_ordinal,
                        "archive": archive.path.name,
                        "source": materialized_archive.source,
                        "source_member": materialized_archive.member,
                        "entry_index": int(entry.index),
                        "path": path,
                        "error": None,
                        "payload": payload,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    })
    return rows


def _load_ir_manifest(ir_root: Path) -> list[Mapping[str, Any]]:
    value = json.loads((ir_root / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("IR manifest must be a JSON array")
    return [row for row in value if isinstance(row, Mapping)]


def _persist_occurrence(
    root: Path,
    ordinal: int,
    source: Mapping[str, Any],
    reports: Mapping[str, Any],
) -> dict[str, Any]:
    sha = str(source.get("sha256") or "unknown")
    directory = root / f"{ordinal:04d}_{sha[:12]}"
    directory.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, dict[str, Any]] = {}
    for name, report in reports.items():
        if report is None:
            continue
        path = directory / f"{name}.json"
        digest = _write_json_atomic(path, report)
        artifacts[name] = {"path": str(path), "sha256": digest}
    return artifacts


def _evaluate_occurrence(
    occurrence: Mapping[str, Any],
    capture_pipeline: Mapping[str, Any],
    ir_manifest: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    provenance = {
        key: occurrence.get(key)
        for key in (
            "archive_ordinal",
            "archive",
            "source",
            "source_member",
            "entry_index",
            "path",
            "sha256",
        )
    }
    payload = occurrence.get("payload")
    if not isinstance(payload, (bytes, bytearray)):
        return {
            "status": "blocked",
            "ready": False,
            "blocking_reasons": [
                f"sgb-extract:{occurrence.get('error') or 'payload-unavailable'}"
            ],
            "provenance": provenance,
            "initial_join_ready": False,
            "root_consensus_ready": False,
            "final_join_ready": False,
            "final_join_canonical_sha256": None,
            "transform_enriched": False,
        }, {}

    reports: dict[str, Any] = {}
    blockers: list[str] = []
    try:
        runtime = parse_sgb_runtime(bytes(payload), strict=False)
        reports["sgb_runtime"] = runtime
        placement_join = build_sgb_placement_join(runtime)
        reports["placement_join"] = placement_join
        scene_placement = build_sgb_scene_placement(placement_join)
        reports["scene_placement"] = scene_placement
        initial_handoffs = build_sgb_object_render_handoff_set(runtime)
        reports["object_handoffs_initial"] = initial_handoffs
        initial_join = build_runtime_object_candidate_join(
            scene_placement,
            initial_handoffs,
            capture_pipeline,
            ir_manifest,
        )
        reports["object_candidate_join_initial"] = initial_join
    except Exception as exc:
        blockers.append(f"static-object-chain:{type(exc).__name__}:{exc}")
        return {
            "status": "blocked",
            "ready": False,
            "blocking_reasons": blockers,
            "provenance": provenance,
            "initial_join_ready": False,
            "root_consensus_ready": False,
            "final_join_ready": False,
            "final_join_canonical_sha256": None,
            "transform_enriched": False,
        }, reports

    final_join = initial_join
    root_consensus: Mapping[str, Any] | None = None
    transform_enriched = False
    if initial_join.get("ready") is True:
        try:
            root_consensus = build_multimatrix_root_consensus(
                runtime,
                initial_join,
                capture_pipeline,
            )
            reports["root_consensus"] = root_consensus
            if root_consensus.get("ready") is True:
                enriched_handoffs = build_sgb_object_render_handoff_set(
                    runtime,
                    root_consensus=root_consensus,
                )
                reports["object_handoffs_enriched"] = enriched_handoffs
                enriched_join = build_runtime_object_candidate_join(
                    scene_placement,
                    enriched_handoffs,
                    capture_pipeline,
                    ir_manifest,
                )
                reports["object_candidate_join_enriched"] = enriched_join
                if enriched_join.get("ready") is True:
                    final_join = enriched_join
                    transform_enriched = True
        except Exception as exc:
            reports["root_consensus_error"] = {
                "status": "not-applied",
                "error": f"{type(exc).__name__}:{exc}",
            }

    reports["object_candidate_join_final"] = final_join
    ready = final_join.get("ready") is True
    final_sha = _canonical_sha(final_join) if ready else None
    return {
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": list(final_join.get("blocking_reasons") or []),
        "provenance": provenance,
        "sgb_runtime_ready": reports.get("sgb_runtime", {}).get("ready") is True,
        "scene_placement_ready": reports.get("scene_placement", {}).get("ready") is True,
        "initial_handoff_ready": reports.get("object_handoffs_initial", {}).get("ready") is True,
        "initial_join_ready": initial_join.get("ready") is True,
        "root_consensus_ready": (
            isinstance(root_consensus, Mapping)
            and root_consensus.get("ready") is True
        ),
        "root_consensus_status": (
            root_consensus.get("status")
            if isinstance(root_consensus, Mapping)
            else None
        ),
        "final_join_ready": ready,
        "final_join_status": final_join.get("status"),
        "final_join_identity_complete": final_join.get("identity_complete") is True,
        "runtime_resource_count": int(final_join.get("runtime_resource_count") or 0),
        "matched_runtime_resource_count": int(
            final_join.get("matched_runtime_resource_count") or 0
        ),
        "unique_candidate_resource_count": int(
            final_join.get("unique_candidate_resource_count") or 0
        ),
        "final_join_canonical_sha256": final_sha,
        "transform_enriched": transform_enriched,
    }, reports


def regenerate_runtime_object_candidates(
    *,
    corpus: list[str | Path],
    capture_pipeline: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    out = Path(output_dir)
    ir_root = out / "scene-ir"
    sgb_root = out / "sgb-candidates"
    blockers: list[str] = []

    capture: Mapping[str, Any] | None = None
    try:
        capture = _load_json_map(capture_pipeline, CAPTURE_FORMAT)
    except Exception as exc:
        blockers.append(f"capture_pipeline:{type(exc).__name__}:{exc}")
    if isinstance(capture, Mapping) and capture.get("pipeline_ready") is not True:
        blockers.append("capture_pipeline:not-ready")

    scene_ir: Mapping[str, Any] | None = None
    ir_manifest: list[Mapping[str, Any]] = []
    if capture is not None and not blockers:
        try:
            scene_ir = build_scene_ir(corpus, ir_root)
        except Exception as exc:
            blockers.append(f"scene_ir:failed:{type(exc).__name__}:{exc}")
        if isinstance(scene_ir, Mapping):
            if scene_ir.get("ready") is not True:
                blockers.extend(
                    f"scene_ir:{reason}"
                    for reason in (scene_ir.get("blocking_reasons") or ["not-ready"])
                )
            else:
                try:
                    ir_manifest = _load_ir_manifest(ir_root)
                except Exception as exc:
                    blockers.append(
                        f"scene_ir:manifest:{type(exc).__name__}:{exc}"
                    )

    occurrences: list[dict[str, Any]] = []
    if capture is not None and not blockers:
        try:
            occurrences = _discover_sgb_occurrences(corpus)
        except Exception as exc:
            blockers.append(f"sgb_discovery:failed:{type(exc).__name__}:{exc}")
    if not occurrences and not blockers:
        blockers.append("sgb_discovery:no-sgb-occurrences")

    evaluations: list[dict[str, Any]] = []
    reports_by_ordinal: dict[int, dict[str, Any]] = {}
    if capture is not None and ir_manifest and not blockers:
        for ordinal, occurrence in enumerate(occurrences):
            evaluation, reports = _evaluate_occurrence(
                occurrence,
                capture,
                ir_manifest,
            )
            evaluation["occurrence_ordinal"] = ordinal
            evaluation["artifacts"] = _persist_occurrence(
                sgb_root,
                ordinal,
                occurrence,
                reports,
            )
            evaluations.append(evaluation)
            reports_by_ordinal[ordinal] = reports

    ready_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in evaluations:
        if row.get("ready") is not True:
            continue
        sgb_sha = str((row.get("provenance") or {}).get("sha256") or "")
        join_sha = str(row.get("final_join_canonical_sha256") or "")
        if sgb_sha and join_sha:
            ready_groups[(sgb_sha, join_sha)].append(row)

    selected_group: list[dict[str, Any]] | None = None
    if len(ready_groups) == 1:
        selected_group = next(iter(ready_groups.values()))
    elif len(ready_groups) > 1:
        blockers.append(
            f"scene_selection:multiple-ready-distinct-sgb-identities:{len(ready_groups)}"
        )
    elif evaluations and not blockers:
        blockers.append("scene_selection:no-ready-sgb-object-join")

    selected_join_path: str | None = None
    selected_root_consensus_path: str | None = None
    selected_scene_placement_path: str | None = None
    selected_handoffs_path: str | None = None
    selected: dict[str, Any] | None = None
    if selected_group:
        representative = min(
            selected_group,
            key=lambda row: int(row.get("occurrence_ordinal") or 0),
        )
        ordinal = int(representative["occurrence_ordinal"])
        reports = reports_by_ordinal[ordinal]
        final_join = reports.get("object_candidate_join_final")
        if isinstance(final_join, Mapping):
            selected_join_path = str(out / "silverstone_sgb_runtime_object_candidate_join.json")
            _write_json_atomic(Path(selected_join_path), final_join)
        scene_placement = reports.get("scene_placement")
        if isinstance(scene_placement, Mapping):
            selected_scene_placement_path = str(out / "silverstone_sgb_scene_placement.json")
            _write_json_atomic(Path(selected_scene_placement_path), scene_placement)
        handoffs = (
            reports.get("object_handoffs_enriched")
            or reports.get("object_handoffs_initial")
        )
        if isinstance(handoffs, Mapping):
            selected_handoffs_path = str(out / "silverstone_sgb_object_render_handoffs.json")
            _write_json_atomic(Path(selected_handoffs_path), handoffs)
        root_consensus = reports.get("root_consensus")
        if isinstance(root_consensus, Mapping):
            selected_root_consensus_path = str(out / "silverstone_sgb_multimatrix_root_consensus.json")
            _write_json_atomic(Path(selected_root_consensus_path), root_consensus)

        selected = {
            "sgb_sha256": (representative.get("provenance") or {}).get("sha256"),
            "final_join_canonical_sha256": representative.get(
                "final_join_canonical_sha256"
            ),
            "duplicate_occurrence_count": len(selected_group),
            "occurrences": [row.get("provenance") for row in selected_group],
            "representative_occurrence_ordinal": ordinal,
            "identity_complete": representative.get(
                "final_join_identity_complete"
            ) is True,
            "transform_enriched": representative.get("transform_enriched") is True,
            "root_consensus_ready": representative.get("root_consensus_ready") is True,
        }

    blockers = list(dict.fromkeys(str(value) for value in blockers))
    ready = bool(selected_join_path) and not blockers
    report = {
        "format": FORMAT,
        "version": 1,
        "status": "completed" if ready else "blocked",
        "ready": ready,
        "summary": {
            "scene_ir_ready": (
                isinstance(scene_ir, Mapping) and scene_ir.get("ready") is True
            ),
            "ir_manifest_resource_count": len(ir_manifest),
            "sgb_occurrence_count": len(occurrences),
            "evaluated_sgb_occurrence_count": len(evaluations),
            "ready_sgb_occurrence_count": sum(
                row.get("ready") is True for row in evaluations
            ),
            "ready_distinct_sgb_identity_count": len(ready_groups),
            "selected_scene_ready": selected is not None,
            "selected_scene_identity_complete": (
                selected.get("identity_complete") is True if selected else False
            ),
            "selected_scene_transform_enriched": (
                selected.get("transform_enriched") is True if selected else False
            ),
            "blocking_reason_count": len(blockers),
        },
        "inputs": {
            "corpus": [str(Path(value).expanduser()) for value in corpus],
            "capture_pipeline": str(Path(capture_pipeline).expanduser()),
        },
        "scene_ir": {
            "format": scene_ir.get("format") if isinstance(scene_ir, Mapping) else None,
            "status": scene_ir.get("status") if isinstance(scene_ir, Mapping) else None,
            "summary": {
                "archive_count": scene_ir.get("archive_count"),
                "manifest_resource_count": scene_ir.get("manifest_resource_count"),
                "manifest_error_count": scene_ir.get("manifest_error_count"),
            } if isinstance(scene_ir, Mapping) else None,
            "root": str(ir_root) if isinstance(scene_ir, Mapping) else None,
        },
        "sgb_occurrences": [
            {
                key: value
                for key, value in row.items()
                if key != "payload"
            }
            for row in occurrences
        ],
        "evaluations": evaluations,
        "selected_scene": selected,
        "outputs": {
            "object_candidate_join": selected_join_path,
            "scene_placement": selected_scene_placement_path,
            "object_handoffs": selected_handoffs_path,
            "root_consensus": selected_root_consensus_path,
            "scene_ir_root": str(ir_root) if isinstance(scene_ir, Mapping) else None,
        },
        "blocking_reasons": blockers,
        "boundary": {
            "scene_selected_by_filename": False,
            "scene_selected_by_archive_order": False,
            "scene_selected_by_frequency": False,
            "selection_gate": (
                "exact SGB payload SHA + canonical ready SGBRuntimeObjectCandidateJoin"
            ),
            "exact_duplicate_sgb_occurrences_may_collapse": True,
            "different_sgb_payloads_with_same_logical_paths_may_collapse": False,
            "runtime_resource_identity": "archive/path/SHA + same-instance gate + IR manifest",
            "logical_scene_path_is_exact_object_identity": False,
            "identity_complete_is_render_admission": False,
            "root_consensus_is_required_for_initial_object_join": False,
            "root_consensus_is_optional_transform_enrichment": True,
            "root_consensus_failure_selects_scene": False,
            "original_game_execution_required": False,
            "new_capture_required": False,
        },
    }
    _write_json_atomic(
        out / "silverstone_renderer_object_candidate_regeneration.json",
        report,
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-pipeline", required=True)
    parser.add_argument("--corpus", action="append", default=[])
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    report = regenerate_runtime_object_candidates(
        corpus=args.corpus,
        capture_pipeline=args.capture_pipeline,
        output_dir=args.output_dir,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "summary": report["summary"],
        "blocking_reasons": report["blocking_reasons"],
        "object_candidate_join": report["outputs"]["object_candidate_join"],
        "manifest": str(
            Path(args.output_dir)
            / "silverstone_renderer_object_candidate_regeneration.json"
        ),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
