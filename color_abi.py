"""Evidence tools for the source-correlated SHIFT MEB color property ABI (460/461).

The declaration/channel order is now source-proven under the repository's
three-DWORD MEB property descriptor convention. Candidate interpretations remain
available for forensic comparisons.
"""
from __future__ import annotations

import hashlib
from typing import Any, Iterable


FORMAT = "SHIFT.ColorABIEvidence/1"
SUPPORTED_PROPERTIES = {"460", "461"}
CANDIDATE_ORDERS = ("RGBA", "BGRA")

# D3D9 couples packed-color declaration semantics to shader-visible channels:
# D3DCOLOR expands packed input to RGBA; UBYTE4N only normalizes each byte.
# The SHIFT executable also contains a float4 -> 0xAARRGGBB pack helper
# (FUN_008310c0), which is a concrete in-source observation of packed BGRA
# memory order on the original little-endian Windows target.
D3D9_COLOR_CANDIDATES = (
    {
        "order": "RGBA",
        "d3d9_type": "UBYTE4N",
        "memory_order": "RGBA",
        "shader_order": "RGBA",
        "normalized": True,
    },
    {
        "order": "BGRA",
        "d3d9_type": "D3DCOLOR",
        "memory_order": "BGRA",
        "shader_order": "RGBA",
        "normalized": True,
    },
)
D3D9_COLOR_TYPES = {
    item["d3d9_type"]: item for item in D3D9_COLOR_CANDIDATES
}
D3D9_COLOR_ORDERS = {
    item["order"]: item for item in D3D9_COLOR_CANDIDATES
}


def _validate_payload(property_id: str, payload: bytes) -> None:
    if str(property_id) not in SUPPORTED_PROPERTIES:
        raise ValueError(f"unsupported color property {property_id!r}")
    if len(payload) % 4:
        raise ValueError("color property payload must be divisible by four bytes")


def interpret_color_d3d9(payload: bytes, d3d9_type: str) -> bytes:
    """Interpret a packed color stream under an explicit D3D9 declaration type."""
    kind = str(d3d9_type).upper()
    candidate = D3D9_COLOR_TYPES.get(kind)
    if candidate is None:
        raise ValueError(f"unsupported D3D9 color type {d3d9_type!r}")
    return interpret_color_bytes(payload, candidate["order"])


def interpret_color_bytes(payload: bytes, order: str) -> bytes:
    """Interpret packed 4-byte samples according to an explicit channel order."""
    order = str(order).upper()
    if order not in CANDIDATE_ORDERS:
        raise ValueError(f"unsupported color channel order {order!r}")
    if len(payload) % 4:
        raise ValueError("color payload must be divisible by four bytes")

    out = bytearray(len(payload))
    for offset in range(0, len(payload), 4):
        c0, c1, c2, c3 = payload[offset:offset + 4]
        if order == "RGBA":
            rgba = (c0, c1, c2, c3)
        else:
            rgba = (c2, c1, c0, c3)
        out[offset:offset + 4] = bytes(rgba)
    return bytes(out)


def _channel_stats(rgba: bytes) -> dict[str, Any]:
    if len(rgba) % 4:
        raise ValueError("RGBA payload must be divisible by four bytes")
    samples = len(rgba) // 4
    if samples == 0:
        return {
            "samples": 0,
            "alpha_non_opaque": 0,
            "alpha_min": None,
            "alpha_max": None,
            "channel_means": [0.0, 0.0, 0.0, 0.0],
        }

    sums = [0, 0, 0, 0]
    alpha_values = []
    for i in range(0, len(rgba), 4):
        row = rgba[i:i + 4]
        for channel in range(4):
            sums[channel] += row[channel]
        alpha_values.append(row[3])

    return {
        "samples": samples,
        "alpha_non_opaque": sum(1 for x in alpha_values if x != 255),
        "alpha_min": min(alpha_values),
        "alpha_max": max(alpha_values),
        "channel_means": [value / samples for value in sums],
    }


def build_color_abi_evidence(
    property_id: str,
    payload: bytes | bytearray | Iterable[int],
) -> dict[str, Any]:
    """Return deterministic RGBA/BGRA candidate interpretations for one color stream."""
    raw = bytes(payload)
    _validate_payload(property_id, raw)

    candidates: list[dict[str, Any]] = []
    for order in CANDIDATE_ORDERS:
        rgba = interpret_color_bytes(raw, order)
        candidate_type = D3D9_COLOR_ORDERS[order]
        candidates.append({
            "order": order,
            "d3d9_type": candidate_type["d3d9_type"],
            "memory_order": candidate_type["memory_order"],
            "shader_order": candidate_type["shader_order"],
            "normalized": candidate_type["normalized"],
            "pixel_bytes_sha256": hashlib.sha256(rgba).hexdigest(),
            "stats": _channel_stats(rgba),
            "rgba8_hex": rgba.hex(),
        })

    property_key = str(property_id)
    from meb_d3d9_source_abi import VERIFIED_COLOR_ABI

    source_verified = dict(VERIFIED_COLOR_ABI[property_key])
    for candidate in candidates:
        candidate["source_verified"] = candidate["order"] == source_verified["source_memory_order"]

    return {
        "format": FORMAT,
        "property_id": property_key,
        "element_size": 4,
        "raw_bytes_sha256": hashlib.sha256(raw).hexdigest(),
        "sample_count": len(raw) // 4,
        "confidence": "source-proven",
        "selection": source_verified["source_memory_order"],
        "candidates": candidates,
        "source_verified": source_verified,
        "source_evidence": {
            "format": "SHIFT.MEBD3D9SourceABIEvidence/1",
            "kind": "shift-exe-c",
            "functions": {
                "binary_loader": "FUN_00859800",
                "declaration_builder": "FUN_00854e70",
                "packed_color_helper": "FUN_008310c0",
                "xml_stream_loader": "FUN_008587e0",
            },
            "descriptor_triplet": source_verified["descriptor_triplet"],
            "usage": source_verified["usage"],
            "channel": source_verified["channel"],
            "d3d9_type": source_verified["d3d9_type"],
            "source_memory_order": source_verified["source_memory_order"],
            "shader_order": source_verified["shader_order"],
            "status": "source-correlated-under-MEB-three-u32-property-id-convention",
        },
    }


