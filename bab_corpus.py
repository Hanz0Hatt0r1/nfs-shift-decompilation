"""Corpus-level fingerprints for opaque SHIFT BAB animation payloads.

This module deliberately does not decode the animation tail. It groups BAB
samples by exact skeleton identity and compares preserved payload metadata so
future keyframe reverse-engineering can work from a measured corpus.
"""
from __future__ import annotations

import hashlib
from typing import Any, Iterable


def _analysis(record: dict[str, Any]) -> dict[str, Any]:
    return record.get("analysis") or record


def skeleton_signature(bab: dict[str, Any]) -> str:
    names = [str(x.get("name", "")) for x in bab.get("bones", []) or []]
    return hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()


def animation_payload_signature(bab: dict[str, Any]) -> dict[str, Any]:
    """Return a stable signature without interpreting opaque animation bytes."""
    bones = list(bab.get("bones", []) or [])
    sha = str(bab.get("animation_payload_sha256") or "")
    size = int(bab.get("animation_payload_size", 0) or 0)
    return {
        "format": "SHIFT.BABAnimationSignature/1",
        "name": bab.get("header", {}).get("name"),
        "version": bab.get("version"),
        "bone_count": len(bones),
        "skeleton_signature": skeleton_signature(bab),
        "animation_payload_offset": bab.get("animation_payload_offset"),
        "animation_payload_size": size,
        "animation_payload_sha256": sha,
        "animation_string_hints": [
            x.get("text")
            for x in bab.get("animation_string_hints", []) or []
            if x.get("text")
        ],
    }


def compare_animation_payloads(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Compare two preserved BAB payloads without decoding their grammar."""
    sa = animation_payload_signature(a)
    sb = animation_payload_signature(b)
    return {
        "format": "SHIFT.BABAnimationComparison/1",
        "same_skeleton": sa["skeleton_signature"] == sb["skeleton_signature"],
        "same_payload": bool(sa["animation_payload_sha256"])
        and sa["animation_payload_sha256"] == sb["animation_payload_sha256"],
        "payload_size_delta": sa["animation_payload_size"] - sb["animation_payload_size"],
        "bone_count_equal": sa["bone_count"] == sb["bone_count"],
        "a": sa,
        "b": sb,
    }


def build_bab_corpus_report(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Group BAB analyses by exact skeleton and report opaque payload diversity."""
    samples = []
    for record in records:
        bab = _analysis(record)
        if bab.get("format") != "SHIFT.BAB":
            continue
        sig = animation_payload_signature(bab)
        samples.append({
            "resource": {
                "archive": record.get("archive"),
                "path": record.get("path"),
            },
            **sig,
        })

    groups: dict[str, list[dict[str, Any]]] = {}
    for sample in samples:
        groups.setdefault(sample["skeleton_signature"], []).append(sample)

    skeleton_groups = []
    for signature, rows in sorted(groups.items()):
        payloads = {x["animation_payload_sha256"] for x in rows if x["animation_payload_sha256"]}
        sizes = sorted({x["animation_payload_size"] for x in rows})
        skeleton_groups.append({
            "skeleton_signature": signature,
            "sample_count": len(rows),
            "payload_hash_count": len(payloads),
            "payload_sizes": sizes,
            "opaque_payloads_vary": len(payloads) > 1 or len(sizes) > 1,
            "samples": sorted(rows, key=lambda x: str(x["resource"].get("path", ""))),
        })

    return {
        "format": "SHIFT.BABCorpusReport/1",
        "sample_count": len(samples),
        "skeleton_group_count": len(skeleton_groups),
        "skeleton_groups": skeleton_groups,
    }
