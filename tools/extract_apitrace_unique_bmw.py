#!/usr/bin/env python3
"""Extract a compact, deduplicated BMW D3D9 geometry evidence set from apitrace.

The input .trace is never materialized as a text dump on disk. For a .trace input
we stream apitrace dump stdout line-by-line, keep only small state/lifecycle
records, and emit a compact artifact set for BMW-like DrawIndexedPrimitive calls.

This tool intentionally does not claim raw VB/IB byte parity: apitrace D3D9 dump
lines expose call/state information, while exact buffer contents remain a separate
runtime-payload evidence boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

FORMAT = "SHIFT.APITRACEUniqueBMWGeometry/1"
DEFAULT_PRIMITIVE_COUNTS = (28, 50, 192, 204, 2098, 2462)

CALL_RE = re.compile(r"^(?P<call>\d+)\s+(?P<iface>[A-Za-z0-9_]+)::(?P<method>\w+)\(")
DRAW_RE = re.compile(
    r"BaseVertexIndex\s*=\s*(-?\d+),\s*"
    r"MinVertexIndex\s*=\s*(\d+),\s*"
    r"NumVertices\s*=\s*(\d+),\s*"
    r"startIndex\s*=\s*(\d+),\s*"
    r"primCount\s*=\s*(\d+)"
)
PTR_RE = r"(?:NULL|0x[0-9a-fA-F]+)"


def _pick(text: str, *names: str) -> str | None:
    for name in names:
        match = re.search(rf"\b{re.escape(name)}\s*=\s*({PTR_RE})", text)
        if match:
            return match.group(1)
    return None


def _pick_out(text: str, *names: str) -> str | None:
    for name in names:
        match = re.search(rf"\b{re.escape(name)}\s*=\s*&?({PTR_RE})", text)
        if match:
            return match.group(1)
    return None


def _integer(text: str, *names: str) -> int | None:
    for name in names:
        match = re.search(rf"\b{re.escape(name)}\s*=\s*(-?\d+)", text)
        if match:
            return int(match.group(1))
    return None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        while chunk := fp.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _source_lines(path: Path, apitrace: str) -> Iterator[str]:
    if path.suffix.lower() != ".trace":
        with path.open("r", encoding="utf-8", errors="replace") as fp:
            yield from (line.rstrip("\n") for line in fp)
        return

    proc = subprocess.Popen(
        [apitrace, "dump", "--call-nos=true", "--arg-names=true", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            yield line.rstrip("\n")
    finally:
        proc.stdout.close()
        stderr = proc.stderr.read() if proc.stderr else ""
        rc = proc.wait()
        if rc:
            raise RuntimeError(f"apitrace dump failed ({rc}): {stderr[-4000:]}")


@dataclass
class Ref:
    call: int
    raw: str
    pointer: str | None = None

    def json(self) -> dict:
        out = {"call": self.call, "raw": self.raw}
        if self.pointer is not None:
            out["pointer"] = self.pointer
        return out


@dataclass
class Creation:
    kind: str
    call: int
    pointer: str
    raw: str

    def json(self) -> dict:
        return {
            "kind": self.kind,
            "call": self.call,
            "pointer": self.pointer,
            "raw": self.raw,
        }


@dataclass
class Lifecycle:
    lock_calls: list[int]
    unlock_calls: list[int]
    desc_calls: list[int]
    release_calls: list[int]
    lock_count: int
    unlock_count: int
    desc_count: int
    release_count: int

    def __init__(self) -> None:
        self.lock_calls = []
        self.unlock_calls = []
        self.desc_calls = []
        self.release_calls = []
        self.lock_count = 0
        self.unlock_count = 0
        self.desc_count = 0
        self.release_count = 0

    @staticmethod
    def _append_bounded(values: list[int], call: int, limit: int = 32) -> None:
        if len(values) < limit:
            values.append(call)

    def json(self) -> dict:
        return {
            "lock_calls": self.lock_calls,
            "unlock_calls": self.unlock_calls,
            "getdesc_calls": self.desc_calls,
            "release_calls": self.release_calls,
            "counts": {
                "lock": self.lock_count,
                "unlock": self.unlock_count,
                "getdesc": self.desc_count,
                "release": self.release_count,
            },
        }


class State:
    def __init__(self) -> None:
        self.decl: Ref | None = None
        self.streams: dict[int, Ref] = {}
        self.indices: Ref | None = None
        self.vs: Ref | None = None
        self.ps: Ref | None = None
        self.textures: dict[int, Ref] = {}
        self.created: dict[str, dict[str, list[Creation]]] = {
            "decl": {},
            "vb": {},
            "ib": {},
            "vs": {},
            "ps": {},
            "tex": {},
        }
        self.released: dict[str, dict[str, list[int]]] = {
            kind: {} for kind in self.created
        }
        self.lifecycle: dict[str, dict[str, Lifecycle]] = {
            "vb": {},
            "ib": {},
        }

    def add_creation(
        self, kind: str, pointer: str | None, call: int, raw: str
    ) -> None:
        if not pointer or pointer == "NULL":
            return
        self.created[kind].setdefault(pointer, []).append(
            Creation(kind, call, pointer, raw)
        )
        if kind in self.lifecycle:
            self.lifecycle[kind].setdefault(pointer, Lifecycle())

    def add_release(self, kind: str, pointer: str | None, call: int) -> None:
        if not pointer or pointer == "NULL":
            return
        self.released[kind].setdefault(pointer, []).append(call)
        if kind in self.lifecycle:
            life = self.lifecycle[kind].setdefault(pointer, Lifecycle())
            life.release_count += 1
            Lifecycle._append_bounded(life.release_calls, call)

    def active_creation(
        self, kind: str, pointer: str | None, at_call: int
    ) -> Creation | None:
        if not pointer or pointer == "NULL":
            return None
        creations = self.created[kind].get(pointer, [])
        releases = self.released[kind].get(pointer, [])
        last_release = max(
            (rel for rel in releases if rel < at_call), default=-1
        )
        for creation in reversed(creations):
            if creation.call > at_call or creation.call <= last_release:
                continue
            return creation
        return None

    def lifecycle_event(
        self, kind: str, pointer: str | None, method: str, call: int
    ) -> None:
        if kind not in self.lifecycle or not pointer or pointer == "NULL":
            return
        life = self.lifecycle[kind].setdefault(pointer, Lifecycle())
        if method == "Lock":
            life.lock_count += 1
            Lifecycle._append_bounded(life.lock_calls, call)
        elif method == "Unlock":
            life.unlock_count += 1
            Lifecycle._append_bounded(life.unlock_calls, call)
        elif method == "GetDesc":
            life.desc_count += 1
            Lifecycle._append_bounded(life.desc_calls, call)

    def snapshot(
        self,
        draw_call: int,
        include_shaders: bool = False,
        include_textures: bool = False,
    ) -> dict:
        streams = {
            str(k): ref.json() for k, ref in sorted(self.streams.items())
        }
        out = {
            "draw_call": draw_call,
            "vertex_declaration": self.decl.json() if self.decl else None,
            "streams": streams,
            "index_buffer": self.indices.json() if self.indices else None,
        }
        if include_shaders:
            out["vertex_shader"] = self.vs.json() if self.vs else None
            out["pixel_shader"] = self.ps.json() if self.ps else None
        if include_textures:
            out["textures"] = {
                str(k): ref.json() for k, ref in sorted(self.textures.items())
            }
        return out

    def geometry_key(self, draw_call: int) -> tuple:
        stream_key = []
        for k, ref in sorted(self.streams.items()):
            creation = self.active_creation("vb", ref.pointer, draw_call)
            stream_key.append(
                (
                    int(k),
                    ref.pointer,
                    creation.call if creation else None,
                    _integer(ref.raw, "OffsetInBytes") or 0,
                    _integer(ref.raw, "Stride") or 0,
                )
            )
        decl_creation = self.active_creation(
            "decl", self.decl.pointer if self.decl else None, draw_call
        )
        ib_creation = self.active_creation(
            "ib", self.indices.pointer if self.indices else None, draw_call
        )
        return (
            (
                self.decl.pointer if self.decl else None,
                decl_creation.call if decl_creation else None,
            ),
            tuple(stream_key),
            (
                self.indices.pointer if self.indices else None,
                ib_creation.call if ib_creation else None,
            ),
        )


def _interface_kind(iface: str) -> str | None:
    if iface == "IDirect3DVertexBuffer9":
        return "vb"
    if iface == "IDirect3DIndexBuffer9":
        return "ib"
    if iface == "IDirect3DVertexDeclaration9":
        return "decl"
    if iface == "IDirect3DVertexShader9":
        return "vs"
    if iface == "IDirect3DPixelShader9":
        return "ps"
    if iface in {
        "IDirect3DTexture9",
        "IDirect3DCubeTexture9",
        "IDirect3DVolumeTexture9",
    }:
        return "tex"
    return None


def update(
    state: State, call: int, iface: str, method: str, raw: str
) -> None:
    if iface == "IDirect3DDevice9":
        if method == "SetVertexDeclaration":
            state.decl = Ref(call, raw, _pick(raw, "pDecl"))
        elif method == "SetStreamSource":
            n = _integer(raw, "StreamNumber", "Stream")
            p = _pick(raw, "pStreamData")
            if n is not None:
                state.streams[n] = Ref(call, raw, p)
        elif method == "SetIndices":
            state.indices = Ref(call, raw, _pick(raw, "pIndexData"))
        elif method == "SetVertexShader":
            state.vs = Ref(call, raw, _pick(raw, "pShader"))
        elif method == "SetPixelShader":
            state.ps = Ref(call, raw, _pick(raw, "pShader"))
        elif method == "SetTexture":
            n = _integer(raw, "Stage")
            if n is not None:
                state.textures[n] = Ref(call, raw, _pick(raw, "pTexture"))
        elif method == "CreateVertexBuffer":
            state.add_creation(
                "vb", _pick_out(raw, "ppVertexBuffer"), call, raw
            )
        elif method == "CreateIndexBuffer":
            state.add_creation(
                "ib", _pick_out(raw, "ppIndexBuffer"), call, raw
            )
        elif method == "CreateVertexDeclaration":
            state.add_creation("decl", _pick_out(raw, "ppDecl"), call, raw)
        elif method == "CreateVertexShader":
            state.add_creation("vs", _pick_out(raw, "ppShader"), call, raw)
        elif method == "CreatePixelShader":
            state.add_creation("ps", _pick_out(raw, "ppShader"), call, raw)
        elif method in {
            "CreateTexture",
            "CreateCubeTexture",
            "CreateVolumeTexture",
        }:
            state.add_creation(
                "tex",
                _pick_out(
                    raw, "ppTexture", "ppCubeTexture", "ppVolumeTexture"
                ),
                call,
                raw,
            )
        return

    kind = _interface_kind(iface)
    if kind in {"vb", "ib"}:
        pointer = _pick(raw, "this")
        state.lifecycle_event(kind, pointer, method, call)
        if method == "Release":
            state.add_release(kind, pointer, call)


def _geometry_resources(state: State, draw_call: int) -> dict:
    resources: dict[str, dict] = {}
    stream0 = state.streams.get(0)
    if stream0 and stream0.pointer and stream0.pointer != "NULL":
        creation = state.active_creation("vb", stream0.pointer, draw_call)
        stride = _integer(stream0.raw, "Stride")
        resources["vertex_buffer"] = {
            "pointer": stream0.pointer,
            "binding_call": stream0.call,
            "offset_bytes": _integer(stream0.raw, "OffsetInBytes"),
            "stride": stride,
            "derived_bytes_if_num_vertices_times_stride": None,
            "creation": creation.json() if creation else None,
            "same_instance": creation is not None,
        }

    index = state.indices
    if index and index.pointer and index.pointer != "NULL":
        creation = state.active_creation("ib", index.pointer, draw_call)
        resources["index_buffer"] = {
            "pointer": index.pointer,
            "binding_call": index.call,
            "creation": creation.json() if creation else None,
            "same_instance": creation is not None,
            "lifecycle": state.lifecycle.get("ib", {})
            .get(index.pointer, Lifecycle())
            .json(),
        }
    return resources


def extract(
    input_path: Path,
    output_dir: Path,
    *,
    apitrace: str = "apitrace",
    primitive_counts: tuple[int, ...] = DEFAULT_PRIMITIVE_COUNTS,
    target_vertex_count: int = 3550,
    include_shaders: bool = False,
    include_textures: bool = False,
    progress_every: int = 5_000_000,
    auto_trim: bool = False,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    state = State()
    primitive_set = set(primitive_counts)
    target_counts: Counter[int] = Counter()
    unique: dict[tuple, dict] = {}
    relevant_calls: dict[int, str] = {}
    line_count = 0
    draw_count = 0
    target_draw_calls: list[int] = []
    source_kind = (
        "trace" if input_path.suffix.lower() == ".trace" else "text_dump"
    )

    for line in _source_lines(input_path, apitrace):
        line_count += 1
        m = CALL_RE.match(line)
        if not m:
            if progress_every and line_count % progress_every == 0:
                print(
                    f"[apitrace-extract] scanned {line_count:,} lines",
                    file=sys.stderr,
                )
            continue

        call = int(m.group("call"))
        iface = m.group("iface")
        method = m.group("method")

        if iface == "IDirect3DDevice9" and method == "DrawIndexedPrimitive":
            dm = DRAW_RE.search(line)
            if not dm:
                continue
            draw_count += 1
            base = int(dm.group(1))
            min_vertex = int(dm.group(2))
            nv = int(dm.group(3))
            start_index = int(dm.group(4))
            prim = int(dm.group(5))
            if nv != target_vertex_count or prim not in primitive_set:
                continue

            target_counts[prim] += 1
            target_draw_calls.append(call)
            geometry = state.geometry_key(call)

            if geometry not in unique:
                snapshot = state.snapshot(
                    call, include_shaders, include_textures
                )
                resources = _geometry_resources(state, call)
                if "vertex_buffer" in resources:
                    stride = resources["vertex_buffer"].get("stride")
                    resources["vertex_buffer"][
                        "derived_bytes_if_num_vertices_times_stride"
                    ] = (
                        nv * stride if stride is not None else None
                    )

                key = hashlib.sha256(
                    json.dumps(
                        geometry,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()

                unique[geometry] = {
                    "geometry_key_sha256": key,
                    "first_draw_call": call,
                    "last_draw_call": call,
                    "draw_count": 1,
                    "primitive_counts": [prim],
                    "draws": [
                        {
                            "call": call,
                            "base_vertex_index": base,
                            "min_vertex_index": min_vertex,
                            "num_vertices": nv,
                            "start_index": start_index,
                            "prim_count": prim,
                        }
                    ],
                    "state": snapshot,
                    "resources": resources,
                }

                relevant_calls[call] = line
                for ref, kind in [
                    (state.decl, "decl"),
                    (state.indices, "ib"),
                    *[
                        (ref, "vb")
                        for _, ref in sorted(state.streams.items())
                    ],
                ]:
                    if not ref:
                        continue
                    relevant_calls[ref.call] = ref.raw
                    creation = state.active_creation(kind, ref.pointer, call)
                    if creation:
                        relevant_calls[creation.call] = creation.raw
            else:
                item = unique[geometry]
                item["last_draw_call"] = call
                item["draw_count"] += 1
                if prim not in item["primitive_counts"]:
                    item["primitive_counts"].append(prim)
                if len(item["draws"]) < 8:
                    item["draws"].append(
                        {
                            "call": call,
                            "base_vertex_index": base,
                            "min_vertex_index": min_vertex,
                            "num_vertices": nv,
                            "start_index": start_index,
                            "prim_count": prim,
                        }
                    )
            continue

        update(state, call, iface, method, line)

        if progress_every and line_count % progress_every == 0:
            print(
                f"[apitrace-extract] scanned {line_count:,} lines",
                file=sys.stderr,
            )

    unique_rows = sorted(
        unique.values(),
        key=lambda x: (min(x["primitive_counts"]), x["first_draw_call"]),
    )

    resources_index: dict[str, list] = {
        "vertex_buffers": [],
        "index_buffers": [],
    }
    seen_resources: set[tuple[str, str, int | None]] = set()
    callset = set(relevant_calls)

    for row in unique_rows:
        for bucket, key_name in [
            ("vertex_buffers", "vertex_buffer"),
            ("index_buffers", "index_buffer"),
        ]:
            resource = row["resources"].get(key_name)
            if not resource:
                continue
            creation = resource.get("creation") or {}
            marker = (
                bucket,
                resource.get("pointer"),
                creation.get("call"),
            )
            if marker in seen_resources:
                continue
            seen_resources.add(marker)
            payload = dict(resource)
            if bucket == "ib":
                lifecycle = {}
            payload["lifecycle"] = (
                state.lifecycle.get("ib", {})
                .get(resource["pointer"], Lifecycle())
                .json()
                if bucket == "index_buffers"
                else state.lifecycle.get("vb", {})
                .get(resource["pointer"], Lifecycle())
                .json()
            )
            resources_index[bucket].append(payload)
            if creation.get("call") is not None:
                callset.add(int(creation["call"]))

    representative_calls = sorted(
        {row["first_draw_call"] for row in unique_rows}
    )
    compact_calls = sorted(
        (call, raw) for call, raw in relevant_calls.items()
    )

    trim_report = {
        "requested": auto_trim,
        "status": "not-requested",
        "output": None,
        "calls": representative_calls,
    }
    if auto_trim and source_kind != "trace":
        trim_report["status"] = "unsupported-for-text-dump"
    elif auto_trim and not representative_calls:
        trim_report["status"] = "not-found"
    elif auto_trim:
        trimmed_path = output_dir / "bmw_unique.trace"
        callset_arg = ",".join(str(call) for call in representative_calls)
        command = [
            apitrace,
            "trim",
            "--auto",
            f"--calls={callset_arg}",
            "-o",
            str(trimmed_path),
            str(input_path),
        ]
        trim_report["command"] = command
        try:
            subprocess.run(command, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            trim_report["status"] = "failed"
            trim_report["error"] = str(exc)
        else:
            trim_report["status"] = "created"
            trim_report["output"] = str(trimmed_path)

    report = {
        "format": FORMAT,
        "source": {
            "path": str(input_path),
            "kind": source_kind,
            "size_bytes": input_path.stat().st_size,
            "sha256": (
                _sha256_file(input_path)
                if source_kind == "text_dump"
                else None
            ),
        },
        "scan": {
            "lines": line_count,
            "draw_calls": draw_count,
            "target_vertex_count": target_vertex_count,
            "target_primitive_counts": sorted(primitive_set),
            "target_draw_count": sum(target_counts.values()),
            "target_draw_counts_by_primitive": dict(
                sorted(target_counts.items())
            ),
            "unique_geometry_bindings": len(unique_rows),
            "representative_calls": representative_calls,
        },
        "geometry": unique_rows,
        "resources": resources_index,
        "callset": sorted(callset),
        "trim": trim_report,
        "evidence_boundary": {
            "draw_geometry_signature": (
                "observed" if unique_rows else "not-observed"
            ),
            "vb_identity": (
                "observed"
                if any(
                    row.get("resources", {}).get("vertex_buffer")
                    for row in unique_rows
                )
                else "not-observed"
            ),
            "ib_identity": (
                "observed"
                if any(
                    row.get("resources", {}).get("index_buffer")
                    for row in unique_rows
                )
                else "not-observed"
            ),
            "exact_vb_bytes": "not-observed",
            "exact_ib_bytes": "not-observed",
            "raw_runtime_payload_parity": "not-proven",
        },
    }

    (output_dir / "unique_bmw_geometry.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    with (output_dir / "compact_relevant_calls.txt").open(
        "w", encoding="utf-8"
    ) as fp:
        for call, raw in compact_calls:
            fp.write(f"{call} {raw}\n")

    with (output_dir / "callset.txt").open("w", encoding="utf-8") as fp:
        for call in sorted(callset):
            fp.write(f"{call}\n")

    summary = {
        "format": FORMAT,
        "status": "observed" if unique_rows else "not-found",
        "input": str(input_path),
        "output": str(output_dir),
        "source_kind": source_kind,
        "lines_scanned": line_count,
        "draw_calls_scanned": draw_count,
        "target_draw_count": sum(target_counts.values()),
        "target_draw_counts_by_primitive": dict(
            sorted(target_counts.items())
        ),
        "unique_geometry_bindings": len(unique_rows),
        "compact_call_count": len(compact_calls),
        "callset_count": len(callset),
        "trim_status": trim_report["status"],
        "trim_output": trim_report.get("output"),
    }

    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return summary


def _parse_counts(value: str) -> tuple[int, ...]:
    values = tuple(
        sorted({int(part.strip()) for part in value.split(",") if part.strip()})
    )
    if not values:
        raise argparse.ArgumentTypeError(
            "at least one primitive count is required"
        )
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", help="apitrace .trace or existing text dump")
    parser.add_argument(
        "output_dir", help="compact output directory"
    )
    parser.add_argument("--apitrace", default="apitrace")
    parser.add_argument("--vertex-count", type=int, default=3550)
    parser.add_argument(
        "--primitive-counts",
        type=_parse_counts,
        default=DEFAULT_PRIMITIVE_COUNTS,
    )
    parser.add_argument("--include-shaders", action="store_true")
    parser.add_argument("--include-textures", action="store_true")
    parser.add_argument("--progress-every", type=int, default=5_000_000)
    parser.add_argument(
        "--auto-trim",
        action="store_true",
        help=(
            "After target discovery, run apitrace trim --auto "
            "for representative draw calls"
        ),
    )
    args = parser.parse_args(argv)

    summary = extract(
        Path(args.trace).expanduser().resolve(),
        Path(args.output_dir).expanduser().resolve(),
        apitrace=args.apitrace,
        primitive_counts=args.primitive_counts,
        target_vertex_count=args.vertex_count,
        include_shaders=args.include_shaders,
        include_textures=args.include_textures,
        progress_every=max(0, args.progress_every),
        auto_trim=args.auto_trim,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
