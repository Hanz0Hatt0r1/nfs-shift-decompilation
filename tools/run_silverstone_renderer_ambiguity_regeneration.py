#!/usr/bin/env python3
"""Regenerate the Phase 618 renderer ambiguity audit from raw/corpus evidence.

The pipeline consumes only the historical D3D9 JSONL, the exact runtime shader
 target set, the already-regenerated draw-local report, and source BFF/ZIP
corpora.  It replays the existing Phase 603/606/610/611/613/615/617/618
builders without ranking candidates or executing the original game.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import defaultdict
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

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
    _build_material_occurrence_index,
    _materialize_bffs,
    _norm,
    _pixel_reflection_index,
    build_runtime_material_descriptor_candidate_join,
)
from imb_runtime_pipeline_candidate_join import build_runtime_pipeline_candidate_join
from shift_importer import BFF

FORMAT = "SHIFT.SilverstoneRendererAmbiguityRegeneration/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"
DRAW_LOCAL_FORMAT = "SHIFT.D3D9TargetDrawLocalEvidence/1"
AMBIGUITY_FORMAT = "SHIFT.IMBDrawLocalAmbiguityAudit/1"

OUTPUT_NAMES = {
    "phase603_runtime_catalog": "silverstone_target_draw_signature_catalog.json",
    "imb_corpus_audit": "silverstone_imb_corpus_audit.json",
    "phase606_pipeline_candidates": "silverstone_runtime_pipeline_candidate_join.json",
    "phase610_geometry_candidates": "silverstone_runtime_geometry_shape_candidate_join.json",
    "phase611_material_candidates": "silverstone_runtime_material_descriptor_candidate_join.json",
    "phase613_pointer_observations": "silverstone_target_pointer_observations.json",
    "phase615_geometry_pointer_candidates": "silverstone_runtime_geometry_pointer_candidate_join.json",
    "phase617_draw_local_static_candidates": "silverstone_draw_local_static_candidate_join.json",
    "phase618_ambiguity": "silverstone_draw_local_ambiguity_audit.json",
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


def _load_json_map(path: str | Path, expected_format: str) -> Mapping[str, Any]:
    source = Path(path).expanduser()
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"JSON object expected: {source}")
    if value.get("format") != expected_format:
        raise ValueError(
            f"{source} must be {expected_format}, got {value.get('format')!r}"
        )
    return value


def _input_record(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser()
    return {
        "path": str(source),
        "present": source.is_file(),
        "size": source.stat().st_size if source.is_file() else None,
        "sha256": _sha256_file(source) if source.is_file() else None,
    }


def _stage_row(name: str, phase: int | None, output: Path) -> dict[str, Any]:
    return {
        "name": name,
        "phase": phase,
        "status": "pending",
        "output": str(output),
        "format": None,
        "sha256": None,
        "summary": None,
        "blocking_reasons": [],
    }


def _execute_stage(
    row: dict[str, Any],
    output: Path,
    builder: Callable[[], Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    try:
        report = builder()
        if not isinstance(report, Mapping):
            raise ValueError("stage builder did not return a mapping")
        digest = _write_json_atomic(output, report)
    except Exception as exc:
        row["status"] = "blocked-error"
        row["blocking_reasons"] = [f"{type(exc).__name__}:{exc}"]
        return None
    row["status"] = "completed"
    row["format"] = report.get("format")
    row["sha256"] = digest
    summary = report.get("summary")
    row["summary"] = dict(summary) if isinstance(summary, Mapping) else None
    return report


def _block_stage(row: dict[str, Any], reasons: Iterable[str]) -> None:
    row["status"] = "blocked-missing-input"
    row["blocking_reasons"] = list(dict.fromkeys(str(value) for value in reasons))


def _merge_fx_sources(
    rows: Iterable[tuple[str, bytes, Mapping[str, Any]]],
) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Merge FX sources only when duplicate normalized paths are byte-identical."""
    variants: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    payloads: dict[tuple[str, str], bytes] = {}
    occurrence_count = 0
    for raw_path, payload, provenance in rows:
        key = _norm(raw_path)
        if not key or not key.endswith(".fx"):
            continue
        occurrence_count += 1
        digest = hashlib.sha256(payload).hexdigest()
        variants[key].setdefault(
            digest,
            {
                "sha256": digest,
                "occurrences": [],
            },
        )["occurrences"].append(dict(provenance))
        payloads[(key, digest)] = payload

    conflicts = []
    sources: dict[str, bytes] = {}
    duplicate_equivalent_path_count = 0
    for key in sorted(variants):
        by_digest = variants[key]
        if len(by_digest) != 1:
            conflicts.append({
                "path": key,
                "distinct_sha256": sorted(by_digest),
                "variants": [by_digest[digest] for digest in sorted(by_digest)],
            })
            continue
        digest = next(iter(by_digest))
        sources[key] = payloads[(key, digest)]
        occurrence_total = len(by_digest[digest]["occurrences"])
        if occurrence_total > 1:
            duplicate_equivalent_path_count += 1

    summary = {
        "fx_occurrence_count": occurrence_count,
        "fx_normalized_path_count": len(variants),
        "fx_unique_source_count": len(sources),
        "fx_duplicate_equivalent_path_count": duplicate_equivalent_path_count,
        "fx_conflicting_path_count": len(conflicts),
        "fx_conflicts": conflicts,
    }
    if conflicts:
        names = ",".join(row["path"] for row in conflicts[:8])
        raise ValueError(f"conflicting-fx-source-paths:{names}")
    return sources, summary


