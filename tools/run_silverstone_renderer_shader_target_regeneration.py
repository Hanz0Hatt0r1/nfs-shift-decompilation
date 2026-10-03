#!/usr/bin/env python3
"""Regenerate the full Silverstone runtime shader target set from source corpus.

This stage reuses the source-backed material/shader ranking and target-set
builders. It preserves every complete tied top-rank candidate set and never
selects a retail permutation by filename, frequency or ordering.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

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

from audit_imb_material_shader_ranking import audit_imb_material_shader_ranking
from imb_runtime_shader_target_set import build_imb_runtime_shader_target_set

FORMAT = "SHIFT.SilverstoneRendererShaderTargetRegeneration/1"
RANKING_FORMAT = "SHIFT.IMBMaterialShaderRanking/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"
COMPACT_FORMAT = "SHIFT.IMBRuntimeShaderTargetSetEvidence/1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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


def _input_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "present": path.is_file(),
        "size": path.stat().st_size if path.is_file() else None,
        "sha256": _sha256_file(path) if path.is_file() else None,
    }


def _load_json_map(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"JSON object expected: {path}")
    return value


def _compact_projection_from_full(
    ranking: Mapping[str, Any],
    target_set: Mapping[str, Any],
) -> dict[str, Any]:
    bindings = [
        row for row in (target_set.get("binding_targets") or [])
        if isinstance(row, Mapping)
    ]
    unique_targets = [
        row for row in (target_set.get("unique_targets") or [])
        if isinstance(row, Mapping)
    ]

    distribution = Counter(
        str(int(row.get("hash_target_count") or 0))
        for row in bindings
    )
    kind_counts = Counter(
        str(row.get("identity_kind") or "")
        for row in unique_targets
        if row.get("identity_kind")
    )

    family_pixels: dict[str, set[str]] = defaultdict(set)
    for row in unique_targets:
        families = [str(value) for value in (row.get("shader_families") or []) if value]
        pixel = row.get("pixel_byte_sha256")
        if not isinstance(pixel, str) or len(pixel) != 64:
            continue
        for family in families:
            family_pixels[family].add(pixel.lower())

    families = [
        {
            "family": family,
            "pixel_shader_sha256": sorted(values),
            "pixel_target_count": len(values),
        }
        for family, values in sorted(family_pixels.items())
    ]

    return {
        "source_ranking": {
            "primitive_binding_count": int(ranking.get("primitive_binding_count") or 0),
            "unique_rank_context_count": int(ranking.get("unique_rank_context_count") or 0),
            "selection_status_counts": dict(ranking.get("selection_status_counts") or {}),
        },
        "result": {
            "binding_target_count": len(bindings),
            "capture_ready_binding_count": sum(
                row.get("capture_ready") is True for row in bindings
            ),
            "attribution_ready_binding_count": sum(
                row.get("attribution_ready") is True for row in bindings
            ),
            "unique_hash_target_count": len(unique_targets),
            "strong_hash_target_count": sum(
                row.get("strength") == "exact-pair" for row in unique_targets
            ),
            "prefilter_only_target_count": sum(
                row.get("strength") == "prefilter-only" for row in unique_targets
            ),
            "target_kind_counts": dict(sorted(kind_counts.items())),
            "binding_hash_target_count_distribution": dict(
                sorted(distribution.items(), key=lambda item: int(item[0]))
            ),
        },
        "families": families,
        "boundary": {
            "all_bindings_capture_ready": (
                bool(bindings)
                and all(row.get("capture_ready") is True for row in bindings)
            ),
            "all_bindings_exact_pair_attribution_ready": (
                bool(bindings)
                and all(row.get("attribution_ready") is True for row in bindings)
            ),
            "selects_permutation": False,
        },
    }


def _compact_projection_from_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("format") != COMPACT_FORMAT:
        raise ValueError(
            f"compact evidence must be {COMPACT_FORMAT}, got {value.get('format')!r}"
        )
    source = value.get("source_ranking")
    result = value.get("result")
    boundary = value.get("boundary")
    if not isinstance(source, Mapping) or not isinstance(result, Mapping):
        raise ValueError("compact evidence missing source_ranking/result")
    boundary = boundary if isinstance(boundary, Mapping) else {}

    families = []
    for row in value.get("families") or []:
        if not isinstance(row, Mapping):
            continue
        hashes = sorted({
            str(item).lower()
            for item in (row.get("pixel_shader_sha256") or [])
            if isinstance(item, str) and len(item) == 64
        })
        families.append({
            "family": str(row.get("family") or ""),
            "pixel_shader_sha256": hashes,
            "pixel_target_count": len(hashes),
        })
    families.sort(key=lambda row: row["family"])

    fields = (
        "binding_target_count",
        "capture_ready_binding_count",
        "attribution_ready_binding_count",
        "unique_hash_target_count",
        "strong_hash_target_count",
        "prefilter_only_target_count",
    )
    return {
        "source_ranking": {
            "primitive_binding_count": int(source.get("primitive_binding_count") or 0),
            "unique_rank_context_count": int(source.get("unique_rank_context_count") or 0),
            "selection_status_counts": dict(source.get("selection_status_counts") or {}),
        },
        "result": {
            **{field: int(result.get(field) or 0) for field in fields},
            "target_kind_counts": dict(result.get("target_kind_counts") or {}),
            "binding_hash_target_count_distribution": dict(
                result.get("binding_hash_target_count_distribution") or {}
            ),
        },
        "families": families,
        "boundary": {
            "all_bindings_capture_ready": (
                boundary.get("all_bindings_capture_ready") is True
            ),
            "all_bindings_exact_pair_attribution_ready": (
                boundary.get("all_bindings_exact_pair_attribution_ready") is True
            ),
            "selects_permutation": boundary.get("selects_permutation") is True,
        },
    }


def regenerate_full_shader_target_set(
    *,
    corpus: list[str | Path],
    output_dir: str | Path,
    compact_evidence: str | Path | None = None,
    max_imb_per_archive: int = 0,
) -> dict[str, Any]:
    if max_imb_per_archive < 0:
        raise ValueError("max_imb_per_archive must be non-negative")

    out = Path(output_dir)
    ranking_path = out / "silverstone_imb_material_shader_ranking.json"
    target_path = out / "silverstone_imb_runtime_shader_target_set.json"
    compact_projection_path = out / "silverstone_runtime_shader_target_projection.json"

    corpus_paths = [Path(value).expanduser() for value in corpus]
    blockers: list[str] = []
    if not corpus_paths:
        blockers.append("input:corpus:no-inputs")
    for ordinal, path in enumerate(corpus_paths):
        if not path.is_file():
            blockers.append(f"input:corpus-{ordinal}:file-not-found:{path}")

    ranking: Mapping[str, Any] | None = None
    target_set: Mapping[str, Any] | None = None
    ranking_sha: str | None = None
    target_sha: str | None = None
    projection_sha: str | None = None
    projection: Mapping[str, Any] | None = None

    if not blockers:
        try:
            ranking = audit_imb_material_shader_ranking(
                corpus_paths,
                max_imb_per_archive=max_imb_per_archive,
            )
            if ranking.get("format") != RANKING_FORMAT:
                raise ValueError(
                    f"ranking format mismatch: {ranking.get('format')!r}"
                )
            ranking_sha = _write_json_atomic(ranking_path, ranking)
        except Exception as exc:
            blockers.append(f"ranking:failed:{type(exc).__name__}:{exc}")
            ranking = None

    if ranking is not None:
        try:
            target_set = build_imb_runtime_shader_target_set(ranking)
            if target_set.get("format") != TARGET_FORMAT:
                raise ValueError(
                    f"target format mismatch: {target_set.get('format')!r}"
                )
            target_sha = _write_json_atomic(target_path, target_set)
            projection = _compact_projection_from_full(ranking, target_set)
            projection_sha = _write_json_atomic(compact_projection_path, projection)
        except Exception as exc:
            blockers.append(f"target_set:failed:{type(exc).__name__}:{exc}")
            target_set = None

    compact_record: dict[str, Any] | None = None
    if compact_evidence is not None:
        compact_path = Path(compact_evidence).expanduser()
        compact_record = _input_record(compact_path)
        compact_record.update({
            "expected_format": COMPACT_FORMAT,
            "projection_status": None,
            "expected_projection_sha256": None,
            "regenerated_projection_sha256": (
                _canonical_sha(projection) if projection is not None else None
            ),
        })
        if not compact_path.is_file():
            blockers.append(f"compact_evidence:file-not-found:{compact_path}")
        elif projection is not None:
            try:
                compact_value = _load_json_map(compact_path)
                expected_projection = _compact_projection_from_evidence(compact_value)
                expected_sha = _canonical_sha(expected_projection)
                regenerated_sha = _canonical_sha(projection)
                compact_record["format"] = compact_value.get("format")
                compact_record["expected_projection_sha256"] = expected_sha
                if expected_sha == regenerated_sha:
                    compact_record["projection_status"] = "exact-semantic-projection-match"
                else:
                    compact_record["projection_status"] = "semantic-projection-mismatch"
                    blockers.append(
                        "compact_evidence:semantic-projection-mismatch"
                    )
            except Exception as exc:
                compact_record["projection_status"] = "unreadable-or-invalid"
                blockers.append(
                    f"compact_evidence:failed:{type(exc).__name__}:{exc}"
                )

    capture_ready = (
        isinstance(target_set, Mapping)
        and target_set.get("capture_ready") is True
        and int(target_set.get("binding_target_count") or 0) > 0
    )
    if target_set is not None and not capture_ready:
        blockers.append("target_set:not-capture-ready")

    blockers = list(dict.fromkeys(str(value) for value in blockers))
    ready = capture_ready and not blockers
    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": "completed" if ready else "blocked",
        "ready": ready,
        "summary": {
            "corpus_input_count": len(corpus_paths),
            "ranking_available": ranking is not None,
            "target_set_available": target_set is not None,
            "target_set_capture_ready": capture_ready,
            "binding_target_count": (
                int(target_set.get("binding_target_count") or 0)
                if isinstance(target_set, Mapping)
                else 0
            ),
            "unique_hash_target_count": (
                int(target_set.get("unique_hash_target_count") or 0)
                if isinstance(target_set, Mapping)
                else 0
            ),
            "compact_crosscheck_requested": compact_evidence is not None,
            "compact_crosscheck_match": (
                isinstance(compact_record, Mapping)
                and compact_record.get("projection_status")
                == "exact-semantic-projection-match"
            ),
            "blocking_reason_count": len(blockers),
        },
        "inputs": {
            "corpus": [_input_record(path) for path in corpus_paths],
            "compact_evidence": compact_record,
            "max_imb_per_archive": max_imb_per_archive,
        },
        "outputs": {
            "ranking": str(ranking_path) if ranking is not None else None,
            "runtime_shader_targets": str(target_path) if target_set is not None else None,
            "compact_projection": (
                str(compact_projection_path) if projection is not None else None
            ),
        },
        "output_sha256": {
            "ranking": ranking_sha,
            "runtime_shader_targets": target_sha,
            "compact_projection": projection_sha,
        },
        "blocking_reasons": blockers,
        "boundary": {
            "ranking_preserves_tied_top_candidates": True,
            "ranking_or_file_order_selects_permutation": False,
            "runtime_target_set_preserves_candidate_variants": True,
            "compact_phase568_evidence_is_reconstruction_source": False,
            "compact_phase568_evidence_is_projection_crosscheck_only": True,
            "target_set_required_for_phase606": TARGET_FORMAT,
            "original_game_execution_required": False,
            "new_capture_required": False,
        },
    }
    _write_json_atomic(
        out / "silverstone_renderer_shader_target_regeneration.json",
        manifest,
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", action="append", default=[])
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--compact-evidence")
    parser.add_argument("--max-imb-per-archive", type=int, default=0)
    args = parser.parse_args(argv)

    manifest = regenerate_full_shader_target_set(
        corpus=args.corpus,
        output_dir=args.output_dir,
        compact_evidence=args.compact_evidence,
        max_imb_per_archive=args.max_imb_per_archive,
    )
    print(json.dumps({
        "format": manifest["format"],
        "status": manifest["status"],
        "summary": manifest["summary"],
        "blocking_reasons": manifest["blocking_reasons"],
        "runtime_shader_targets": manifest["outputs"]["runtime_shader_targets"],
        "manifest": str(
            Path(args.output_dir)
            / "silverstone_renderer_shader_target_regeneration.json"
        ),
    }, ensure_ascii=False, indent=2))
    return 0 if manifest["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
