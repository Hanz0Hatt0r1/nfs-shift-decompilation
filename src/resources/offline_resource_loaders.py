"""High-level fail-closed loaders over the offline SHIFT resource catalog.

These loaders do not parse unknown formats, invent aliases, or synthesize missing
resources.  They only select exact catalog archives/roots and report semantic
dependency blockers already proven by ``SHIFT.OfflineResourceDependencyGraph/1``.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from offline_resource_pipeline import (
    GRAPH_FORMAT,
    CATALOG_FORMAT,
    TRACK_PHYSICS_ROOT_EXTENSIONS,
    TRACK_VISUAL_ROOT_EXTENSIONS,
    VEHICLE_PHYSICS_EXTENSIONS,
    VEHICLE_RENDER_ROOT_EXTENSIONS,
)

TRACK_LOAD_FORMAT = "SHIFT.OfflineTrackLoad/1"
VEHICLE_LOAD_FORMAT = "SHIFT.OfflineVehicleLoad/1"


def _catalog_rows(catalog: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    return [row for row in (catalog.get(key) or []) if isinstance(row, Mapping)]


def _archive(
    catalog: Mapping[str, Any],
    filename: str,
    blockers: list[str],
    label: str,
    *,
    optional: bool = False,
) -> Mapping[str, Any] | None:
    hits = [
        row for row in _catalog_rows(catalog, "archives")
        if str(row.get("archive_name") or "").lower() == filename.lower()
    ]
    if len(hits) == 1:
        return hits[0]
    if not optional or hits:
        blockers.append(
            f"{label}-archive-" + ("missing" if not hits else f"ambiguous:{len(hits)}")
        )
    return None


def _resource_rows_for_archive(
    catalog: Mapping[str, Any], archive: Mapping[str, Any] | None
) -> list[Mapping[str, Any]]:
    if archive is None:
        return []
    archive_id = str(archive.get("id") or "")
    return [
        row for row in _catalog_rows(catalog, "resources")
        if str(row.get("archive_id") or "") == archive_id
    ]


def _unique_ext(
    rows: Sequence[Mapping[str, Any]],
    ext: str,
    blockers: list[str],
    label: str,
) -> str | None:
    hits = [row for row in rows if str(row.get("extension") or "").lower() == ext]
    if len(hits) == 1 and hits[0].get("id"):
        return str(hits[0]["id"])
    blockers.append(f"{label}{ext}-" + ("missing" if not hits else f"ambiguous:{len(hits)}"))
    return None


def _dependency_state(
    catalog: Mapping[str, Any],
    graph: Mapping[str, Any],
    selected: Sequence[Mapping[str, Any]],
    blockers: list[str],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    selected_ids = {str(row.get("id") or "") for row in selected if row.get("id")}
    edges = [
        edge for edge in (graph.get("edges") or [])
        if isinstance(edge, Mapping)
        and str(edge.get("source_archive_id") or "") in selected_ids
    ]
    unresolved = [
        edge for edge in edges
        if edge.get("admissible") is True and edge.get("status") != "resolved"
    ]
    blockers.extend(
        f"dependency-{edge.get('status')}:{edge.get('source_path')}->{edge.get('ref')}"
        for edge in unresolved
    )
    decoded_any = any(
        row.get("decode_status") in {"parsed", "blocked"}
        for row in _catalog_rows(catalog, "resources")
        if str(row.get("archive_id") or "") in selected_ids
    )
    if selected_ids and not decoded_any:
        blockers.append("dependency-validation-not-run:use --decode-known")
    return edges, unresolved


def _contract_boundary() -> dict[str, Any]:
    return {
        "archive_selection": "exact-filename",
        "required_root_selection": "unique-extension-within-selected-archive",
        "dependency_resolution": "admissible-semantic-edges-only",
        "heuristic_refs_close_gate": False,
        "basename_fallback": False,
        "missing_resource_synthesis": False,
    }


def load_track(
    catalog: Mapping[str, Any],
    graph: Mapping[str, Any],
    *,
    track: str,
) -> dict[str, Any]:
    """Select one track's exact visual/physics archives and proven root resources."""
    blockers: list[str] = []
    if catalog.get("format") != CATALOG_FORMAT:
        blockers.append("catalog:invalid-format")
    if graph.get("format") != GRAPH_FORMAT:
        blockers.append("dependency-graph:invalid-format")

    visual = _archive(catalog, f"{track}.bff", blockers, "track-visual")
    physics = _archive(catalog, f"{track}_Physics.bff", blockers, "track-physics")
    selected = [row for row in (visual, physics) if row is not None]
    visual_rows = _resource_rows_for_archive(catalog, visual)
    physics_rows = _resource_rows_for_archive(catalog, physics)

    roots = {
        "track_visual": {
            ext: _unique_ext(visual_rows, ext, blockers, "track-visual")
            for ext in TRACK_VISUAL_ROOT_EXTENSIONS
        },
        "track_physics": {
            ext: _unique_ext(physics_rows, ext, blockers, "track-physics")
            for ext in TRACK_PHYSICS_ROOT_EXTENSIONS
        },
    }
    roots["track_visual"]["imb_resource_ids"] = [
        str(row["id"]) for row in visual_rows
        if row.get("extension") == ".imb" and row.get("id")
    ]
    roots["track_visual"]["imx_resource_ids"] = [
        str(row["id"]) for row in visual_rows
        if row.get("extension") == ".imx" and row.get("id")
    ]

    edges, unresolved = _dependency_state(catalog, graph, selected, blockers)
    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    return {
        "format": TRACK_LOAD_FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "track": track,
        "selected_archives": {
            key: row
            for key, row in (("track_visual", visual), ("track_physics", physics))
            if row is not None
        },
        "roots": roots,
        "dependency_edges": edges,
        "unresolved_dependencies": unresolved,
        "blocking_reasons": blockers,
        "boundary": _contract_boundary(),
    }


def load_vehicle(
    catalog: Mapping[str, Any],
    graph: Mapping[str, Any],
    *,
    vehicle: str,
) -> dict[str, Any]:
    """Select one vehicle's exact archive, optional cockpit and proven root assets."""
    blockers: list[str] = []
    if catalog.get("format") != CATALOG_FORMAT:
        blockers.append("catalog:invalid-format")
    if graph.get("format") != GRAPH_FORMAT:
        blockers.append("dependency-graph:invalid-format")

    vehicle_archive = _archive(catalog, f"{vehicle}.bff", blockers, "vehicle")
    cockpit = _archive(
        catalog,
        f"{vehicle}_Cockpit.bff",
        blockers,
        "vehicle-cockpit",
        optional=True,
    )
    selected = [row for row in (vehicle_archive, cockpit) if row is not None]
    rows = _resource_rows_for_archive(catalog, vehicle_archive)
    roots = {
        ext: _unique_ext(rows, ext, blockers, "vehicle")
        for ext in VEHICLE_PHYSICS_EXTENSIONS + VEHICLE_RENDER_ROOT_EXTENSIONS
    }

    edges, unresolved = _dependency_state(catalog, graph, selected, blockers)
    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    return {
        "format": VEHICLE_LOAD_FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "vehicle": vehicle,
        "selected_archives": {
            key: row
            for key, row in (("vehicle", vehicle_archive), ("vehicle_cockpit", cockpit))
            if row is not None
        },
        "roots": {"vehicle": roots},
        "dependency_edges": edges,
        "unresolved_dependencies": unresolved,
        "blocking_reasons": blockers,
        "boundary": _contract_boundary(),
    }
