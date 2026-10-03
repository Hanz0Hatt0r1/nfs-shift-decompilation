"""Build an exact, fail-closed vehicle render resource closure from Process D artifacts."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping

CATALOG_FORMAT = "SHIFT.OfflineResourceCatalog/1"
DEPENDENCY_GRAPH_FORMAT = "SHIFT.OfflineResourceDependencyGraph/1"
BOOTSTRAP_FORMAT = "SHIFT.SceneVehicleBootstrap/1"
FORMAT = "SHIFT.VehicleRenderResourceGraph/1"

_DEPENDENCY_SOURCE_EXTENSIONS = {".vhf", ".meb", ".bmt"}


def _rows(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in (value or []) if isinstance(row, Mapping)]


def build_vehicle_render_resource_graph(
    catalog: Mapping[str, Any],
    dependency_graph: Mapping[str, Any],
    bootstrap: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve VHF -> geometry -> material -> texture/shader resources exactly.

    Only already-admissible semantic dependency edges are traversed. Diagnostic
    string-scan edges never enter the closure and unresolved/ambiguous semantic
    edges remain explicit blockers.
    """
    blockers: list[str] = []
    if catalog.get("format") != CATALOG_FORMAT:
        blockers.append("catalog:invalid-format")
    if dependency_graph.get("format") != DEPENDENCY_GRAPH_FORMAT:
        blockers.append("dependency-graph:invalid-format")
    if bootstrap.get("format") != BOOTSTRAP_FORMAT:
        blockers.append("bootstrap:invalid-format")

    selected = bootstrap.get("selected_archives") or {}
    vehicle_archive = selected.get("vehicle") if isinstance(selected, Mapping) else None
    if not isinstance(vehicle_archive, Mapping):
        blockers.append("vehicle-archive:missing")
        vehicle_archive = {}

    roots = bootstrap.get("roots") or {}
    vehicle_roots = roots.get("vehicle") if isinstance(roots, Mapping) else None
    if not isinstance(vehicle_roots, Mapping):
        blockers.append("vehicle-roots:missing")
        vehicle_roots = {}
    root_id = vehicle_roots.get(".vhf")
    if not isinstance(root_id, str) or not root_id:
        blockers.append("vehicle-vhf-root:missing")
        root_id = None

    resources = {
        str(row.get("id")): row
        for row in _rows(catalog.get("resources"))
        if row.get("id")
    }
    if root_id is not None:
        root = resources.get(root_id)
        if root is None:
            blockers.append("vehicle-vhf-root:catalog-resource-missing")
        else:
            if str(root.get("archive_id") or "") != str(vehicle_archive.get("id") or ""):
                blockers.append("vehicle-vhf-root:archive-mismatch")
            if str(root.get("extension") or "").lower() != ".vhf":
                blockers.append("vehicle-vhf-root:not-vhf")

    outgoing: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for edge in _rows(dependency_graph.get("edges")):
        if edge.get("admissible") is True:
            outgoing[str(edge.get("source_id") or "")].append(edge)

    visited: set[str] = set()
    queue = [root_id] if root_id is not None and root_id in resources else []
    closure_edges: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    while queue:
        resource_id = str(queue.pop(0))
        if resource_id in visited:
            continue
        visited.add(resource_id)
        resource = resources[resource_id]
        ext = str(resource.get("extension") or "").lower()
        if ext in _DEPENDENCY_SOURCE_EXTENSIONS and resource.get("decode_status") != "parsed":
            blockers.append(
                f"dependency-source-not-parsed:{resource_id}:{ext or '<none>'}"
            )

        for edge in outgoing.get(resource_id, []):
            status = str(edge.get("status") or "")
            targets = [str(value) for value in (edge.get("targets") or [])]
            row = {
                "source_id": resource_id,
                "source_path": edge.get("source_path"),
                "kind": edge.get("kind"),
                "ref": edge.get("ref"),
                "scope": edge.get("scope"),
                "parser": edge.get("parser"),
                "status": status,
                "targets": targets,
            }
            closure_edges.append(row)
            if status != "resolved" or len(targets) != 1:
                unresolved.append(row)
                blockers.append(
                    "dependency-"
                    + (status or "invalid")
                    + f":{edge.get('source_path')}->{edge.get('ref')}"
                )
                continue
            target = targets[0]
            if target not in resources:
                unresolved.append(row)
                blockers.append(f"dependency-target-not-in-catalog:{target}")
                continue
            queue.append(target)

    closure = [resources[resource_id] for resource_id in sorted(visited)]
    extension_counts = Counter(
        str(row.get("extension") or "<none>") for row in closure
    )
    category_counts = Counter(
        str(row.get("category") or "UNKNOWN") for row in closure
    )
    decode_counts = Counter(
        str(row.get("decode_status") or "unknown") for row in closure
    )

    asset_rows = [
        {
            "resource_id": row.get("id"),
            "archive_id": row.get("archive_id"),
            "archive_name": row.get("archive_name"),
            "path": row.get("path"),
            "extension": row.get("extension"),
            "category": row.get("category"),
            "decode_status": row.get("decode_status"),
            "decoded_sha256": row.get("decoded_sha256"),
            "raw_sha256": row.get("raw_sha256"),
            "neutral_ir": row.get("neutral_ir"),
        }
        for row in closure
    ]

    blockers = list(dict.fromkeys(blockers))
    closure_ready = bool(root_id) and bool(closure) and not blockers
    native_blockers = list(blockers)
    if closure_ready:
        native_blockers.append("runtime-draw-shader-permutation-provenance-required")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "resource-ready-native-blocked" if closure_ready else "blocked",
        "ready": closure_ready,
        "resource_closure_ready": closure_ready,
        "native_render_ready": False,
        "vehicle": bootstrap.get("vehicle"),
        "source_archive": vehicle_archive.get("archive_name"),
        "source_archive_id": vehicle_archive.get("id"),
        "vhf_root_resource_id": root_id,
        "resources": asset_rows,
        "edges": closure_edges,
        "unresolved_dependencies": unresolved,
        "blocking_reasons": blockers,
        "native_blocking_reasons": native_blockers,
        "stats": {
            "resources": len(asset_rows),
            "edges": len(closure_edges),
            "unresolved_dependencies": len(unresolved),
            "extensions": dict(sorted(extension_counts.items())),
            "categories": dict(sorted(category_counts.items())),
            "decode_status": dict(sorted(decode_counts.items())),
        },
        "boundary": {
            "root_selection": "exact-bootstrap-vhf-resource-id",
            "dependency_edges": "admissible-semantic-parser-only",
            "diagnostic_edges_traversed": False,
            "basename_fallback": False,
            "lod_or_damage_selection_invented": False,
            "runtime_draw_identity_claimed": False,
            "shader_permutation_identity_claimed": False,
            "native_render_admission_claimed": False,
        },
    }