def _build_material_support(
    corpus: list[str | Path],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]], dict[str, Any]]:
    fx_rows: list[tuple[str, bytes, Mapping[str, Any]]] = []
    reflection_index: dict[str, dict[str, Any]]
    archive_count = 0

    with ExitStack() as stack:
        paths = _materialize_bffs(corpus, stack)
        archives = [stack.enter_context(BFF(path)) for path in paths]
        archive_count = len(archives)
        for archive in archives:
            for entry in archive.entries:
                key = _norm(entry.path)
                if not key.endswith(".fx"):
                    continue
                try:
                    payload = archive.extract_entry(entry, type2="lzx")
                except Exception:
                    continue
                fx_rows.append((
                    entry.path,
                    payload,
                    {
                        "archive": archive.path.name,
                        "entry_index": int(entry.index),
                        "path": entry.path.replace("\\", "/"),
                    },
                ))
        fx_sources, fx_summary = _merge_fx_sources(fx_rows)
        reflection_index = _pixel_reflection_index(archives)

    occurrences = _build_material_occurrence_index(
        corpus,
        render_fx_sources=fx_sources,
    )
    summary = {
        **fx_summary,
        "archive_count": archive_count,
        "pixel_reflection_sha_count": len(reflection_index),
        "material_bmt_sha_count": len(occurrences),
        "material_occurrence_count": sum(len(rows) for rows in occurrences.values()),
    }
    return occurrences, reflection_index, summary


