#!/usr/bin/env python3
"""Parsers for decoded SHIFT resource formats.

This module intentionally converts proprietary resources into a stable,
platform-neutral intermediate representation rather than pretending we have
fully reconstructed every runtime format.
"""
from __future__ import annotations

import json
import math
import re
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


from meb_format import read_meb, mesh_summary
from csm_format import read_csm, csm_summary
from bas_format import parse_bas

_NUMBER_RE = re.compile(r"[;,\\s]+")


def _split_values(text: str) -> list[str]:
    return [x for x in _NUMBER_RE.split(text.strip()) if x]


def _num(text: str, kind: str) -> Any:
    t = text.strip()
    k = kind.lower()
    if k in {"bool", "boolean"}:
        return t.lower() in {"1", "true", "yes", "on"}
    if k in {"string", "str", "name", "filename"}:
        return t
    if k in {"s8", "s16", "s32", "s64", "int", "integer"}:
        return int(float(t)) if any(c in t.lower() for c in ".e") else int(t, 10)
    if k in {"u8", "u16", "u32", "u64", "uint", "unsigned"}:
        return int(float(t)) if any(c in t.lower() for c in ".e") else int(t, 10)
    if k in {"f32", "float", "single", "f64", "double", "f80"}:
        return float(t)
    if k in {"vec2", "vec2f", "vec3", "vec3f", "vec4", "vec4f",
             "quat", "quatf", "quatd", "color", "mat3", "mat3f", "mat4", "mat4f"}:
        vals = []
        for x in _split_values(t):
            try:
                vals.append(float(x))
            except ValueError:
                vals.append(x)
        return vals
    # Fct/Ptr/Ref and unknown scalar types are preserved exactly. The runtime
    # meaning of these references needs class-specific reverse engineering.
    return t


def _scalar_or_raw(text: str, type_name: str | None) -> Any:
    if type_name:
        try:
            return _num(text, type_name)
        except (ValueError, OverflowError):
            pass
    return text


@dataclass
class ReflectionClass:
    name: str
    base: str | None
    props: dict[str, str]


def parse_reflection_xml(data: bytes | str) -> dict[str, Any]:
    """Parse SHIFT's <Reflection> XML into typed, nested JSON-compatible data."""
    root = ET.fromstring(data)
    if root.tag.lower() != "reflection":
        raise ValueError(f"expected Reflection root, got {root.tag!r}")

    classes: dict[str, ReflectionClass] = {}
    for c in root.findall("class"):
        name = c.get("name", "")
        if not name:
            continue
        # Some resources repeat base class declarations. Merge all definitions.
        rec = classes.get(name)
        if rec is None:
            rec = ReflectionClass(name=name, base=c.get("base"), props={})
            classes[name] = rec
        elif c.get("base") and not rec.base:
            rec.base = c.get("base")
        for p in c.findall("prop"):
            pn = p.get("name")
            pt = p.get("type")
            if pn:
                rec.props[pn] = pt or "Unknown"

    def schema_for(class_name: str | None) -> dict[str, str]:
        out: dict[str, str] = {}
        seen: set[str] = set()
        cur = class_name
        while cur and cur not in seen:
            seen.add(cur)
            c = classes.get(cur)
            if not c:
                break
            # child class overrides inherited property declarations.
            out = {**c.props, **out}
            cur = c.base
        return out

    def parse_data(node: ET.Element) -> dict[str, Any]:
        cname = node.get("class", "Unknown")
        schema = schema_for(cname)
        out: dict[str, Any] = {
            "class": cname,
            "id": node.get("id"),
            "properties": {},
        }
        for prop in node.findall("prop"):
            pname = prop.get("name", "")
            typ = schema.get(pname)
            children = prop.findall("./funcpropdata/data")
            if children:
                value: Any = [parse_data(child) for child in children]
            elif "data" in prop.attrib:
                value = _scalar_or_raw(prop.get("data", ""), typ)
            elif prop.get("elements") is not None:
                # Empty function/array field. Keep explicit cardinality.
                value = []
            else:
                value = None
            if "elements" in prop.attrib:
                try:
                    declared = int(prop.get("elements", "0"))
                except ValueError:
                    declared = None
                out["properties"][pname] = {
                    "type": typ,
                    "elements": declared,
                    "value": value,
                }
            else:
                out["properties"][pname] = {
                    "type": typ,
                    "value": value,
                }
        return out

    objects = [parse_data(d) for d in root.findall("data")]
    return {
        "format": "SHIFT.ReflectionXML",
        "version": 1,
        "classes": [
            {"name": c.name, "base": c.base, "properties": c.props}
            for c in classes.values()
        ],
        "objects": objects,
    }



