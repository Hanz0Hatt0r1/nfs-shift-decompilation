"""Content-addressed resource index for cross-BFF parity.

The index deliberately keeps path identity and stored-byte identity separate.
A matching raw SHA-256 is stronger than a matching logical path, but neither
one claims decoded-format or runtime-material equivalence.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping

from runtime_resource_identity import normalize_resource_path

FORMAT = "SHIFT.ResourceContentIndex/1"


def build_resource_content_index(
    resources: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in resources:
        path = normalize_resource_path(item.get("resource_path", item.get("path")))
        sha = str(item.get("resource_sha256", item.get("raw_sha256", ""))).strip().lower()
        archive = str(item.get("archive", "")).strip()
        row = {
            "archive": archive,
            "path": path,
            "sha256": sha or None,
            "type": item.get("type"),
            "compressed_size": item.get("compressed_size"),
            "uncompressed_size": item.get("uncompressed_size"),
        }
        if path is not None:
            by_path[path].append(row)
        if sha:
            by_sha[sha].append(row)

    path_groups = [
        {
            "path": path,
            "occurrences": len(items),
            "archives": sorted({item["archive"] for item in items if item["archive"]}),
            "sha256_values": sorted(
                {str(item["sha256"]) for item in items if item["sha256"]}
            ),
        }
        for path, items in by_path.items()
    ]
    sha_groups = [
        {
            "sha256": sha,
            "occurrences": len(items),
            "archives": sorted({item["archive"] for item in items if item["archive"]}),
            "paths": sorted({str(item["path"]) for item in items if item["path"]}),
        }
        for sha, items in by_sha.items()
    ]

    path_groups.sort(key=lambda row: (-row["occurrences"], row["path"]))
    sha_groups.sort(key=lambda row: (-row["occurrences"], row["sha256"]))

    return {
        "format": FORMAT,
        "version": 1,
        "resource_count": sum(len(items) for items in by_path.values()),
        "unique_paths": len(by_path),
        "unique_sha256": len(by_sha),
        "path_groups": path_groups,
        "sha_groups": sha_groups,
        "limitations": [
            "Logical path equality does not prove payload equality.",
            "Raw SHA-256 equality proves stored-byte equality for the supplied scope only.",
            "No decoded resource semantics or runtime material identity are inferred.",
        ],
    }


def find_exact_payload_matches(
    index: Mapping[str, Any],
    sha256: str,
) -> list[dict[str, Any]]:
    needle = str(sha256).strip().lower()
    for group in index.get("sha_groups") or []:
        if str(group.get("sha256", "")).lower() == needle:
            return [dict(group)]
    return []


__all__ = [
    "FORMAT",
    "build_resource_content_index",
    "find_exact_payload_matches",
]