def run_ambiguity_regeneration(
    *,
    capture_jsonl: str | Path,
    runtime_shader_targets: str | Path,
    draw_local: str | Path,
    corpus: list[str | Path],
    output_dir: str | Path,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    capture_path = Path(capture_jsonl).expanduser()
    target_path = Path(runtime_shader_targets).expanduser()
    draw_path = Path(draw_local).expanduser()
    corpus_paths = [Path(value).expanduser() for value in corpus]

    inputs = {
        "capture_jsonl": _input_record(capture_path),
        "runtime_shader_targets": _input_record(target_path),
        "draw_local": _input_record(draw_path),
        "corpus": [_input_record(path) for path in corpus_paths],
    }
    blockers: list[str] = []
    if not capture_path.is_file():
        blockers.append(f"input:capture_jsonl:file-not-found:{capture_path}")
    if not target_path.is_file():
        blockers.append(f"input:runtime_shader_targets:file-not-found:{target_path}")
    if not draw_path.is_file():
        blockers.append(f"input:draw_local:file-not-found:{draw_path}")
    if not corpus_paths:
        blockers.append("input:corpus:no-inputs")
    for ordinal, path in enumerate(corpus_paths):
        if not path.is_file():
            blockers.append(f"input:corpus-{ordinal}:file-not-found:{path}")

    targets: Mapping[str, Any] | None = None
    draw_report: Mapping[str, Any] | None = None
    if target_path.is_file():
        try:
            targets = _load_json_map(target_path, TARGET_FORMAT)
        except Exception as exc:
            blockers.append(
                f"input:runtime_shader_targets:{type(exc).__name__}:{exc}"
            )
    if draw_path.is_file():
        try:
            draw_report = _load_json_map(draw_path, DRAW_LOCAL_FORMAT)
        except Exception as exc:
            blockers.append(f"input:draw_local:{type(exc).__name__}:{exc}")

    stage_specs = [
        ("phase603_runtime_catalog", 603),
        ("imb_corpus_audit", None),
        ("phase606_pipeline_candidates", 606),
        ("phase610_geometry_candidates", 610),
        ("phase611_material_candidates", 611),
        ("phase613_pointer_observations", 613),
        ("phase615_geometry_pointer_candidates", 615),
        ("phase617_draw_local_static_candidates", 617),
        ("phase618_ambiguity", 618),
    ]
    stages = {
        name: _stage_row(name, phase, out / OUTPUT_NAMES[name])
        for name, phase in stage_specs
    }
    reports: dict[str, Mapping[str, Any] | None] = {
        name: None for name, _ in stage_specs
    }
    material_support: dict[str, Any] | None = None

    initial_ready = not blockers and targets is not None and draw_report is not None
    if initial_ready:
        reports["phase603_runtime_catalog"] = _execute_stage(
            stages["phase603_runtime_catalog"],
            out / OUTPUT_NAMES["phase603_runtime_catalog"],
            lambda: _catalog_capture(capture_path, targets),
        )
        reports["imb_corpus_audit"] = _execute_stage(
            stages["imb_corpus_audit"],
            out / OUTPUT_NAMES["imb_corpus_audit"],
            lambda: audit_imb_corpus(corpus_paths),
        )
    else:
        _block_stage(stages["phase603_runtime_catalog"], ["validated-inputs-unavailable"])
        _block_stage(stages["imb_corpus_audit"], ["validated-inputs-unavailable"])

    catalog = reports["phase603_runtime_catalog"]
    corpus_audit = reports["imb_corpus_audit"]

    if catalog is None or targets is None:
        _block_stage(
            stages["phase606_pipeline_candidates"],
            ["phase603-runtime-catalog-unavailable"],
        )
    else:
        reports["phase606_pipeline_candidates"] = _execute_stage(
            stages["phase606_pipeline_candidates"],
            out / OUTPUT_NAMES["phase606_pipeline_candidates"],
            lambda: build_runtime_pipeline_candidate_join(catalog, targets),
        )

    if catalog is None or targets is None:
        _block_stage(
            stages["phase613_pointer_observations"],
            ["phase603-runtime-catalog-unavailable"],
        )
    else:
        reports["phase613_pointer_observations"] = _execute_stage(
            stages["phase613_pointer_observations"],
            out / OUTPUT_NAMES["phase613_pointer_observations"],
            lambda: _pointer_capture(capture_path, targets, catalog),
        )

    pipeline_join = reports["phase606_pipeline_candidates"]
    if catalog is None or pipeline_join is None or corpus_audit is None:
        missing = []
        if catalog is None:
            missing.append("phase603-runtime-catalog-unavailable")
        if pipeline_join is None:
            missing.append("phase606-pipeline-candidates-unavailable")
        if corpus_audit is None:
            missing.append("imb-corpus-audit-unavailable")
        _block_stage(stages["phase610_geometry_candidates"], missing)
    else:
        reports["phase610_geometry_candidates"] = _execute_stage(
            stages["phase610_geometry_candidates"],
            out / OUTPUT_NAMES["phase610_geometry_candidates"],
            lambda: build_runtime_geometry_shape_candidate_join(
                catalog,
                pipeline_join,
                corpus_audit,
            ),
        )

    geometry_join = reports["phase610_geometry_candidates"]
    if catalog is None or geometry_join is None:
        _block_stage(
            stages["phase611_material_candidates"],
            [
                reason
                for reason, missing in (
                    ("phase603-runtime-catalog-unavailable", catalog is None),
                    ("phase610-geometry-candidates-unavailable", geometry_join is None),
                )
                if missing
            ],
        )
    else:
        support_holder: dict[str, Any] = {}

        def build_material_stage() -> Mapping[str, Any]:
            occurrences, reflections, summary = _build_material_support(corpus_paths)
            support_holder.update(summary)
            return build_runtime_material_descriptor_candidate_join(
                catalog,
                geometry_join,
                material_occurrences=occurrences,
                pixel_reflections=reflections,
            )

        reports["phase611_material_candidates"] = _execute_stage(
            stages["phase611_material_candidates"],
            out / OUTPUT_NAMES["phase611_material_candidates"],
            build_material_stage,
        )
        material_support = support_holder or None

    pointer_report = reports["phase613_pointer_observations"]
    material_join = reports["phase611_material_candidates"]
    if pointer_report is None or material_join is None:
        missing = []
        if pointer_report is None:
            missing.append("phase613-pointer-observations-unavailable")
        if material_join is None:
            missing.append("phase611-material-candidates-unavailable")
        _block_stage(stages["phase615_geometry_pointer_candidates"], missing)
    else:
        reports["phase615_geometry_pointer_candidates"] = _execute_stage(
            stages["phase615_geometry_pointer_candidates"],
            out / OUTPUT_NAMES["phase615_geometry_pointer_candidates"],
            lambda: build_runtime_geometry_pointer_candidate_join(
                pointer_report,
                material_join,
            ),
        )

    geometry_pointer_join = reports["phase615_geometry_pointer_candidates"]
    if draw_report is None or geometry_pointer_join is None:
        missing = []
        if draw_report is None:
            missing.append("draw-local-unavailable")
        if geometry_pointer_join is None:
            missing.append("phase615-geometry-pointer-candidates-unavailable")
        _block_stage(stages["phase617_draw_local_static_candidates"], missing)
    else:
        reports["phase617_draw_local_static_candidates"] = _execute_stage(
            stages["phase617_draw_local_static_candidates"],
            out / OUTPUT_NAMES["phase617_draw_local_static_candidates"],
            lambda: build_draw_local_static_candidate_join(
                draw_report,
                geometry_pointer_join,
            ),
        )

    static_join = reports["phase617_draw_local_static_candidates"]
    if static_join is None:
        _block_stage(
            stages["phase618_ambiguity"],
            ["phase617-draw-local-static-candidates-unavailable"],
        )
    else:
        reports["phase618_ambiguity"] = _execute_stage(
            stages["phase618_ambiguity"],
            out / OUTPUT_NAMES["phase618_ambiguity"],
            lambda: build_draw_local_ambiguity_audit(static_join),
        )

    for name, row in stages.items():
        if row["status"].startswith("blocked"):
            blockers.extend(
                f"{name}:{reason}" for reason in row["blocking_reasons"]
            )

    ambiguity = reports["phase618_ambiguity"]
    if isinstance(ambiguity, Mapping) and ambiguity.get("format") != AMBIGUITY_FORMAT:
        blockers.append(
            f"phase618_ambiguity:format-mismatch:{ambiguity.get('format')!r}"
        )

    blockers = list(dict.fromkeys(str(value) for value in blockers))
    ready = (
        isinstance(ambiguity, Mapping)
        and ambiguity.get("format") == AMBIGUITY_FORMAT
        and not blockers
    )
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
                row["status"].startswith("blocked") for row in stages.values()
            ),
            "phase618_available": ambiguity is not None,
            "blocking_reason_count": len(blockers),
        },
        "inputs": inputs,
        "stages": list(stages.values()),
        "outputs": {
            name: (
                str(out / OUTPUT_NAMES[name])
                if reports[name] is not None
                else None
            )
            for name, _ in stage_specs
        },
        "material_support": material_support,
        "blocking_reasons": blockers,
        "boundary": {
            "source_graph": (
                "historical raw D3D9 JSONL + exact shader targets + draw-local "
                "+ BFF/ZIP corpus"
            ),
            "fx_duplicate_path_policy": "byte-identical duplicates only",
            "fx_conflicting_path_selects_winner": False,
            "candidate_ranking_is_proof": False,
            "pointer_identity_is_portable_resource_identity": False,
            "descriptor_match_is_render_admission": False,
            "single_candidate_is_render_admission": False,
            "original_game_execution_required": False,
            "new_capture_required": False,
        },
    }
    _write_json_atomic(
        out / "silverstone_renderer_ambiguity_regeneration.json",
        manifest,
    )
    return manifest