def parse_vhf_scene(data: bytes | str) -> dict[str, Any]:
    """Parse SHIFT/Blimey VHF/CAR XML into an Android-neutral scene graph."""
    root = ET.fromstring(data)
    if root.tag.upper() != "CAR":
        raise ValueError(f"expected CAR root, got {root.tag!r}")

    matrices: dict[str, dict[str, Any]] = {}
    mesh_resources: list[str] = []
    node_count = 0
    damage_count = 0
    sphere_count = 0

    def norm_ref(v: str) -> str:
        return v.replace("\\", "/")

    def parse_node(node: ET.Element) -> dict[str, Any]:
        nonlocal node_count, damage_count, sphere_count
        node_count += 1
        ntype = node.get("type", "")
        if ntype.upper() == "DAMAGE":
            damage_count += 1
        out: dict[str, Any] = {
            "type": ntype,
            "name": node.get("Name", ""),
            "matrix": node.get("MatrixNumber"),
        }
        for key in ("instances", "subobjects", "userflags", "matrices"):
            if key in node.attrib:
                try:
                    out[key] = int(node.attrib[key], 0)
                except ValueError:
                    out[key] = node.attrib[key]
        resources = []
        children = []
        spheres = []
        for child in list(node):
            tag = child.tag.upper()
            if tag == "RESOURCE":
                f = norm_ref(child.get("Filename", ""))
                if f:
                    resources.append(f)
                    mesh_resources.append(f)
            elif tag == "SPHERE":
                sphere_count += 1
                rec = {"centre": child.get("Centre", ""), "radius": child.get("Radius")}
                spheres.append(rec)
            elif tag == "NODE":
                children.append(parse_node(child))
            elif tag == "MATRIX":
                mid = child.get("id")
                if mid is not None:
                    rec = {
                        "offset": child.get("Offset", ""),
                        "orientation": child.get("Orientation", ""),
                    }
                    if "parent" in child.attrib:
                        rec["parent"] = child.get("parent")
                    matrices[mid] = rec
        if resources:
            out["resources"] = resources
        if spheres:
            out["spheres"] = spheres
        if children:
            out["children"] = children
        return out

    # Root contains a mixture of MATRIX and NODE records. Parse matrices first
    # so consumers can resolve transforms independent of document order.
    for elem in list(root):
        if elem.tag.upper() == "NODE":
            # parse_node also discovers nested matrices.
            pass
        elif elem.tag.upper() == "MATRIX":
            mid = elem.get("id")
            if mid is not None:
                rec = {"offset": elem.get("Offset", ""), "orientation": elem.get("Orientation", "")}
                if "parent" in elem.attrib:
                    rec["parent"] = elem.get("parent")
                matrices[mid] = rec

    scene_nodes = [parse_node(e) for e in root.findall("NODE")]
    return {
        "format": "SHIFT.VHFScene",
        "version": 1,
        "name": root.get("Name", ""),
        "exporter_version": root.get("ExporterVersion", ""),
        "matrices": matrices,
        "nodes": scene_nodes,
        "stats": {
            "nodes": node_count,
            "damage_nodes": damage_count,
            "spheres": sphere_count,
            "resource_refs": len(mesh_resources),
        },
    }

BML_TAGS = (b"HEAD", b"ELMT", b"ATTR", b"COLL", b"NUMB", b"BOOL", b"STRS")


