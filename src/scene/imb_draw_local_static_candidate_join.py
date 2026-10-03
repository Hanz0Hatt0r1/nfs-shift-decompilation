"""Join draw-local D3D9 evidence to static IMB candidates conservatively.

The input contracts are ``SHIFT.D3D9TargetDrawLocalEvidence/1`` and
``SHIFT.IMBRuntimeGeometryPointerCandidateJoin/1``.  The stage reconstructs the
same pointer-free resource-shape hash and capture-local geometry-pointer hash
used by Phases 605/613, then applies only exact shader-byte contradictions to
Phase 615 static candidate sets.

No surviving candidate is promoted to retail resource identity.  Runtime
resource path/SHA or exact VB/IB payload equality is still required for that
promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.IMBDrawLocalStaticCandidateJoin/1"
DRAW_LOCAL_FORMAT = "SHIFT.D3D9TargetDrawLocalEvidence/1"
GEOMETRY_JOIN_FORMAT = "SHIFT.IMBRuntimeGeometryPointerCandidateJoin/1"


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
        f"input file not found: {candidate} (also tried {repo_candidate})"
    )


def _draw_geometry_identity(draw: Mapping[str, Any]) -> dict[str, Any] | None:
    source = draw.get("geometry_identity")
    if not isinstance(source, Mapping):
        return None
    stream0_ptr = source.get("stream0_vertex_buffer_ptr")
    stream0_generation = source.get(
        "stream0_vertex_buffer_creation_event_index"
    )
    index_ptr = source.get("index_buffer_ptr")
    index_generation = source.get("index_buffer_creation_event_index")
    draw_range = source.get("draw_range")
    if not isinstance(draw_range, Mapping):
        return None
    identity = {
        "device_ptr": source.get("device_ptr") or draw.get("device_ptr"),
        "stream0_vertex_buffer_ptr": stream0_ptr,
        "stream0_vertex_buffer_creation_event_index": stream0_generation,
        "index_buffer_ptr": index_ptr,
        "index_buffer_creation_event_index": index_generation,
        "draw_range": {
            "primitive_type": draw_range.get("primitive_type"),
            "base_vertex_index": draw_range.get("base_vertex_index"),
            "start_index": draw_range.get("start_index"),
            "primitive_count": draw_range.get("primitive_count"),
        },
    }
    identity["creation_identity_complete"] = bool(
        stream0_ptr
        and index_ptr
        and stream0_generation is not None
        and index_generation is not None
    )
    return identity


def _texture_shape(binding: Mapping[str, Any]) -> dict[str, Any] | None:
    stage = binding.get("stage")
    if not isinstance(stage, int):
        return None
    descriptor = binding.get("descriptor")
    if not isinstance(descriptor, Mapping):
        descriptor = {}
    return {
        "stage": stage,
        "resource_type_name": descriptor.get("resource_type_name"),
        "width": descriptor.get("width"),
        "height": descriptor.get("height"),
        "depth": descriptor.get("depth"),
        "edge_length": descriptor.get("edge_length"),
        "format": descriptor.get("format"),
        "pool": descriptor.get("pool"),
        "level_count": descriptor.get(
            "level_count", descriptor.get("levels")
        ),
        "usage": descriptor.get("usage"),
    }


def _draw_resource_shape(draw: Mapping[str, Any]) -> dict[str, Any] | None:
    shader_pair = draw.get("shader_pair")
    if not isinstance(shader_pair, Mapping):
        return None
    declaration = draw.get("declaration")
    declaration = declaration if isinstance(declaration, Mapping) else {}

    stream_layout: list[dict[str, Any]] = []
    stream_shapes: list[dict[str, Any]] = []
    for binding in draw.get("streams") or []:
        if not isinstance(binding, Mapping):
            continue
        stream = binding.get("stream")
        if not isinstance(stream, int):
            continue
        stride = binding.get("stride")
        descriptor = binding.get("descriptor")
        descriptor = descriptor if isinstance(descriptor, Mapping) else {}
        stream_layout.append({"stream": stream, "stride": stride})
        stream_shapes.append({
            "stream": stream,
            "stride": stride,
            "length": descriptor.get("length"),
            "usage": descriptor.get("usage"),
            "fvf": descriptor.get("fvf"),
            "pool": descriptor.get("pool"),
        })
    stream_layout.sort(key=lambda row: int(row["stream"]))
    stream_shapes.sort(key=lambda row: int(row["stream"]))

    index_binding = draw.get("index_binding")
    index_binding = (
        index_binding if isinstance(index_binding, Mapping) else {}
    )
    index_descriptor = index_binding.get("descriptor")
    index_descriptor = (
        index_descriptor if isinstance(index_descriptor, Mapping) else {}
    )
    index_shape = {
        "length": index_descriptor.get("length"),
        "usage": index_descriptor.get("usage"),
        "format": index_descriptor.get("format"),
        "pool": index_descriptor.get("pool"),
    }

    texture_shapes = []
    for binding in draw.get("sampler_bindings") or []:
        if not isinstance(binding, Mapping):
            continue
        shape = _texture_shape(binding)
        if shape is not None:
            texture_shapes.append(shape)
    texture_shapes.sort(key=lambda row: int(row["stage"]))

    pipeline = {
        "vertex_shader_sha256": _valid_sha(
            shader_pair.get("vertex_shader_sha256")
        ),
        "pixel_shader_sha256": _valid_sha(
            shader_pair.get("pixel_shader_sha256")
        ),
        "declaration_sha256": _valid_sha(
            declaration.get("declaration_sha256")
        ),
        "stream_layout": stream_layout,
        "index_format": index_shape.get("format"),
    }
    return {
        **pipeline,
        "stream_resource_shapes": stream_shapes,
        "index_resource_shape": index_shape,
        "texture_stages": texture_shapes,
    }


def _compact_candidate(group: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "content_group_sha256": _valid_sha(group.get("content_group_sha256")),
        "imb_sha256": _valid_sha(group.get("imb_sha256")),
        "imb_paths": sorted(
            {str(value) for value in (group.get("imb_paths") or []) if value}
        ),
        "archives": sorted(
            {str(value) for value in (group.get("archives") or []) if value}
        ),
        "bmt_sha256": _valid_sha(group.get("bmt_sha256")),
        "shader_family": group.get("shader_family"),
        "primitive_index": group.get("primitive_index"),
        "draw_range": dict(group.get("draw_range") or {}),
        "static_vertex_stride": group.get("static_vertex_stride"),
        "matched_vertex_shader_sha256": _valid_sha(
            group.get("matched_vertex_shader_sha256")
        ),
        "matched_pixel_shader_sha256": _valid_sha(
            group.get("matched_pixel_shader_sha256")
        ),
        "pipeline_recovery_evidence_kind": group.get(
            "pipeline_recovery_evidence_kind"
        ),
        "pipeline_recovery_static_vertex_shader_mismatch": (
            group.get("pipeline_recovery_static_vertex_shader_mismatch") is True
        ),
    }


def _geometry_indices(
    geometry_join: Mapping[str, Any],
) -> tuple[
    dict[str, dict[str, dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    by_resource: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    by_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for resource in geometry_join.get("resource_shapes") or []:
        if not isinstance(resource, Mapping):
            continue
        resource_sha = _valid_sha(resource.get("resource_shape_sha256"))
        if not resource_sha:
            continue
        for identity_row in resource.get("geometry_pointer_identities") or []:
            if not isinstance(identity_row, Mapping):
                continue
            identity_sha = _valid_sha(
                identity_row.get("geometry_pointer_identity_sha256")
            )
            if not identity_sha:
                continue
            candidates = sorted(
                [
                    _compact_candidate(group)
                    for group in (
                        identity_row.get("candidate_content_groups") or []
                    )
                    if isinstance(group, Mapping)
                    and _valid_sha(group.get("content_group_sha256"))
                ],
                key=lambda row: str(row.get("content_group_sha256") or ""),
            )
            source = {
                "resource_shape_sha256": resource_sha,
                "geometry_pointer_identity_sha256": identity_sha,
                "source_gate_status": identity_row.get(
                    "geometry_candidate_gate_status"
                ),
                "source_candidate_status": identity_row.get(
                    "candidate_content_status"
                ),
                "candidate_content_groups": candidates,
            }
            by_resource[resource_sha][identity_sha] = source
            by_identity[identity_sha].append(source)

    for sources in by_identity.values():
        sources.sort(key=lambda row: str(row["resource_shape_sha256"]))
    return dict(by_resource), dict(by_identity)


def _shader_gate(
    candidate: Mapping[str, Any],
    *,
    observed_vertex_sha: str | None,
    observed_pixel_sha: str | None,
) -> tuple[bool, str]:
    candidate_pixel = _valid_sha(candidate.get("matched_pixel_shader_sha256"))
    candidate_vertex = _valid_sha(candidate.get("matched_vertex_shader_sha256"))
    cross_vs = (
        candidate.get("pipeline_recovery_static_vertex_shader_mismatch") is True
    )

    if candidate_pixel and observed_pixel_sha and candidate_pixel != observed_pixel_sha:
        return False, "rejected-pixel-shader-byte-mismatch"
    if (
        candidate_vertex
        and observed_vertex_sha
        and candidate_vertex != observed_vertex_sha
        and not cross_vs
    ):
        return False, "rejected-vertex-shader-byte-mismatch"
    if (
        candidate_pixel == observed_pixel_sha
        and candidate_pixel is not None
        and candidate_vertex == observed_vertex_sha
        and candidate_vertex is not None
    ):
        return True, "exact-vs+ps-byte-match"
    if candidate_pixel == observed_pixel_sha and candidate_pixel is not None:
        if cross_vs and candidate_vertex and candidate_vertex != observed_vertex_sha:
            return True, "exact-ps-byte-match-cross-vs-donor"
        return True, "exact-ps-byte-match"
    if candidate_vertex == observed_vertex_sha and candidate_vertex is not None:
        return True, "exact-vs-byte-match"
    return True, "shader-byte-gate-unavailable"


def _candidate_union(sources: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    # Geometry-only fallback can span multiple Phase 615 resource shapes. Keep
    # every shader-evidence variant instead of fabricating a contradiction by
    # overwriting equal static content identities observed in another shape.
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    for source in sources:
        for candidate in source.get("candidate_content_groups") or []:
            if not isinstance(candidate, Mapping):
                continue
            key = (
                candidate.get("content_group_sha256"),
                candidate.get("matched_vertex_shader_sha256"),
                candidate.get("matched_pixel_shader_sha256"),
                candidate.get("pipeline_recovery_evidence_kind"),
                candidate.get("pipeline_recovery_static_vertex_shader_mismatch"),
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(dict(candidate))
    result.sort(
        key=lambda row: (
            str(row.get("content_group_sha256") or ""),
            str(row.get("matched_vertex_shader_sha256") or ""),
            str(row.get("matched_pixel_shader_sha256") or ""),
        )
    )
    return result


def build_draw_local_static_candidate_join(
    draw_local: Mapping[str, Any],
    geometry_join: Mapping[str, Any],
) -> dict[str, Any]:
    if draw_local.get("format") != DRAW_LOCAL_FORMAT:
        raise ValueError(
            "draw-local report must be SHIFT.D3D9TargetDrawLocalEvidence/1"
        )
    if geometry_join.get("format") != GEOMETRY_JOIN_FORMAT:
        raise ValueError(
            "geometry join must be SHIFT.IMBRuntimeGeometryPointerCandidateJoin/1"
        )

    by_resource, by_identity = _geometry_indices(geometry_join)
    gate_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    match_kind_counts: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    exact_pair_candidate_draw_count = 0
    single_candidate_draw_count = 0
    ambiguous_candidate_draw_count = 0
    rejected_candidate_count = 0

    for draw in draw_local.get("draws") or []:
        if not isinstance(draw, Mapping):
            continue
        identity = _draw_geometry_identity(draw)
        identity_sha = _canonical_hash(identity) if identity is not None else None
        resource_shape = _draw_resource_shape(draw)
        resource_sha = (
            _canonical_hash(resource_shape)
            if resource_shape is not None
            else None
        )

        sources: list[dict[str, Any]] = []
        match_kind = "unmatched"
        if resource_sha and identity_sha:
            direct = by_resource.get(resource_sha, {}).get(identity_sha)
            if direct is not None:
                sources = [direct]
                match_kind = "exact-resource+geometry"
        if not sources and identity_sha:
            sources = list(by_identity.get(identity_sha) or [])
            if len(sources) == 1:
                match_kind = "geometry-only-single-resource-fallback"
            elif len(sources) > 1:
                match_kind = "geometry-only-multi-resource-fallback"
        match_kind_counts[match_kind] += 1

        shader_pair = draw.get("shader_pair") or {}
        observed_vertex_sha = (
            _valid_sha(shader_pair.get("vertex_shader_sha256"))
            if isinstance(shader_pair, Mapping)
            else None
        )
        observed_pixel_sha = (
            _valid_sha(shader_pair.get("pixel_shader_sha256"))
            if isinstance(shader_pair, Mapping)
            else None
        )

        baseline = _candidate_union(sources)
        surviving_variants: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        draw_gate_counts: Counter[str] = Counter()
        for candidate in baseline:
            keep, reason = _shader_gate(
                candidate,
                observed_vertex_sha=observed_vertex_sha,
                observed_pixel_sha=observed_pixel_sha,
            )
            draw_gate_counts[reason] += 1
            gate_counts[reason] += 1
            record = {**dict(candidate), "shader_gate_status": reason}
            if keep:
                surviving_variants.append(record)
            else:
                rejected.append(record)
                rejected_candidate_count += 1

        surviving_content_shas = sorted({
            str(candidate.get("content_group_sha256"))
            for candidate in surviving_variants
            if candidate.get("content_group_sha256")
        })
        if identity is None or identity_sha is None:
            status = "draw-geometry-identity-unavailable"
        elif not sources:
            status = "geometry-identity-not-in-phase615"
        elif not baseline:
            status = "no-static-candidates"
        elif not surviving_content_shas:
            status = "all-static-candidates-rejected-by-exact-shader-bytes"
        elif len(surviving_content_shas) == 1:
            status = "single-static-candidate"
            single_candidate_draw_count += 1
        else:
            status = "ambiguous-static-candidates"
            ambiguous_candidate_draw_count += 1
        status_counts[status] += 1

        if any(
            candidate.get("shader_gate_status") == "exact-vs+ps-byte-match"
            for candidate in surviving_variants
        ):
            exact_pair_candidate_draw_count += 1

        rows.append({
            "event_index": draw.get("event_index"),
            "frame": draw.get("frame"),
            "draw_evidence_sha256": _valid_sha(draw.get("draw_evidence_sha256")),
            "resource_shape_sha256": resource_sha,
            "resource_shape": resource_shape,
            "geometry_pointer_identity_sha256": identity_sha,
            "geometry_pointer_identity": identity,
            "phase615_match_kind": match_kind,
            "phase615_resource_shape_sha256s": sorted(
                str(source.get("resource_shape_sha256")) for source in sources
            ),
            "phase615_source_gate_statuses": sorted({
                str(source.get("source_gate_status"))
                for source in sources
                if source.get("source_gate_status")
            }),
            "shader_pair": {
                "vertex_shader_sha256": observed_vertex_sha,
                "pixel_shader_sha256": observed_pixel_sha,
            },
            "source_candidate_variant_count": len(baseline),
            "surviving_candidate_variant_count": len(surviving_variants),
            "surviving_content_group_count": len(surviving_content_shas),
            "surviving_content_group_sha256s": surviving_content_shas,
            "rejected_candidate_variant_count": len(rejected),
            "shader_gate_status_counts": dict(sorted(draw_gate_counts.items())),
            "candidate_resolution_status": status,
            "surviving_candidate_variants": surviving_variants,
            "rejected_candidate_variants": rejected,
        })

    rows.sort(
        key=lambda row: (
            int(row.get("event_index"))
            if isinstance(row.get("event_index"), int)
            else 2**63 - 1,
            str(row.get("draw_evidence_sha256") or ""),
        )
    )

    group_raw: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "draw_count": 0,
            "statuses": Counter(),
            "survivor_sets": set(),
            "shader_pairs": set(),
            "match_kinds": Counter(),
        }
    )
    for row in rows:
        identity_sha = row.get("geometry_pointer_identity_sha256")
        if not identity_sha:
            continue
        group = group_raw[str(identity_sha)]
        group["draw_count"] += 1
        group["statuses"][str(row["candidate_resolution_status"])] += 1
        group["match_kinds"][str(row["phase615_match_kind"])] += 1
        group["survivor_sets"].add(
            tuple(row.get("surviving_content_group_sha256s") or [])
        )
        pair = row.get("shader_pair") or {}
        group["shader_pairs"].add(
            (
                pair.get("vertex_shader_sha256"),
                pair.get("pixel_shader_sha256"),
            )
        )

    geometry_groups = []
    for identity_sha in sorted(group_raw):
        group = group_raw[identity_sha]
        survivor_sets = sorted(group["survivor_sets"])
        geometry_groups.append({
            "geometry_pointer_identity_sha256": identity_sha,
            "draw_count": int(group["draw_count"]),
            "phase615_match_kind_counts": dict(
                sorted(group["match_kinds"].items())
            ),
            "candidate_resolution_status_counts": dict(
                sorted(group["statuses"].items())
            ),
            "unique_surviving_candidate_set_count": len(survivor_sets),
            "surviving_candidate_sets": [list(values) for values in survivor_sets],
            "unique_shader_pair_count": len(group["shader_pairs"]),
        })

    return {
        "format": FORMAT,
        "version": 1,
        "status": "observed" if rows else "not-observed",
        "summary": {
            "draw_count": len(rows),
            "phase615_match_kind_counts": dict(sorted(match_kind_counts.items())),
            "exact_vs_ps_candidate_draw_count": exact_pair_candidate_draw_count,
            "single_static_candidate_draw_count": single_candidate_draw_count,
            "ambiguous_static_candidate_draw_count": ambiguous_candidate_draw_count,
            "rejected_static_candidate_variant_count": rejected_candidate_count,
            "candidate_resolution_status_counts": dict(sorted(status_counts.items())),
            "shader_gate_status_counts": dict(sorted(gate_counts.items())),
            "unique_geometry_pointer_identity_count": len(group_raw),
        },
        "draws": rows,
        "geometry_groups": geometry_groups,
        "boundary": {
            "candidate_only": True,
            "exact_resource_shape": (
                "pointer-free D3D9 shader/declaration/stream/index/CTAB-filtered texture descriptor hash; shape equality is not resource identity"
            ),
            "capture_local_pointer_identity_only": True,
            "exact_shader_gate": (
                "candidate matched VS/PS byte SHA-256 may reject contradictory static candidates; missing shader hashes fail open"
            ),
            "cross_vs_policy": (
                "an explicit Phase 612 static-VS mismatch is donor diagnostics only and cannot reject an otherwise exact pixel-shader match"
            ),
            "single_candidate_is_retail_identity": False,
            "render_admission": False,
            "remaining_hard_identity_gate": (
                "exact runtime resource path/SHA or exact VB/IB payload equality is still required for portable IMB identity"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draw_local_report")
    parser.add_argument("geometry_join")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    draw_local = json.loads(
        resolve_input_path(args.draw_local_report).read_text(encoding="utf-8")
    )
    geometry_join = json.loads(
        resolve_input_path(args.geometry_join).read_text(encoding="utf-8")
    )
    if not isinstance(draw_local, dict) or not isinstance(geometry_join, dict):
        raise ValueError("inputs must be JSON objects")
    report = build_draw_local_static_candidate_join(draw_local, geometry_join)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