def _catalog_capture(
    capture_path: Path,
    targets: Mapping[str, Any],
) -> Mapping[str, Any]:
    with capture_path.open("r", encoding="utf-8") as stream:
        return catalog_target_draw_signatures(stream, target_inventory=targets)


def _pointer_capture(
    capture_path: Path,
    targets: Mapping[str, Any],
    catalog: Mapping[str, Any],
) -> Mapping[str, Any]:
    with capture_path.open("r", encoding="utf-8") as stream:
        return build_target_pointer_observations(
            stream,
            target_inventory=targets,
            target_catalog=catalog,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-jsonl", required=True)
    parser.add_argument("--runtime-shader-targets", required=True)
    parser.add_argument("--draw-local", required=True)
    parser.add_argument("--corpus", action="append", default=[])
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    manifest = run_ambiguity_regeneration(
        capture_jsonl=args.capture_jsonl,
        runtime_shader_targets=args.runtime_shader_targets,
        draw_local=args.draw_local,
        corpus=args.corpus,
        output_dir=args.output_dir,
    )
    print(json.dumps({
        "format": manifest["format"],
        "status": manifest["status"],
        "summary": manifest["summary"],
        "blocking_reasons": manifest["blocking_reasons"],
        "phase618": manifest["outputs"]["phase618_ambiguity"],
        "manifest": str(
            Path(args.output_dir)
            / "silverstone_renderer_ambiguity_regeneration.json"
        ),
    }, ensure_ascii=False, indent=2))
    return 0 if manifest["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
