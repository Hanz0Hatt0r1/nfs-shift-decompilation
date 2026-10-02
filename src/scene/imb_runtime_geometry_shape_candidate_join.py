"""Correlate D3D9 target geometry resource shapes to static IMB content.

Phase 610 operates below the pipeline aggregation used by
SHIFT.IMBRuntimePipelineCandidateJoin/1.  It removes texture descriptors and
transient instance-stream offsets from runtime resource shapes, then correlates
each stable stream-0/index-buffer geometry descriptor with archive-invariant
static IMB content groups.

The result is candidate-only evidence.  Descriptor equality is not runtime
resource identity and never bypasses the existing Phase 572/574 admission
gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.IMBRuntimeGeometryShapeCandidateJoin/1"
RUNTIME_FORMAT = "SHIFT.D3D9TargetDrawSignatureCatalog/1"
PIPELINE_FORMAT = "SHIFT.IMBRuntimePipelineCandidateJoin/1"
CORPUS_FORMAT = "SHIFT.IMBCorpusAudit/1"

_INDEX_BYTE_WIDTH = {
    101: 2,  # D3DFMT_INDEX16
    102: 4,  # D3DFMT_INDEX32
}


def _valid_sha(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _canonical_hash(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def resolve_input_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate
    repo_root = Path(__file__).resolve().parents[2]
    repo_candidate = repo_root / candidate
    if repo_candidate.exists():
        return repo_candidate
    raise FileNotFoundError(
        f"input file not found: {candidate} "
        f"(also tried {repo_candidate})"
    )


def _pipeline_payload(signature: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "vertex_shader_sha256": signature.get("vertex_shader_sha256"),
        "pixel_shader_sha256": signature.get("pixel_shader_sha256"),
        "declaration_sha256": signature.get("declaration_sha256"),
        "stream_layout": list(signature.get("stream_layout") or []),
        "index_format": signature.get("index_format"),
    }


def _stream0_shape(signature: Mapping[str, Any]) -> dict[str, Any]:
    for row in signature.get("stream_resource_shapes") or []:
        if not isinstance(row, Mapping):
            continue
        try:
            stream = int(row.get("stream"))
        except (TypeError, ValueError):
            continue
        if stream != 0:
            continue
        return {
            "stream": 0,
            "length": row.get("length"),
            "stride": row.get("stride"),
            "usage": row.get("usage"),
            "fvf": row.get("fvf"),
            "pool": row.get("pool"),
        }
    return {}


def _index_shape(signature: Mapping[str, Any]) -> dict[str, Any]:
    source = signature.get("index_resource_shape")
    if not isinstance(source, Mapping):
        return {}
    return {
        "length": source.get("length"),
        "format": source.get("format"),
        "usage": source.get("usage"),
        "pool": source.get("pool"),
    }


def _observed_draw_ranges(
    row: Mapping[str, Any],
) -> list[dict[str, int]]:
    ranges: set[tuple[int, int]] = set()
    source = row.get("observed_draw_ranges")
    if not isinstance(source, list) or not source:
        top = row.get("top_draw_ranges")
        distinct = row.get("distinct_draw_range_count")
        if (
            isinstance(top, list)
            and isinstance(distinct, int)
            and distinct == len(top)
        ):
            source = top
        else:
            source = []

    for value in source:
        if not isinstance(value, Mapping):
            continue
        try:
            start_index = int(value.get("start_index"))
            primitive_count = int(value.get("primitive_count"))
        except (TypeError, ValueError):
            continue
        if start_index < 0 or primitive_count < 0:
            continue
        ranges.add((start_index, primitive_count))
    return [
        {
            "start_index": start_index,
            "primitive_count": primitive_count,
        }
        for start_index, primitive_count in sorted(ranges)
    ]


def _runtime_vertex_count(
    stream0: Mapping[str, Any],
) -> int | None:
    try:
        length = int(stream0.get("length"))
        stride = int(stream0.get("stride"))
    except (TypeError, ValueError):
        return None
    if length <= 0 or stride <= 0 or length % stride:
        return None
    return length // stride


def _runtime_index_count(
    index_shape: Mapping[str, Any],
) -> tuple[int | None, int | None]:
    try:
        length = int(index_shape.get("length"))
        fmt = int(index_shape.get("format"))
    except (TypeError, ValueError):
        return None, None
    width = _INDEX_BYTE_WIDTH.get(fmt)
    if width is None or length <= 0 or length % width:
        return None, width
    return length // width, width


def _corpus_geometry_index(
    corpus: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    variants: dict[str, set[tuple[int, int, int]]] = defaultdict(set)
    for row in corpus.get("rows") or []:
        if not isinstance(row, Mapping) or row.get("ready") is not True:
            continue
        digest = _valid_sha(row.get("decoded_sha256"))
        if not digest:
            continue
        try:
            vertex_count = int(row.get("vertex_count"))
            primitive_count = int(row.get("primitive_count"))
            triangle_count = int(row.get("triangle_count"))
        except (TypeError, ValueError):
            continue
        if vertex_count <= 0 or primitive_count <= 0 or triangle_count <= 0:
            continue
        variants[digest].add(
            (vertex_count, primitive_count, triangle_count)
        )

    result: dict[str, dict[str, Any]] = {}
    for digest, rows in variants.items():
        if len(rows) != 1:
            result[digest] = {
                "consistent": False,
                "variant_count": len(rows),
            }
            continue
        vertex_count, primitive_count, triangle_count = next(iter(rows))
        result[digest] = {
            "consistent": True,
            "vertex_count": vertex_count,
            "primitive_count": primitive_count,
            "triangle_count": triangle_count,
            "index_count": triangle_count * 3,
        }
    return result


def _group_matches_ranges(
    group: Mapping[str, Any],
    ranges: list[dict[str, int]],
) -> bool:
    if not ranges:
        return True
    draw_range = group.get("draw_range")
    if not isinstance(draw_range, Mapping):
        return False
    try:
        first_index = int(draw_range.get("first_index"))
        primitive_count = int(draw_range.get("primitive_count"))
    except (TypeError, ValueError):
        return False
    return any(
        first_index == row["start_index"]
        and primitive_count == row["primitive_count"]
        for row in ranges
    )


def _enrich_group(
    group: Mapping[str, Any],
    *,
    corpus_index: Mapping[str, Mapping[str, Any]],
    runtime_vertex_count: int | None,
    runtime_index_count: int | None,
) -> dict[str, Any]:
    row = dict(group)
    digest = _valid_sha(group.get("imb_sha256"))
    source = corpus_index.get(digest or "")
    row["source_geometry_status"] = (
        "consistent"
        if isinstance(source, Mapping)
        and source.get("consistent") is True
        else "unavailable-or-inconsistent"
    )
    if row["source_geometry_status"] != "consistent":
        row["source_vertex_count"] = None
        row["source_primitive_record_count"] = None
        row["source_triangle_count"] = None
        row["source_index_count"] = None
        row["descriptor_match_complete"] = False
        row["vertex_buffer_exact_fit"] = False
        row["index_buffer_exact_fit"] = False
        row["descriptor_geometry_match"] = False
        return row

    source_vertex_count = int(source["vertex_count"])
    source_primitive_count = int(source["primitive_count"])
    source_triangle_count = int(source["triangle_count"])
    source_index_count = int(source["index_count"])
    row["source_vertex_count"] = source_vertex_count
    row["source_primitive_record_count"] = source_primitive_count
    row["source_triangle_count"] = source_triangle_count
    row["source_index_count"] = source_index_count

    draw_range = group.get("draw_range")
    full_mesh_draw = False
    if isinstance(draw_range, Mapping):
        try:
            first_index = int(draw_range.get("first_index"))
            index_count = int(draw_range.get("index_count"))
        except (TypeError, ValueError):
            pass
        else:
            full_mesh_draw = (
                first_index == 0
                and index_count == source_index_count
            )

    vertex_exact = (
        runtime_vertex_count is not None
        and runtime_vertex_count == source_vertex_count
    )
    index_exact = (
        runtime_index_count is not None
        and full_mesh_draw
        and runtime_index_count == source_index_count
    )
    complete = (
        runtime_vertex_count is not None
        and runtime_index_count is not None
        and full_mesh_draw
    )
    row["full_mesh_draw"] = full_mesh_draw
    row["descriptor_match_complete"] = complete
    row["vertex_buffer_exact_fit"] = vertex_exact
    row["index_buffer_exact_fit"] = index_exact
    row["descriptor_geometry_match"] = (
        complete and vertex_exact and index_exact
    )
    return row


def build_runtime_geometry_shape_candidate_join(
    runtime_catalog: Mapping[str, Any],
    pipeline_join: Mapping[str, Any],
    corpus_audit: Mapping[str, Any],
) -> dict[str, Any]:
    if runtime_catalog.get("format") != RUNTIME_FORMAT:
        raise ValueError(
            "runtime catalog must be "
            "SHIFT.D3D9TargetDrawSignatureCatalog/1"
        )
    if pipeline_join.get("format") != PIPELINE_FORMAT:
        raise ValueError(
            "pipeline join must be "
            "SHIFT.IMBRuntimePipelineCandidateJoin/1"
        )
    if corpus_audit.get("format") != CORPUS_FORMAT:
        raise ValueError(
            "corpus audit must be SHIFT.IMBCorpusAudit/1"
        )

    pipeline_candidates = {
        str(row.get("runtime_signature_sha256") or ""): row
        for row in (pipeline_join.get("pipeline_candidates") or [])
        if isinstance(row, Mapping)
        and row.get("runtime_signature_sha256")
    }
    corpus_index = _corpus_geometry_index(corpus_audit)

    raw_geometry: dict[str, dict[str, Any]] = {}
    for shape in runtime_catalog.get("resource_shape_signatures") or []:
        if not isinstance(shape, Mapping):
            continue
        signature = shape.get("signature")
        if not isinstance(signature, Mapping):
            continue

        pipeline = _pipeline_payload(signature)
        pipeline_sha = _canonical_hash(pipeline)
        stream0 = _stream0_shape(signature)
        index_shape = _index_shape(signature)
        ranges = _observed_draw_ranges(shape)
        geometry_signature = {
            "pipeline_signature_sha256": pipeline_sha,
            "stream0_resource_shape": stream0,
            "index_resource_shape": index_shape,
            "observed_draw_ranges": ranges,
        }
        geometry_sha = _canonical_hash(geometry_signature)
        row = raw_geometry.setdefault(geometry_sha, {
            "geometry_shape_sha256": geometry_sha,
            "geometry_signature": geometry_signature,
            "pipeline_signature_sha256": pipeline_sha,
            "resource_shape_sha256s": [],
            "resource_shape_count": 0,
            "draw_count": 0,
            "primitive_count_sum": 0,
            "first_frame": shape.get("first_frame"),
            "last_frame": shape.get("last_frame"),
            "families": set(),
        })
        resource_sha = _valid_sha(shape.get("signature_sha256"))
        if (
            resource_sha
            and resource_sha not in row["resource_shape_sha256s"]
        ):
            row["resource_shape_sha256s"].append(resource_sha)
        row["resource_shape_count"] += 1
        row["draw_count"] += int(shape.get("draw_count") or 0)
        row["primitive_count_sum"] += int(
            shape.get("primitive_count_sum") or 0
        )
        first_frame = shape.get("first_frame")
        last_frame = shape.get("last_frame")
        if isinstance(first_frame, int):
            if not isinstance(row["first_frame"], int):
                row["first_frame"] = first_frame
            else:
                row["first_frame"] = min(
                    int(row["first_frame"]), first_frame
                )
        if isinstance(last_frame, int):
            if not isinstance(row["last_frame"], int):
                row["last_frame"] = last_frame
            else:
                row["last_frame"] = max(
                    int(row["last_frame"]), last_frame
                )
        row["families"].update(
            str(value)
            for value in (shape.get("families") or [])
            if value
        )

    rows: list[dict[str, Any]] = []
    descriptor_gate_status_counts: Counter[str] = Counter()
    single_content_shape_count = 0
    single_content_draw_count = 0
    linked_shape_count = 0
    descriptor_gate_applied_count = 0
    descriptor_gate_reduced_count = 0
    descriptor_gate_fallback_count = 0
    distinct_content_groups: set[str] = set()

    for source in raw_geometry.values():
        row = dict(source)
        row["families"] = sorted(row["families"])
        row["resource_shape_sha256s"].sort()
        geometry_signature = row["geometry_signature"]
        stream0 = geometry_signature["stream0_resource_shape"]
        index_shape = geometry_signature["index_resource_shape"]
        ranges = geometry_signature["observed_draw_ranges"]
        runtime_vertex_count = _runtime_vertex_count(stream0)
        runtime_index_count, index_byte_width = _runtime_index_count(
            index_shape
        )

        pipeline_row = pipeline_candidates.get(
            str(row["pipeline_signature_sha256"])
        )
        base_groups = (
            [
                dict(value)
                for value in (
                    pipeline_row.get("candidate_content_groups") or []
                )
                if isinstance(value, Mapping)
            ]
            if isinstance(pipeline_row, Mapping)
            else []
        )
        range_groups = [
            group
            for group in base_groups
            if _group_matches_ranges(group, ranges)
        ]
        enriched = [
            _enrich_group(
                group,
                corpus_index=corpus_index,
                runtime_vertex_count=runtime_vertex_count,
                runtime_index_count=runtime_index_count,
            )
            for group in range_groups
        ]
        exact_descriptor = [
            group
            for group in enriched
            if group.get("descriptor_geometry_match") is True
        ]
        complete_descriptor = [
            group
            for group in enriched
            if group.get("descriptor_match_complete") is True
        ]

        if exact_descriptor:
            candidates = exact_descriptor
            descriptor_gate_applied_count += 1
            if len(candidates) < len(enriched):
                descriptor_gate_reduced_count += 1
                gate_status = "reduced"
            else:
                gate_status = "matched-all"
        else:
            candidates = enriched
            if complete_descriptor:
                descriptor_gate_fallback_count += 1
                gate_status = "no-exact-match-fallback"
            else:
                gate_status = "not-applied"

        descriptor_gate_status_counts[gate_status] += 1
        if isinstance(pipeline_row, Mapping):
            linked_shape_count += 1

        candidate_hashes = sorted({
            str(group.get("content_group_sha256"))
            for group in candidates
            if group.get("content_group_sha256")
        })
        distinct_content_groups.update(candidate_hashes)

        if len(candidate_hashes) == 1:
            candidate_status = "single-content-candidate"
            single_content_shape_count += 1
            single_content_draw_count += int(row["draw_count"])
        elif candidate_hashes:
            candidate_status = "ambiguous-content-candidates"
        elif not base_groups:
            candidate_status = "no-pipeline-content-candidates"
        else:
            candidate_status = "no-range-content-candidates"

        row.update({
            "runtime_vertex_count": runtime_vertex_count,
            "runtime_index_count": runtime_index_count,
            "runtime_index_byte_width": index_byte_width,
            "pipeline_candidate_status": (
                pipeline_row.get("candidate_content_status")
                if isinstance(pipeline_row, Mapping)
                else None
            ),
            "base_pipeline_content_group_count": len(base_groups),
            "range_candidate_content_group_count": len(range_groups),
            "descriptor_gate_status": gate_status,
            "candidate_content_status": candidate_status,
            "candidate_content_group_count": len(candidate_hashes),
            "candidate_content_group_sha256s": candidate_hashes,
            "candidate_content_groups": candidates,
        })
        rows.append(row)

    rows.sort(
        key=lambda row: (
            -int(row.get("draw_count") or 0),
            str(row.get("geometry_shape_sha256") or ""),
        )
    )
    runtime_draw_count = sum(
        int(row.get("draw_count") or 0)
        for row in rows
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "observed" if rows else "not-observed",
        "summary": {
            "runtime_resource_shape_signature_count": len(
                runtime_catalog.get("resource_shape_signatures") or []
            ),
            "runtime_geometry_shape_count": len(rows),
            "runtime_geometry_shape_draw_count": runtime_draw_count,
            "pipeline_linked_geometry_shape_count": linked_shape_count,
            "descriptor_gate_applied_geometry_shape_count": (
                descriptor_gate_applied_count
            ),
            "descriptor_gate_reduced_geometry_shape_count": (
                descriptor_gate_reduced_count
            ),
            "descriptor_gate_fallback_geometry_shape_count": (
                descriptor_gate_fallback_count
            ),
            "single_content_candidate_geometry_shape_count": (
                single_content_shape_count
            ),
            "single_content_candidate_draw_count": (
                single_content_draw_count
            ),
            "distinct_candidate_content_group_count": len(
                distinct_content_groups
            ),
            "descriptor_gate_status_counts": dict(
                sorted(descriptor_gate_status_counts.items())
            ),
            "corpus_geometry_sha_count": len(corpus_index),
        },
        "geometry_shapes": rows,
        "boundary": {
            "candidate_only": True,
            "render_admission": False,
            "runtime_resource_identity": "not evaluated",
            "runtime_pointer_identity": "not preserved",
            "geometry_shape_identity": (
                "pipeline + stream-0 buffer descriptor + index-buffer "
                "descriptor + complete observed draw-range set; texture "
                "descriptors are intentionally excluded"
            ),
            "descriptor_gate": (
                "source IMB vertex/index counts may narrow candidates only "
                "when the runtime descriptors are exact-fit and at least one "
                "candidate matches; otherwise the range-matched set is kept"
            ),
            "single_content_candidate": (
                "one archive-invariant static IMB content contract matches "
                "the observed geometry shape; this is not runtime archive, "
                "resource-pointer or same-instance identity"
            ),
            "required_for_promotion": (
                "exact runtime IMB resource identity + exact primitive "
                "draw range + existing Phase 572 strong match gates"
            ),
        },
    }


def validate_files(
    runtime_catalog_path: str | Path,
    pipeline_join_path: str | Path,
    corpus_audit_path: str | Path,
) -> dict[str, Any]:
    runtime = json.loads(
        resolve_input_path(runtime_catalog_path).read_text(
            encoding="utf-8"
        )
    )
    pipeline = json.loads(
        resolve_input_path(pipeline_join_path).read_text(
            encoding="utf-8"
        )
    )
    corpus = json.loads(
        resolve_input_path(corpus_audit_path).read_text(
            encoding="utf-8"
        )
    )
    if not all(isinstance(value, dict) for value in (
        runtime,
        pipeline,
        corpus,
    )):
        raise ValueError("all inputs must be JSON objects")
    return build_runtime_geometry_shape_candidate_join(
        runtime,
        pipeline,
        corpus,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime_catalog")
    parser.add_argument("pipeline_join")
    parser.add_argument("corpus_audit")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_files(
        args.runtime_catalog,
        args.pipeline_join,
        args.corpus_audit,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
