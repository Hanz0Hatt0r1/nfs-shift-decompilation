"""Extract conservative BMW target-draw evidence from an apitrace D3D9 dump.

This intentionally does not infer declaration/resource/shader identity from draw
geometry alone. It records only what a DrawIndexedPrimitive text dump can prove.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Iterable

FORMAT = "SHIFT.APITRACEDrawEvidence/1"
TARGET_VERTEX_COUNT = 3550
PAINT_RANGES = (
    {"primitive_index": 1, "first_index": 150, "index_count": 6294},
    {"primitive_index": 2, "first_index": 6444, "index_count": 7386},
)
DRAW_RE = re.compile(
    rb"^(?P<call>\d+) .*?"
    rb"BaseVertexIndex = (?P<base>-?\d+), "
    rb"MinVertexIndex = (?P<min>\d+), "
    rb"NumVertices = (?P<nv>\d+), "
    rb"startIndex = (?P<start>\d+), "
    rb"primCount = (?P<prim>\d+)"
)


def _open_input(path: Path) -> tuple[Iterable[bytes], str]:
    if path.suffix.lower() != ".zip":
        f = open(path, "rb")
        return f, str(path)

    zf = zipfile.ZipFile(path)
    candidates = [info for info in zf.infolist() if not info.is_dir() and info.file_size]
    if not candidates:
        zf.close()
        raise ValueError("zip contains no non-empty files")
    candidates.sort(
        key=lambda i: (
            0 if Path(i.filename).suffix.lower() in {".txt", ".log", ".dump"} else 1,
            i.filename,
        )
    )
    stream = zf.open(candidates[0], "r")
    return _ZipLineStream(stream, zf), candidates[0].filename


class _ZipLineStream:
    def __init__(self, stream, zf):
        self.stream = stream
        self.zf = zf

    def __iter__(self):
        return iter(self.stream)

    def close(self):
        self.stream.close()
        self.zf.close()


def analyze(path: str | Path, *, top_n: int = 25) -> dict:
    input_path = Path(path)
    source, source_name = _open_input(input_path)
    sha = hashlib.sha256()
    line_count = 0
    draw_count = 0
    call_min = None
    call_max = None
    tuple_counts: Counter[tuple[int, int, int]] = Counter()
    pair_counts: Counter[
        tuple[tuple[int, int, int], tuple[int, int, int]]
    ] = Counter()
    target_counts: Counter[str] = Counter()
    target_first: dict[str, list[int]] = {"paint_1": [], "paint_2": []}
    target_last: dict[str, int | None] = {"paint_1": None, "paint_2": None}
    target_pairs = Counter()
    start_index_observed = Counter()
    prev = None

    try:
        for raw in source:
            line_count += 1
            sha.update(raw)
            m = DRAW_RE.match(raw)
            if not m:
                continue

            draw_count += 1
            call = int(m.group("call"))
            nv = int(m.group("nv"))
            start = int(m.group("start"))
            prim = int(m.group("prim"))
            sig = (nv, start, prim)
            tuple_counts[sig] += 1
            call_min = call if call_min is None else min(call_min, call)
            call_max = call if call_max is None else max(call_max, call)

            if prev is not None:
                pair_counts[(prev, sig)] += 1
            prev = sig

            if nv == TARGET_VERTEX_COUNT and prim == 2098:
                target_counts["paint_1"] += 1
                start_index_observed["paint_1"] += start
                target_last["paint_1"] = call
                if len(target_first["paint_1"]) < top_n:
                    target_first["paint_1"].append(call)

            if nv == TARGET_VERTEX_COUNT and prim == 2462:
                target_counts["paint_2"] += 1
                start_index_observed["paint_2"] += start
                target_last["paint_2"] = call
                if len(target_first["paint_2"]) < top_n:
                    target_first["paint_2"].append(call)
    finally:
        close = getattr(source, "close", None)
        if close:
            close()

    sig_1 = (TARGET_VERTEX_COUNT, 0, 2098)
    sig_2 = (TARGET_VERTEX_COUNT, 0, 2462)
    for a, b in ((sig_1, sig_2), (sig_2, sig_1)):
        target_pairs[f"{a[2]}->{b[2]}"] = pair_counts[(a, b)]

    expected = {"paint_1": PAINT_RANGES[0], "paint_2": PAINT_RANGES[1]}
    targets = {}
    for key, paint in expected.items():
        prim = paint["index_count"] // 3
        observed_sig = (TARGET_VERTEX_COUNT, 0, prim)
        targets[key] = {
            **paint,
            "expected_primitive_count": prim,
            "observed": target_counts[key] > 0,
            "observed_draw_count": target_counts[key],
            "observed_signature": {
                "num_vertices": TARGET_VERTEX_COUNT,
                "start_index": 0,
                "primitive_count": prim,
            },
            "index_count_match": True,
            "start_index_match": False,
            "observed_start_index_total": start_index_observed[key],
            "observed_signature_count": tuple_counts[observed_sig],
            "first_call_numbers": target_first[key],
            "last_call_number": target_last[key],
        }

    target_bundle_pairs = [
        {
            "from_primitive_count": a[2],
            "to_primitive_count": b[2],
            "count": c,
        }
        for (a, b), c in pair_counts.items()
        if a[0] == TARGET_VERTEX_COUNT and b[0] == TARGET_VERTEX_COUNT
    ]
    target_bundle_pairs.sort(
        key=lambda row: (
            -row["count"],
            row["from_primitive_count"],
            row["to_primitive_count"],
        )
    )

    return {
        "format": FORMAT,
        "status": "observed" if any(v["observed"] for v in targets.values()) else "not-found",
        "ready": False,
        "source": {
            "path": str(input_path),
            "member": source_name if source_name != str(input_path) else None,
            "sha256": sha.hexdigest(),
            "line_count": line_count,
            "draw_count": draw_count,
            "call_number_min": call_min,
            "call_number_max": call_max,
        },
        "target": {
            "vertex_count": TARGET_VERTEX_COUNT,
            "paint_ranges": targets,
            "adjacent_target_pairs": dict(target_pairs),
            "vertex_count_bundle_adjacency": target_bundle_pairs[:25],
        },
        "top_draw_signatures": [
            {
                "num_vertices": nv,
                "start_index": start,
                "primitive_count": prim,
                "count": count,
            }
            for (nv, start, prim), count in tuple_counts.most_common(top_n)
        ],
        "evidence_boundary": {
            "geometry_signature": "observed"
            if any(v["observed"] for v in targets.values())
            else "not-observed",
            "target_index_count": "observed"
            if any(v["observed"] for v in targets.values())
            else "not-observed",
            "exact_start_index_mapping": "not-proven",
            "vertex_declaration_instance": "not-observed",
            "vertex_buffer_identity": "not-observed",
            "index_buffer_identity": "not-observed",
            "shader_identity": "not-observed",
            "texture_identity": "not-observed",
            "same_instance_gate": "not-proven",
        },
        "blocking_reasons": [
            "apitrace-draw-dump-lacks-declaration-resource-state",
            "apitrace-draw-dump-lacks-shader-binding-state",
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--top", type=int, default=25)
    args = p.parse_args()
    report = analyze(args.input, top_n=max(1, args.top))
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "format": report["format"],
                "status": report["status"],
                "ready": report["ready"],
                "draw_count": report["source"]["draw_count"],
                "paint_1": report["target"]["paint_ranges"]["paint_1"]["observed_draw_count"],
                "paint_2": report["target"]["paint_ranges"]["paint_2"]["observed_draw_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