def compare_color_candidate(
    property_id: str,
    payload: bytes,
    expected_rgba8: bytes,
) -> dict[str, Any]:
    """Compare both explicit channel-order candidates to a known RGBA8 reference."""
    evidence = build_color_abi_evidence(property_id, payload)
    expected = bytes(expected_rgba8)
    if len(expected) != len(payload):
        raise ValueError("expected RGBA8 length must match raw color payload length")

    results = []
    for candidate in evidence["candidates"]:
        rgba = interpret_color_bytes(payload, candidate["order"])
        differing = sum(1 for a, b in zip(rgba, expected) if a != b)
        results.append({
            "order": candidate["order"],
            "d3d9_type": candidate.get("d3d9_type"),
            "memory_order": candidate.get("memory_order"),
            "shader_order": candidate.get("shader_order"),
            "exact_match": differing == 0,
            "differing_bytes": differing,
            "expected_sha256": hashlib.sha256(expected).hexdigest(),
            "candidate_sha256": candidate["pixel_bytes_sha256"],
        })

    return {
        "format": "SHIFT.ColorABICandidateComparison/1",
        "property_id": str(property_id),
        "candidate_results": results,
        "selection": evidence["selection"],
        "source_verified": evidence["source_verified"],
    }



def aggregate_color_abi_evidence(
    reports: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate COLOR evidence reports while preserving the source-proven selection."""
    rows = list(reports)
    by_property: dict[str, list[dict[str, Any]]] = {"460": [], "461": []}
    invalid: list[str] = []
    for index, report in enumerate(rows):
        property_id = str(report.get("property_id") or "")
        if property_id not in SUPPORTED_PROPERTIES:
            invalid.append(f"report-{index}:unsupported-property")
            continue
        if report.get("format") != FORMAT:
            invalid.append(f"report-{index}:invalid-format")
            continue
        by_property[property_id].append(report)

    properties: dict[str, Any] = {}
    for property_id, items in by_property.items():
        candidate_rows: list[dict[str, Any]] = []
        for order in CANDIDATE_ORDERS:
            exact_hashes = []
            mean_channels = []
            for report in items:
                candidate = next(
                    (x for x in report.get("candidates", []) or [] if x.get("order") == order),
                    None,
                )
                if candidate is None:
                    continue
                exact_hashes.append(candidate.get("pixel_bytes_sha256"))
                stats = candidate.get("stats") or {}
                means = stats.get("channel_means")
                if isinstance(means, list) and len(means) == 4:
                    mean_channels.append([float(x) for x in means])
            consensus = len(set(x for x in exact_hashes if x)) <= 1 if exact_hashes else None
            averaged_means = None
            if mean_channels:
                averaged_means = [
                    sum(row[channel] for row in mean_channels) / len(mean_channels)
                    for channel in range(4)
                ]
            candidate_rows.append({
                "order": order,
                "reports": len(exact_hashes),
                "unique_candidate_hashes": sorted(set(x for x in exact_hashes if x)),
                "stable_across_reports": consensus,
                "mean_channel_means": averaged_means,
            })

        source_orders = {
            str(report.get("source_verified", {}).get("source_memory_order"))
            for report in items
            if isinstance(report.get("source_verified"), dict)
        }
        verified_order = (
            next(iter(source_orders))
            if source_orders and len(source_orders) == 1
            else None
        )
        properties[property_id] = {
            "report_count": len(items),
            "candidate_consistency": candidate_rows,
            "selection": verified_order or "not-selected",
            "source_verified": (
                dict(items[0].get("source_verified"))
                if verified_order and items and isinstance(items[0].get("source_verified"), dict)
                else None
            ),
        }

    return {
        "format": "SHIFT.ColorABICorpusEvidence/1",
        "report_count": len(rows),
        "invalid_reports": invalid,
        "properties": properties,
        "selection": "BGRA" if any(
            item.get("selection") == "BGRA" for item in properties.values()
        ) and all(
            item.get("selection") in ("BGRA", "not-selected")
            for item in properties.values()
        ) else "not-selected",
    }
