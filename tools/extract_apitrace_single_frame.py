#!/usr/bin/env python3
"""Extract one self-contained apitrace frame for offline analysis.

The preferred mode is --auto-bmw. It scans the original .trace once, finds the
frame containing the strongest BMW M3 target-draw signature set, and then uses
apitrace trim --auto on the exact call range of that frame. This preserves the
frame-local calls while asking apitrace to add replay dependencies.

The original multi-gigabyte trace is never rewritten or expanded to a permanent
text dump. Only the compact output trace and a JSON manifest are written.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

from tools.extract_apitrace_unique_bmw import (
    CALL_RE,
    DRAW_RE,
    State,
    _load_runtime_geometry,
    update,
)

FORMAT = "SHIFT.APITRACESingleFrameTrace/1"
DEFAULT_PRIMITIVES = (28, 50, 192, 204, 2098, 2462)

@dataclass
class FrameCandidate:
    index: int
    start_call: int
    end_call: int | None = None
    target_draw_calls: list[int] = field(default_factory=list)
    primitive_counts: set[int] = field(default_factory=set)

    @property
    def score(self) -> tuple[int, int, int]:
        return (
            len(self.primitive_counts),
            len(self.target_draw_calls),
            int(2098 in self.primitive_counts)
            + int(2462 in self.primitive_counts),
        )

    def json(self) -> dict:
        return {
            "frame_index": self.index,
            "start_call": self.start_call,
            "end_call": self.end_call,
            "target_draw_calls": list(self.target_draw_calls),
            "primitive_counts": sorted(self.primitive_counts),
            "score": list(self.score),
        }


def _dump_lines(trace: Path, apitrace: str) -> Iterator[str]:
    if trace.suffix.lower() != ".trace":
        with trace.open("r", encoding="utf-8", errors="replace") as fp:
            yield from (line.rstrip("\n") for line in fp)
        return

    proc = subprocess.Popen(
        [
            apitrace,
            "dump",
            "--call-nos=true",
            "--arg-names=true",
            str(trace),
        ],
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
            raise RuntimeError(
                f"apitrace dump failed ({rc}): {stderr[-4000:]}"
            )


def _parse_pointer_targets(path: Path | None) -> tuple[str | None, dict[int, str]]:
    if path is None:
        return None, {}
    vb, _, ibs = _load_runtime_geometry(path)
    return vb, ibs


def _finalize_frame(
    current: FrameCandidate,
    best: FrameCandidate | None,
) -> FrameCandidate | None:
    if current.target_draw_calls and (
        best is None or current.score > best.score
    ):
        return current
    return best


def find_bmw_frame(
    trace: Path,
    *,
    apitrace: str = "apitrace",
    target_vertex_count: int = 3550,
    primitive_counts: tuple[int, ...] = DEFAULT_PRIMITIVES,
    target_vertex_buffer: str | None = None,
    target_index_buffers: dict[int, str] | None = None,
) -> dict:
    primitive_set = set(primitive_counts)
    target_index_buffers = target_index_buffers or {}
    state = State()
    current = FrameCandidate(index=0, start_call=0)
    best: FrameCandidate | None = None
    frame_count = 0
    draw_count = 0

    for line in _dump_lines(trace, apitrace):
        m = CALL_RE.match(line)
        if not m:
            continue

        call = int(m.group("call"))
        iface = m.group("iface")
        method = m.group("method")

        if method in {"Present", "PresentEx"}:
            current.end_call = call
            best = _finalize_frame(current, best)
            frame_count += 1
            current = FrameCandidate(index=frame_count, start_call=call + 1)
            continue

        if iface == "IDirect3DDevice9" and method == "DrawIndexedPrimitive":
            dm = DRAW_RE.search(line)
            if dm:
                nv = int(dm.group(3))
                primitive = int(dm.group(5))
                if nv == target_vertex_count and primitive in primitive_set:
                    stream0 = state.streams.get(0)
                    vb_pointer = stream0.pointer if stream0 else None
                    if (
                        target_vertex_buffer is None
                        or vb_pointer == target_vertex_buffer
                    ):
                        expected_ib = target_index_buffers.get(primitive)
                        index_pointer = (
                            state.indices.pointer if state.indices else None
                        )
                        if expected_ib is None or index_pointer == expected_ib:
                            current.target_draw_calls.append(call)
                            current.primitive_counts.add(primitive)
                            draw_count += 1

        update(state, call, iface, method, line)

    if current.target_draw_calls:
        best = _finalize_frame(current, best)

    if best is None:
        raise RuntimeError(
            "no BMW target frame found; provide --frame or inspect the trace manually"
        )

    return {
        "status": "observed",
        "frame": best.json(),
        "frame_count_observed": frame_count,
        "target_draw_count": draw_count,
        "selection": "best-frame-by-target-primitive-coverage",
    }


def find_draw_frame(
    trace: Path,
    draw_call: int,
    *,
    apitrace: str = "apitrace",
) -> dict:
    if draw_call < 0:
        raise ValueError("draw-call must be >= 0")

    state = State()
    current = FrameCandidate(index=0, start_call=0)
    frame_count = 0
    selected: FrameCandidate | None = None

    for line in _dump_lines(trace, apitrace):
        m = CALL_RE.match(line)
        if not m:
            continue

        call = int(m.group("call"))
        iface = m.group("iface")
        method = m.group("method")

        if method in {"Present", "PresentEx"}:
            current.end_call = call
            if draw_call >= current.start_call and call >= draw_call:
                if selected is not None:
                    selected.end_call = call
                    break
            frame_count += 1
            current = FrameCandidate(index=frame_count, start_call=call + 1)
            continue

        if call == draw_call:
            selected = current
            selected.target_draw_calls.append(call)

        update(state, call, iface, method, line)

    if selected is None:
        raise RuntimeError(f"draw call {draw_call} was not found")

    if selected.end_call is None:
        raise RuntimeError(
            f"draw call {draw_call} has no following Present/PresentEx frame boundary"
        )

    return {
        "status": "observed",
        "frame": selected.json(),
        "frame_count_observed": frame_count,
        "selection": "exact-draw-call-frame",
    }


def _run(command: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def trim_call_range(
    trace: Path,
    output_trace: Path,
    *,
    start_call: int,
    end_call: int,
    apitrace: str = "apitrace",
) -> list[str]:
    if start_call < 0 or end_call < start_call:
        raise ValueError("invalid call range")
    output_trace.parent.mkdir(parents=True, exist_ok=True)
    command = [
        apitrace,
        "trim",
        "--auto",
        f"--calls={start_call}-{end_call}",
        "-o",
        str(output_trace),
        str(trace),
    ]
    _run(command)
    return command


def trim_frame_number(
    trace: Path,
    output_trace: Path,
    *,
    frame: int,
    apitrace: str = "apitrace",
) -> list[str]:
    if frame < 0:
        raise ValueError("frame must be >= 0")
    output_trace.parent.mkdir(parents=True, exist_ok=True)
    command = [
        apitrace,
        "trim",
        "--auto",
        f"--frames={frame}/frame",
        "-o",
        str(output_trace),
        str(trace),
    ]
    _run(command)
    return command


def build_manifest(
    trace: Path,
    output_trace: Path,
    *,
    mode: str,
    command: list[str],
    selection: dict,
) -> dict:
    return {
        "format": FORMAT,
        "status": "created" if output_trace.is_file() else "not-created",
        "ready": output_trace.is_file(),
        "source": {
            "path": str(trace),
            "size_bytes": trace.stat().st_size,
        },
        "output": {
            "path": str(output_trace),
            "size_bytes": output_trace.stat().st_size
            if output_trace.is_file()
            else None,
        },
        "mode": mode,
        "trim_command": command,
        "selection": selection,
        "evidence_boundary": {
            "single_frame_trace": (
                "created" if output_trace.is_file() else "not-created"
            ),
            "resource_replay_dependencies": (
                "requested-via-auto-trim"
                if output_trace.is_file()
                else "not-observed"
            ),
            "raw_buffer_payloads": "not-embedded-by-this-tool",
        },
    }


def extract(
    trace: str | Path,
    output_dir: str | Path,
    *,
    frame: int | None = None,
    draw_call: int | None = None,
    auto_bmw: bool = False,
    target_runtime_geometry: str | Path | None = None,
    apitrace: str = "apitrace",
) -> dict:
    trace_path = Path(trace).expanduser().resolve()
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    if not trace_path.is_file():
        raise FileNotFoundError(trace_path)

    modes = sum(x is not None for x in (frame, draw_call)) + int(auto_bmw)
    if modes != 1:
        raise ValueError(
            "choose exactly one of --frame, --draw-call or --auto-bmw"
        )

    vb_pointer = None
    ib_pointers: dict[int, str] = {}
    if target_runtime_geometry is not None:
        vb_pointer, ib_pointers = _parse_pointer_targets(
            Path(target_runtime_geometry).expanduser().resolve()
        )

    output_trace = out / "single_frame.trace"

    if frame is not None:
        command = trim_frame_number(
            trace_path,
            output_trace,
            frame=frame,
            apitrace=apitrace,
        )
        selection = {
            "requested_frame": frame,
            "frame_index": frame,
        }
        mode = "frame"
    elif draw_call is not None:
        scan = find_draw_frame(
            trace_path,
            draw_call,
            apitrace=apitrace,
        )
        selected = scan["frame"]
        command = trim_call_range(
            trace_path,
            output_trace,
            start_call=selected["start_call"],
            end_call=selected["end_call"],
            apitrace=apitrace,
        )
        selection = {
            **scan,
            "requested_draw_call": draw_call,
        }
        mode = "draw-call"
    else:
        scan = find_bmw_frame(
            trace_path,
            apitrace=apitrace,
            target_vertex_buffer=vb_pointer,
            target_index_buffers=ib_pointers,
            target_vertex_count=3550,
            primitive_counts=DEFAULT_PRIMITIVES,
        )
        selected = scan["frame"]
        if selected["end_call"] is None:
            raise RuntimeError(
                "BMW target was found after the last Present; "
                "use --draw-call for a trace without a following frame boundary"
            )
        command = trim_call_range(
            trace_path,
            output_trace,
            start_call=selected["start_call"],
            end_call=selected["end_call"],
            apitrace=apitrace,
        )
        selection = scan
        mode = "auto-bmw"

    manifest = build_manifest(
        trace_path,
        output_trace,
        mode=mode,
        command=command,
        selection=selection,
    )
    manifest_path = out / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("output_dir", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--frame", type=int)
    group.add_argument("--draw-call", type=int)
    group.add_argument("--auto-bmw", action="store_true")
    parser.add_argument("--target-runtime-geometry", type=Path)
    parser.add_argument("--apitrace", default="apitrace")
    args = parser.parse_args(argv)

    result = extract(
        args.trace,
        args.output_dir,
        frame=args.frame,
        draw_call=args.draw_call,
        auto_bmw=args.auto_bmw,
        target_runtime_geometry=args.target_runtime_geometry,
        apitrace=args.apitrace,
    )
    print(
        json.dumps(
            {
                "format": result["format"],
                "status": result["status"],
                "ready": result["ready"],
                "mode": result["mode"],
                "output": result["output"],
                "selection": result["selection"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
