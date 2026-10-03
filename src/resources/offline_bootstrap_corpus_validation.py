"""Corpus-wide readiness validation for exact track and vehicle bootstrap targets.

Raw parser/resource statistics already live in SHIFT.OfflineResourceCoverage/1.
This stage answers a different question: which source-backed high-level targets
can pass the existing fail-closed load_track/load_vehicle contracts.

Candidate discovery is deliberately narrow:
- track: exact <stem>.bff + <stem>_Physics.bff filename pair;
- vehicle: an archive containing both .cdf and .edf resources, matching the
  existing vehicle physics corpus admission convention.

Discovery never makes a target ready.  Every candidate is subsequently checked
through the normal loaders, which enforce exact archive identity, unique roots,
source-backed dependency edges, and blocked-root policy.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from offline_resource_loaders import load_track, load_vehicle
from offline_resource_pipeline import CATALOG_FORMAT, GRAPH_FORMAT

FORMAT = "SHIFT.OfflineBootstrapCorpusValidation/1"


def _rows(value: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    return [row for row in (value.get(key) or []) if isinstance(row, Mapping)]


def _archive_name(row: Mapping[str, Any]) -> str:
    return str(row.get("archive_name") or "")


def discover_track_candidates(catalog: Mapping[str, Any]) -> list[str]:
    """Return stems having an exact visual + `_Physics.bff` archive-name pair."""
    names = {_archive_name(row).lower() for row in _rows(catalog, "archives")}
    stems: set[str] = set()
    display_by_lower: dict[str, str] = {}
    for row in _rows(catalog, "archives"):
        name = _archive_name(row)
        lower = name.lower()
        if not lower.endswith("_physics.bff"):
            continue
        stem = name[:-len("_Physics.bff")]
        base_name = stem + ".bff"
        if base_name.lower() in names:
            stems.add(stem.lower())
            display_by_lower.setdefault(stem.lower(), stem)
    return [display_by_lower[key] for key in sorted(stems)]


def discover_vehicle_candidates(catalog: Mapping[str, Any]) -> list[str]:
    """Return archive stems having the established CDF+EDF vehicle signature."""
    extensions_by_archive: dict[str, set[str]] = defaultdict(set)
    archive_name_by_id: dict[str, str] = {}
    for archive in _rows(catalog, "archives"):
        archive_id = str(archive.get("id") or "")
        if archive_id:
            archive_name_by_id[archive_id] = _archive_name(archive)
    for resource in _rows(catalog, "resources"):
        archive_id = str(resource.get("archive_id") or "")
        extension = str(resource.get("extension") or "").lower()
        if archive_id and extension:
            extensions_by_archive[archive_id].add(extension)

    stems: dict[str, str] = {}
    for archive_id, extensions in extensions_by_archive.items():
        if not {".cdf", ".edf"}.issubset(extensions):
            continue
        name = archive_name_by_id.get(archive_id, "")
        if not name.lower().endswith(".bff"):
            continue
        stem = name[:-4]
        stems.setdefault(stem.lower(), stem)
    return [stems[key] for key in sorted(stems)]


def _target_row(kind: str, name: str, report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "kind": kind,
        "name": name,
        "status": report.get("status"),
        "ready": report.get("ready") is True,
        "blocking_reasons": list(report.get("blocking_reasons") or []),
        "blocked_required_roots": list(report.get("blocked_required_roots") or []),
        "unresolved_dependency_count": len(report.get("unresolved_dependencies") or []),
        "selected_archives": dict(report.get("selected_archives") or {}),
        "roots": dict(report.get("roots") or {}),
    }


def build_bootstrap_corpus_validation(
    catalog: Mapping[str, Any],
    graph: Mapping[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    if catalog.get("format") != CATALOG_FORMAT:
        blockers.append("catalog:invalid-format")
    if graph.get("format") != GRAPH_FORMAT:
        blockers.append("dependency-graph:invalid-format")

    targets: list[dict[str, Any]] = []
    if not blockers:
        for track in discover_track_candidates(catalog):
            targets.append(_target_row("track", track, load_track(catalog, graph, track=track)))
        for vehicle in discover_vehicle_candidates(catalog):
            targets.append(
                _target_row("vehicle", vehicle, load_vehicle(catalog, graph, vehicle=vehicle))
            )

    by_kind: dict[str, dict[str, int]] = {}
    for kind in ("track", "vehicle"):
        rows = [row for row in targets if row["kind"] == kind]
        by_kind[kind] = {
            "candidates": len(rows),
            "ready": sum(row["ready"] for row in rows),
            "blocked": sum(not row["ready"] for row in rows),
        }

    reason_counts = Counter(
        str(reason)
        for row in targets
        if not row["ready"]
        for reason in row["blocking_reasons"]
    )
    target_blocked = sum(not row["ready"] for row in targets)
    blockers.extend(
        f"target-blocked:{row['kind']}:{row['name']}"
        for row in targets
        if not row["ready"]
    )
    blockers = list(dict.fromkeys(blockers))

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "summary": {
            "targets": len(targets),
            "ready": len(targets) - target_blocked,
            "blocked": target_blocked,
            "track": by_kind["track"],
            "vehicle": by_kind["vehicle"],
            "blocking_reason_counts": dict(sorted(reason_counts.items())),
        },
        "targets": targets,
        "blocking_reasons": blockers,
        "boundary": {
            "raw_resource_validation_replaced": False,
            "track_candidate_rule": "exact <stem>.bff + <stem>_Physics.bff pair",
            "vehicle_candidate_rule": "archive contains CDF+EDF resources",
            "vehicle_candidate_rule_source": "existing vehicle physics corpus admission",
            "candidate_discovery_implies_readiness": False,
            "target_validation": "existing fail-closed load_track/load_vehicle contracts",
            "fuzzy_name_matching": False,
            "basename_dependency_resolution": False,
            "missing_resource_synthesis": False,
        },
    }


def build_bootstrap_corpus_validation_files(
    catalog_path: str | Path,
    graph_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    graph = json.loads(Path(graph_path).read_text(encoding="utf-8"))
    if not isinstance(catalog, dict) or not isinstance(graph, dict):
        raise ValueError("catalog and dependency graph must be JSON objects")
    report = build_bootstrap_corpus_validation(catalog, graph)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
