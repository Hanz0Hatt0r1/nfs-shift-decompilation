#!/usr/bin/env python3
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def fnv1a64(data: bytes) -> str:
    value = 0xCBF29CE484222325
    for byte in data:
        value ^= byte
        value = (value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"{value:016x}"


def bytes_hash(event):
    raw = event.get("bytes_hex")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return fnv1a64(bytes.fromhex(raw))
    except ValueError:
        return None


def create_signature(event):
    name = event.get("event")
    if name == "create_texture":
        w, h, fmt = event.get("width"), event.get("height"), event.get("format")
        if all(isinstance(v, int) for v in (w, h, fmt)):
            return f"tex:{w}x{h}:{fmt}"
    elif name == "create_cube_texture":
        edge, fmt = event.get("edge_length"), event.get("format")
        if isinstance(edge, int) and isinstance(fmt, int):
            return f"cube:{edge}:{fmt}"
    elif name == "create_vertex_buffer":
        length = event.get("length")
        if isinstance(length, int):
            return f"vb:{length}"
    elif name == "create_index_buffer":
        length, fmt = event.get("length"), event.get("format")
        if isinstance(length, int) and isinstance(fmt, int):
            return f"ib:{length}:{fmt}"
    elif name == "create_vertex_shader":
        digest = bytes_hash(event)
        if digest:
            return f"vs:{digest}"
    elif name == "create_pixel_shader":
        digest = bytes_hash(event)
        if digest:
            return f"ps:{digest}"
    elif name == "create_vertex_declaration":
        digest = bytes_hash(event)
        if digest:
            return f"decl:{digest}"
    return None


CREATE_PTR = {
    "create_texture": ("texture", "texture_ptr"),
    "create_cube_texture": ("texture", "texture_ptr"),
    "create_vertex_buffer": ("vb", "vertex_buffer_ptr"),
    "create_index_buffer": ("ib", "index_buffer_ptr"),
    "create_vertex_shader": ("vs", "shader_ptr"),
    "create_pixel_shader": ("ps", "shader_ptr"),
    "create_vertex_declaration": ("decl", "declaration_ptr"),
}

BIND_PTR = {
    "set_texture": ("texture", "texture_ptr"),
    "set_stream_source": ("vb", "vertex_buffer_ptr"),
    "set_indices": ("ib", "index_buffer_ptr"),
    "set_vertex_shader": ("vs", "shader_ptr"),
    "set_pixel_shader": ("ps", "shader_ptr"),
    "set_vertex_declaration": ("decl", "declaration_ptr"),
}


def analyze(path):
    current = {
        "texture": {},
        "vb": {},
        "ib": {},
        "vs": {},
        "ps": {},
        "decl": {},
    }
    created = Counter()
    bound = Counter()
    first_frame = {}
    last_frame = {}
    parse_errors = 0
    lines = 0

    with open(path, "r", encoding="utf-8", errors="replace") as src:
        for line in src:
            lines += 1
            try:
                event = json.loads(line)
            except Exception:
                parse_errors += 1
                continue

            name = event.get("event")

            if name == "resource_signature_use":
                sig = event.get("resource_signature")
                use_count = event.get("use_count")
                if isinstance(sig, str) and sig and isinstance(use_count, int):
                    bound[sig] = max(bound[sig], use_count)
                    first = event.get("first_frame")
                    last = event.get("last_frame", event.get("frame"))
                    if sig not in first_frame and isinstance(first, int):
                        first_frame[sig] = first
                    if isinstance(last, int):
                        last_frame[sig] = max(last_frame.get(sig, last), last)
                continue

            create_desc = CREATE_PTR.get(name)
            if create_desc:
                kind, field = create_desc
                ptr = event.get(field)
                sig = event.get("resource_signature") or create_signature(event)
                if ptr and sig:
                    current[kind][ptr] = sig
                    created[sig] += 1
                    frame = event.get("frame")
                    first_frame.setdefault(sig, frame)
                    last_frame[sig] = frame
                continue

            bind_desc = BIND_PTR.get(name)
            if bind_desc:
                kind, field = bind_desc
                ptr = event.get(field)
                sig = event.get("resource_signature")
                if not sig and ptr:
                    sig = current[kind].get(ptr)
                if sig:
                    bound[sig] += 1
                    frame = event.get("frame")
                    first_frame.setdefault(sig, frame)
                    last_frame[sig] = frame

    return {
        "lines": lines,
        "parse_errors": parse_errors,
        "created": created,
        "bound": bound,
        "first_frame": first_frame,
        "last_frame": last_frame,
    }


def kind_of(signature):
    return signature.split(":", 1)[0] if ":" in signature else "unknown"


def main():
    parser = argparse.ArgumentParser(
        description="List stable D3D9 resource signatures and bind frequency from a SHIFT capture."
    )
    parser.add_argument("capture")
    parser.add_argument("--top", type=int, default=50)
    parser.add_argument(
        "--kind",
        choices=("tex", "cube", "rt", "depth", "vb", "ib", "vs", "ps", "decl"),
        help="show only one signature kind",
    )
    parser.add_argument("--json", dest="json_output")
    args = parser.parse_args()

    report = analyze(args.capture)
    signatures = set(report["created"]) | set(report["bound"])
    if args.kind:
        signatures = {s for s in signatures if kind_of(s) == args.kind}

    ranked = sorted(
        signatures,
        key=lambda s: (
            report["bound"][s],
            report["created"][s],
            s,
        ),
        reverse=True,
    )

    print(f"events: {report['lines']:,}")
    print(f"parse errors: {report['parse_errors']:,}")
    print()
    print("binds     creates   first    last     resource trigger")
    print("-" * 88)
    for sig in ranked[: args.top]:
        first = report["first_frame"].get(sig)
        last = report["last_frame"].get(sig)
        print(
            f"{report['bound'][sig]:9,d} "
            f"{report['created'][sig]:9,d} "
            f"{str(first):8s} "
            f"{str(last):8s} "
            f"{sig}"
        )

    if args.json_output:
        payload = {
            "capture": str(Path(args.capture)),
            "events": report["lines"],
            "parse_errors": report["parse_errors"],
            "resources": [
                {
                    "signature": sig,
                    "kind": kind_of(sig),
                    "binds": report["bound"][sig],
                    "creates": report["created"][sig],
                    "first_frame": report["first_frame"].get(sig),
                    "last_frame": report["last_frame"].get(sig),
                }
                for sig in ranked
            ],
        }
        Path(args.json_output).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
