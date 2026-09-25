#!/usr/bin/env python3
"""Extract D3D9 state immediately before BMW-like target DrawIndexedPrimitive calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

CALL_RE = re.compile(r"^(\d+) IDirect3DDevice9::(\w+)\(")
DRAW_RE = re.compile(
    r"BaseVertexIndex = (-?\d+), .*?MinVertexIndex = (\d+), "
    r"NumVertices = (\d+), startIndex = (\d+), primCount = (\d+)"
)
PTR = r"(?:NULL|0x[0-9a-fA-F]+)"

TARGETS = {
    "paint_1": (3550, 2098),
    "paint_2": (3550, 2462),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def pick(text: str, *names: str) -> str | None:
    for name in names:
        m = re.search(rf"\b{re.escape(name)}\s*=\s*({PTR})", text)
        if m:
            return m.group(1)
    return None


def pick_out(text: str, *names: str) -> str | None:
    for name in names:
        m = re.search(rf"\b{re.escape(name)}\s*=\s*&({PTR})", text)
        if m:
            return m.group(1)
    return None


def integer(text: str, *names: str) -> int | None:
    for name in names:
        m = re.search(rf"\b{re.escape(name)}\s*=\s*(-?\d+)", text)
        if m:
            return int(m.group(1))
    return None


def ref(call: int, raw: str, pointer: str | None = None) -> dict:
    out = {"call": call, "raw": raw}
    if pointer is not None:
        out["pointer"] = pointer
    return out


class State:
    def __init__(self):
        self.decl = None
        self.streams = {}
        self.indices = None
        self.vs = None
        self.ps = None
        self.textures = {}
        self.vs_constants = []
        self.ps_constants = []
        self.created = {
            "decl": {}, "vb": {}, "ib": {}, "vs": {}, "ps": {}, "tex": {}
        }

    def creation(self, kind, pointer):
        if pointer in (None, "NULL"):
            return None
        return self.created[kind].get(pointer)

    def snapshot(self):
        def add_creation(item, kind):
            if not item:
                return None
            result = dict(item)
            result["creation"] = self.creation(kind, item.get("pointer"))
            return result

        return {
            "vertex_declaration": add_creation(self.decl, "decl"),
            "streams": {
                str(k): add_creation(v, "vb") for k, v in sorted(self.streams.items())
            },
            "index_buffer": add_creation(self.indices, "ib"),
            "vertex_shader": add_creation(self.vs, "vs"),
            "pixel_shader": add_creation(self.ps, "ps"),
            "textures": {
                str(k): add_creation(v, "tex") for k, v in sorted(self.textures.items())
            },
            "vertex_constant_writes": list(self.vs_constants),
            "pixel_constant_writes": list(self.ps_constants),
        }


def update(state: State, call: int, method: str, raw: str) -> None:
    if method == "SetVertexDeclaration":
        state.decl = ref(call, raw, pick(raw, "pDecl"))
    elif method == "SetStreamSource":
        n = integer(raw, "StreamNumber", "Stream")
        p = pick(raw, "pStreamData")
        if n is not None:
            state.streams[n] = {**ref(call, raw, p),
                               "offset": integer(raw, "OffsetInBytes"),
                               "stride": integer(raw, "Stride")}
    elif method == "SetIndices":
        state.indices = ref(call, raw, pick(raw, "pIndexData"))
    elif method == "SetVertexShader":
        state.vs = ref(call, raw, pick(raw, "pShader"))
    elif method == "SetPixelShader":
        state.ps = ref(call, raw, pick(raw, "pShader"))
    elif method == "SetTexture":
        n = integer(raw, "Stage")
        if n is not None:
            state.textures[n] = ref(call, raw, pick(raw, "pTexture"))
    elif method in ("SetVertexShaderConstantF", "SetPixelShaderConstantF"):
        item = ref(call, raw)
        item["start_register"] = integer(raw, "StartRegister")
        item["vector4f_count"] = integer(raw, "Vector4fCount")
        (state.vs_constants if method.startswith("SetVertex") else state.ps_constants).append(item)
    elif method == "CreateVertexDeclaration":
        p = pick_out(raw, "ppDecl")
        if p:
            state.created["decl"][p] = ref(call, raw, p)
    elif method == "CreateVertexBuffer":
        p = pick_out(raw, "ppVertexBuffer")
        if p:
            state.created["vb"][p] = ref(call, raw, p)
    elif method == "CreateIndexBuffer":
        p = pick_out(raw, "ppIndexBuffer")
        if p:
            state.created["ib"][p] = ref(call, raw, p)
    elif method == "CreateVertexShader":
        p = pick_out(raw, "ppShader")
        if p:
            state.created["vs"][p] = ref(call, raw, p)
    elif method == "CreatePixelShader":
        p = pick_out(raw, "ppShader")
        if p:
            state.created["ps"][p] = ref(call, raw, p)
    elif method in ("CreateTexture", "CreateCubeTexture", "CreateVolumeTexture"):
        p = pick_out(raw, "ppTexture")
        if p:
            state.created["tex"][p] = ref(call, raw, p)


def source_lines(path: Path, apitrace: str):
    if path.suffix.lower() == ".trace":
        proc = subprocess.Popen(
            [apitrace, "dump", "--call-nos=true", "--arg-names=true", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            yield line.rstrip("\n")
        err = proc.stderr.read() if proc.stderr else ""
        rc = proc.wait()
        if rc:
            raise RuntimeError(f"apitrace dump failed ({rc}): {err[-4000:]}")
    else:
        with path.open(encoding="utf-8", errors="replace") as f:
            yield from (line.rstrip("\n") for line in f)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace", help="SHIFT.trace or an apitrace text dump")
    p.add_argument("output_dir")
    p.add_argument("--max-per-target", type=int, default=50)
    p.add_argument("--start-index", type=int, default=None)
    p.add_argument("--apitrace", default="apitrace")
    args = p.parse_args()

    path = Path(args.trace)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    state = State()
    counts = {name: 0 for name in TARGETS}
    samples = {name: 0 for name in TARGETS}
    snapshots = []

    for line in source_lines(path, args.apitrace):
        m = CALL_RE.match(line)
        if not m:
            continue
        call, method = int(m.group(1)), m.group(2)

        if method != "DrawIndexedPrimitive":
            update(state, call, method, line)
            continue

        dm = DRAW_RE.search(line)
        if not dm:
            continue
        draw = {
            "base_vertex_index": int(dm.group(1)),
            "min_vertex_index": int(dm.group(2)),
            "num_vertices": int(dm.group(3)),
            "start_index": int(dm.group(4)),
            "prim_count": int(dm.group(5)),
        }

        target = next(
            (name for name, (nv, pc) in TARGETS.items()
             if draw["num_vertices"] == nv and draw["prim_count"] == pc
             and (args.start_index is None or draw["start_index"] == args.start_index)),
            None,
        )
        if target is None:
            continue

        counts[target] += 1
        if samples[target] >= max(1, args.max_per_target):
            continue

        snap = state.snapshot()
        snapshots.append({
            "target": target,
            "draw_call": call,
            "draw": draw,
            "state": snap,
        })
        samples[target] += 1

    with (out / "target_draw_context.jsonl").open("w", encoding="utf-8") as f:
        for row in snapshots:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    summary = {
        "format": "SHIFT.APITRACEFullStateEvidence/1",
        "source": {"path": str(path), "sha256": sha256(path)},
        "targets": {
            k: {"observed_draw_count": counts[k], "sampled_snapshot_count": samples[k]}
            for k in TARGETS
        },
        "snapshots": len(snapshots),
        "evidence_boundary": {
            "draw_local_state": "observed" if snapshots else "not-observed",
            "meb_resource_identity": "not-observed",
            "same_instance_gate": "not-proven",
        },
    }
    (out / "target_draw_context_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