def _u32le(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise ValueError("BML u32 out of range")
    return struct.unpack_from("<I", data, off)[0]


def parse_bml(data: bytes, *, include_raw: bool = False) -> dict[str, Any]:
    """Index the BLMY/BML chunk container used by SHIFT scripts/campaign data."""
    if len(data) < 0x10 or data[:4] != b"BLMY":
        raise ValueError("not a BLMY BML resource")
    version = _u32le(data, 4)
    declared_size = _u32le(data, 8)
    # The block directory is seven 16-byte descriptors in the known BML format.
    blocks: dict[str, dict[str, int]] = {}
    off = 0x10
    for _ in range(7):
        if off + 16 > len(data):
            raise ValueError("truncated BML block directory")
        tag = data[off:off + 4]
        size = _u32le(data, off + 4)
        payload_off = _u32le(data, off + 8)
        reserved = _u32le(data, off + 12)
        name = tag.decode("ascii", "replace")
        if tag not in BML_TAGS:
            raise ValueError(f"unexpected BML block tag {tag!r}")
        if payload_off + size > len(data):
            raise ValueError(f"BML block {name} exceeds resource size")
        blocks[name] = {
            "offset": payload_off,
            "size": size,
            "reserved": reserved,
        }
        off += 16

    head = data[blocks["HEAD"]["offset"]:blocks["HEAD"]["offset"] + blocks["HEAD"]["size"]]
    head_values = [struct.unpack_from("<I", head, i)[0] for i in range(0, len(head) - len(head) % 4, 4)]

    numb_blob = data[blocks["NUMB"]["offset"]:blocks["NUMB"]["offset"] + blocks["NUMB"]["size"]]
    floats = []
    for i in range(0, len(numb_blob) - len(numb_blob) % 4, 4):
        v = struct.unpack_from("<f", numb_blob, i)[0]
        floats.append(None if not math.isfinite(v) else v)

    bool_blob = data[blocks["BOOL"]["offset"]:blocks["BOOL"]["offset"] + blocks["BOOL"]["size"]]
    str_blob = data[blocks["STRS"]["offset"]:blocks["STRS"]["offset"] + blocks["STRS"]["size"]]
    strings = []
    start = 0
    while start < len(str_blob):
        end = str_blob.find(b"\x00", start)
        if end < 0:
            end = len(str_blob)
        raw = str_blob[start:end]
        strings.append({
            "offset": start,
            "text": raw.decode("utf-8", "replace"),
        })
        start = end + 1

    result: dict[str, Any] = {
        "format": "SHIFT.BMLY",
        "version": version,
        "declared_size": declared_size,
        "actual_size": len(data),
        "blocks": blocks,
        "head_u32": head_values,
        "number_float_count": len(floats),
        "number_floats": floats[:4096],
        "bool_bytes": len(bool_blob),
        "strings": strings[:16384],
    }
    if include_raw:
        result["raw_hex"] = {
            tag: data[b["offset"]:b["offset"] + b["size"]].hex()
            for tag, b in blocks.items()
            if tag in {"ELMT", "ATTR", "COLL"}
        }
    return result


def parse_dds_metadata(data: bytes) -> dict[str, Any]:
    if len(data) < 128 or data[:4] != b"DDS ":
        raise ValueError("not a DDS file")
    h = struct.unpack_from("<31I", data, 4)
    height, width = h[2], h[3]
    pitch_or_linear = h[4]
    mipmaps = h[6]
    pf_flags, pf_fourcc, pf_rgb_bits = h[19], h[20], h[21]
    fourcc = struct.pack("<I", pf_fourcc)
    return {
        "format": "DDS",
        "width": width,
        "height": height,
        "mipmaps": mipmaps or 1,
        "pitch_or_linear_size": pitch_or_linear,
        "pixel_format_flags": pf_flags,
        "fourcc": fourcc.decode("ascii", "replace").rstrip("\x00"),
        "rgb_bits": pf_rgb_bits,
        "byte_size": len(data),
    }


def _xml_tree(node: ET.Element, depth: int = 0, max_depth: int = 12) -> dict[str, Any]:
    out: dict[str, Any] = {"tag": node.tag, "attributes": dict(node.attrib)}
    text = (node.text or "").strip()
    if text:
        out["text"] = text[:4096]
    if depth < max_depth:
        children = list(node)
        if children:
            out["children"] = [_xml_tree(c, depth + 1, max_depth) for c in children]
    else:
        out["children_truncated"] = len(list(node))
    return out


def parse_sgb(data: bytes) -> dict[str, Any]:
    """Index the SHIFT binary scene graph container used by track .sgb files.

    The format starts with a 16-byte header followed by reversed FourCC chunks.
    Each chunk is `tag[4] + size:u32le`, where size includes the 8-byte header.
    This intentionally records chunk boundaries without inventing semantics for
    NODE/FLAT/SUMM payloads that still need deeper RE work.
    """
    if len(data) < 16 or not data.startswith(b" \x42\x47\x53"):
        raise ValueError("not a SHIFT SGB resource")

    chunks: list[dict[str, Any]] = []
    off = 16
    while off + 8 <= len(data):
        raw_tag = data[off:off + 4]
        size = struct.unpack_from("<I", data, off + 4)[0]
        if size < 8:
            raise ValueError(f"SGB invalid chunk size {size} at 0x{off:X}")
        end = off + size
        if end > len(data):
            # The file may carry a non-container tail after END; preserve it.
            break
        tag = raw_tag[::-1].decode("ascii", "replace")
        payload = data[off + 8:end]
        chunks.append({
            "tag": tag,
            "offset": off,
            "size": size,
            "payload_size": len(payload),
            "payload_sha256": __import__("hashlib").sha256(payload).hexdigest(),
            "payload_head": payload[:24].hex(),
            "resource_refs": _sgb_strings(payload, off + 8),
        })
        off = end
        if tag == "END ":
            break

    refs = [ref for chunk in chunks for ref in chunk.get("resource_refs", [])]
    unique_refs = []
    seen_paths = set()
    for ref in refs:
        key = ref["path"].lower()
        if key not in seen_paths:
            seen_paths.add(key)
            unique_refs.append(ref)
    by_kind = {}
    for ref in unique_refs:
        by_kind.setdefault(ref["kind"], 0)
        by_kind[ref["kind"]] += 1
    return {
        "format": "SHIFT.SGB",
        "version": 1,
        "header_hex": data[:16].hex(),
        "chunk_count": len(chunks),
        "chunks": chunks,
        "resource_refs": unique_refs,
        "resource_ref_counts": by_kind,
        "container_end": off,
        "trailing_bytes": max(0, len(data) - off),
    }



_SGB_ALLOWED = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./\\-")
_SGB_EXTENSIONS = tuple(
    x.encode("ascii")
    for x in ("meb", "bmt", "mtx", "dds", "csm", "vhf", "fxo", "fx", "sgb", "bml", "bas")
)

_SGB_KIND = {
    ".meb": "geometry",
    ".bmt": "material",
    ".mtx": "material-source",
    ".dds": "texture",
    ".csm": "collision",
    ".vhf": "scene-source",
    ".fxo": "shader-cache",
    ".fx": "shader-source",
    ".sgb": "scene-source",
    ".bml": "data",
    ".bas": "skeleton-source",
}


def _sgb_strings(data: bytes, base_offset: int = 0) -> list[dict[str, Any]]:
    """Recover path-like strings deterministically from an SGB payload."""
    rows: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()

    def emit(text: str, absolute_offset: int, relative_offset: int, encoding: str) -> None:
        text = text.replace("\\", "/")
        ext = Path(text.lower()).suffix
        key = (absolute_offset, text.lower())
        if key in seen:
            return
        seen.add(key)
        rows.append({
            "offset": absolute_offset,
            "relative_offset": relative_offset,
            "encoding": encoding,
            "path": text,
            "extension": ext,
            "kind": _SGB_KIND.get(ext, "unknown"),
            "confidence": "string-scan",
        })

    # ASCII: scan known extensions and walk backwards over path-safe bytes.
    lower = data.lower()
    for ext in _SGB_EXTENSIONS:
        suffix = b"." + ext
        cursor = 0
        while True:
            pos = lower.find(suffix, cursor)
            if pos < 0:
                break
            start = pos
            while start > 0 and data[start - 1] in _SGB_ALLOWED:
                start -= 1
            raw = data[start:pos + len(suffix)]
            if 2 <= len(raw) <= 256:
                emit(raw.decode("utf-8", "replace"), base_offset + start, start, "ascii")
            cursor = pos + 1

    # UTF-16LE: search each extension in its UTF-16 representation.
    for ext in _SGB_EXTENSIONS:
        suffix = b"." + ext
        encoded = b"".join(bytes((ch, 0)) for ch in suffix)
        cursor = 0
        while True:
            pos = data.find(encoded, cursor)
            if pos < 0:
                break
            start = pos
            while start >= 2 and data[start - 2] in _SGB_ALLOWED and data[start - 1] == 0:
                start -= 2
            raw = data[start:pos + len(encoded)]
            if 4 <= len(raw) <= 512 and len(raw) % 2 == 0:
                text_bytes = bytes(raw[i] for i in range(0, len(raw), 2))
                emit(text_bytes.decode("utf-8", "replace"), base_offset + start, start, "utf-16le")
            cursor = pos + 2

    rows.sort(key=lambda x: (x["offset"], x["path"].lower()))
    return rows

SGB_KIND.get(ext, "unknown"),
                    "confidence": "string-scan",
                })
    return rows
