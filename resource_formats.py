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
        })
        off = end
        if tag == "END ":
            break

    return {
        "format": "SHIFT.SGB",
        "version": 1,
        "header_hex": data[:16].hex(),
        "chunk_count": len(chunks),
        "chunks": chunks,
        "container_end": off,
        "trailing_bytes": max(0, len(data) - off),
    }


def analyze_decoded_resource(path: str, data: bytes) -> dict[str, Any]:
    """Format-aware analysis used by the universal importer."""
    ext = Path(path.lower()).suffix
    base: dict[str, Any] = {"path": path, "extension": ext, "size": len(data)}
    head = data[:64]
    try:
        if data.startswith(b"BLMY"):
            base["analysis"] = parse_bmt_material(data) if ext == ".bmt" else parse_bml(data)
        elif ext == ".lod" and data.lstrip().startswith(b"<?xml"):
            txt = data.decode("utf-8", "replace")
            entries = []
            for line in txt.splitlines():
                m = re.search(r'<ENTRY\s+substring="([^"]+)"([^>]*)/>', line)
                if not m:
                    continue
                attrs = dict(re.findall(r'([A-Za-z0-9_]+)="?([^\s\"]+)"?', m.group(2)))
                entries.append({"substring": m.group(1), "attrs": attrs})
            base["analysis"] = {"format": "SHIFT.LOD_XML", "root": "LODCONTROL", "entry_count": len(entries), "entries": entries, "parser": "loose"}
        elif ext == ".sgb" and data.startswith(b" \x42\x47\x53"):
            base["analysis"] = parse_sgb(data)
        elif ext == ".vhf" and data.lstrip().startswith(b"<?xml"):
            base["analysis"] = parse_vhf_scene(data)
        elif data.lstrip().startswith(b"<?xml") or data.lstrip().startswith(b"<Reflection"):
            txt = data.decode("utf-8", "replace")
            if b"<Reflection" in data:
                base["analysis"] = parse_reflection_xml(data)
            else:
                root = ET.fromstring(txt)
                base["analysis"] = {
                    "format": "XML",
                    "root": root.tag,
                    "tree": _xml_tree(root),
                }
        elif data.startswith(b"DDS "):
            base["analysis"] = parse_dds_metadata(data)
        elif ext == ".meb":
            base["analysis"] = mesh_summary(read_meb(data))
        elif ext == ".csm":
            base["analysis"] = csm_summary(read_csm(data))
        elif data.startswith(b"FEV1"):
            base["analysis"] = {"format": "FMOD.FEV", "magic": "FEV1"}
        elif data.startswith(b"FSB4"):
            base["analysis"] = {"format": "FMOD.FSB", "magic": "FSB4"}
        elif data.startswith(b"NXS\x00MESH") or b"MESH" in data[:32]:
            base["analysis"] = {"format": "SHIFT.MESH.binary", "signature": data[:16].hex()}
        elif data.startswith(b" \x42\x47\x53"):
            base["analysis"] = {"format": "SHIFT.SGB", "signature": data[:16].hex()}
        elif ext in {".fx", ".fxh"}:
            base["analysis"] = parse_hlsl_metadata(data)
        else:
            base["analysis"] = {"format": "binary/unknown", "head_hex": head.hex()}
    except Exception as exc:
        base["analysis_error"] = f"{type(exc).__name__}: {exc}"
        base["analysis"] = {"format": "unparsed", "head_hex": head.hex()}
    return base

# BMT element/attribute IDs observed consistently in the SHIFT material format.
# They are Resource IDs rather than direct STRS offsets. Keeping this small map
# explicit is safer than pretending we know the original global hash function.
BMT_ELEMENT_NAMES = {
    3596240483: "material",
    648867590: "shaderparam",
    1688245861: "type",
    1773598955: "value",
    3396092427: "render_state_group",
    14911235: "alpha_state_group",
}
BMT_ATTR_NAMES = {
    102443717: "name",
    1688245861: "type",
    116: "t",
    118: "v",
}


def _parse_bmt_blocks(data: bytes) -> tuple[dict[str, dict[str, int]], dict[str, Any]]:
    if len(data) < 0x10 or data[:4] != b"BLMY":
        raise ValueError("not a BLMY resource")
    blocks: dict[str, dict[str, int]] = {}
    off = 0x10
    for _ in range(7):
        if off + 16 > len(data):
            raise ValueError("truncated BMT block directory")
        tag = data[off:off + 4].decode("ascii", "replace")
        size, payload_off, reserved = struct.unpack_from("<III", data, off + 4)
        if payload_off + size > len(data):
            raise ValueError(f"BMT block {tag} exceeds resource size")
        blocks[tag] = {"offset": payload_off, "size": size, "reserved": reserved}
        off += 16
    head_off = blocks["HEAD"]["offset"]
    head = [_u32le(data, head_off + i * 4) for i in range(7)]
    return blocks, {
        "version": _u32le(data, 4),
        "declared_size": _u32le(data, 8),
        "head_u32": head,
    }


def _bmt_strings(blob: bytes) -> tuple[dict[int, str], list[dict[str, Any]]]:
    by_off: dict[int, str] = {}
    rows: list[dict[str, Any]] = []
    p = 0
    while p < len(blob):
        end = blob.find(b"\x00", p)
        if end < 0:
            end = len(blob)
        text = blob[p:end].decode("utf-8", "replace")
        by_off[p] = text
        rows.append({"offset": p, "text": text})
        p = end + 1
    return by_off, rows


def parse_bmt(data: bytes) -> dict[str, Any]:
    """Decode the BMLY container used by SHIFT .bmt materials.

    The result contains the exact block layout, typed attribute values, and a
    generic element tree. Known material node/attribute resource IDs are named;
    unknown IDs remain explicit as hash_XXXXXXXX so no data is discarded.
    """
    blocks, meta = _parse_bmt_blocks(data)
    eo, es = blocks["ELMT"]["offset"], blocks["ELMT"]["size"]
    ao, ass = blocks["ATTR"]["offset"], blocks["ATTR"]["size"]
    no, ns = blocks["NUMB"]["offset"], blocks["NUMB"]["size"]
    bo, bs = blocks["BOOL"]["offset"], blocks["BOOL"]["size"]
    so, ss = blocks["STRS"]["offset"], blocks["STRS"]["size"]
    if es % 28:
        raise ValueError("BMT ELMT block is not a whole number of 28-byte records")
    if ass % 20:
        raise ValueError("BMT ATTR block is not a whole number of 20-byte records")
    elem_count = es // 28
    attr_count = ass // 20
    elems = [struct.unpack_from("<7I", data, eo + i * 28) for i in range(elem_count)]
    attrs = [struct.unpack_from("<5I", data, ao + i * 20) for i in range(attr_count)]
    string_map, strings = _bmt_strings(data[so:so + ss])
    numb = [struct.unpack_from("<f", data, no + i * 4)[0] for i in range(ns // 4)]
    bool_blob = data[bo:bo + bs]

    def resolve_elem(v: int) -> str:
        return BMT_ELEMENT_NAMES.get(v, f"hash_{v:08X}")

    def resolve_attr(v: int) -> str:
        return BMT_ATTR_NAMES.get(v, f"hash_{v:08X}")

    def attr_value(attr: tuple[int, int, int, int, int]) -> Any:
        _name, kind, start, count, _next = attr
        if count == 0:
            return []
        if kind == 2:
            vals = [string_map.get(start, "")]
            if count > 1:
                # STRS values are offset references in practice. Preserve the
                # primary value and expose only direct sequential offsets when
                # they resolve cleanly.
                vals = [string_map.get(start + j, "") for j in range(count)]
            return vals[0] if count == 1 else vals
        if kind == 1:
            vals = []
            for j in range(count):
                bit = start + j
                vals.append(bool(bool_blob[bit >> 3] & (1 << (bit & 7))))
            return vals[0] if count == 1 else vals
        if kind == 0:
            vals = numb[start:start + count]
            return vals[0] if count == 1 else vals
        return {"raw_type": kind, "value": start, "count": count}

    def parse_attrs(element_index: int) -> list[dict[str, Any]]:
        e = elems[element_index]
        first, count = e[1], e[2]
        out = []
        for idx in range(first, min(first + count, attr_count)):
            a = attrs[idx]
            out.append({
                "index": idx,
                "name_id": a[0],
                "name": resolve_attr(a[0]),
                "type": a[1],
                "value_index": a[2],
                "count": a[3],
                "next": a[4],
                "value": attr_value(a),
            })
        return out

    def children_of(index: int) -> list[int]:
        first_child = elems[index][4]
        expected = elems[index][3]
        out: list[int] = []
        cur = first_child
        seen: set[int] = set()
        while cur != 0xFFFFFFFF and cur < elem_count and cur not in seen and len(out) <= expected + 32:
            seen.add(cur)
            out.append(cur)
            cur = elems[cur][5]
        return out

    def node(index: int, depth: int = 0) -> dict[str, Any]:
        e = elems[index]
        return {
            "index": index,
            "name_id": e[0],
            "name": resolve_elem(e[0]),
            "attributes": parse_attrs(index),
            "declared_child_count": e[3],
            "children": [node(i, depth + 1) for i in children_of(index)],
        }

    root_index = meta["head_u32"][6]
    tree = node(root_index) if root_index < elem_count else None
    return {
        "format": "SHIFT.BMT",
        "version": meta["version"],
        "declared_size": meta["declared_size"],
        "actual_size": len(data),
        "blocks": blocks,
        "head": {
            "elements": meta["head_u32"][0],
            "attributes": meta["head_u32"][1],
            "coll": meta["head_u32"][2],
            "numbers": meta["head_u32"][3],
            "strings": meta["head_u32"][4],
            "booleans": meta["head_u32"][5],
            "root": root_index,
        },
        "string_count_actual": len(strings),
        "strings": strings,
        "root": tree,
    }

_HLSL_INCLUDE_RE = re.compile(r'#\s*include\s*[<"]([^>"]+)[>"]', re.I)
_HLSL_TECHNIQUE_RE = re.compile(r'\btechnique(?:\d+)?\s+([A-Za-z_][A-Za-z0-9_]*)', re.I)
_HLSL_SAMPLER_RE = re.compile(r'\bsampler(?:2D|3D|CUBE|STATE|2DARRAY|CUBEARRAY)?\s+([A-Za-z_][A-Za-z0-9_]*)', re.I)
_HLSL_TEX_RE = re.compile(r'\b(?:Texture(?:2D|3D|Cube|2DArray)|texture2D|Texture)\s+([A-Za-z_][A-Za-z0-9_]*)', re.I)
_HLSL_VAR_RE = re.compile(r'^\s*(?:uniform\s+)?(float|float2|float3|float4|float4x4|int|bool|half|half2|half3|half4)\s+([A-Za-z_][A-Za-z0-9_]*)', re.M | re.I)


def _material_summary_from_tree(tree: dict[str, Any]) -> dict[str, Any]:
    attrs = tree.get("attributes", [])
    # The stock material schema has seven root attributes in a stable order:
    # name, shader, technique, fog, antialias, numparams, cull.
    semantic = ["name", "shader", "technique", "fog", "antialias", "numparams", "cull"]
    root_values = {semantic[i]: attrs[i].get("value") for i in range(min(len(attrs), len(semantic)))}
    params = []
    for child in tree.get("children", []):
        if child.get("name") != "shaderparam":
            continue
        p = {a["name"]: a.get("value") for a in child.get("attributes", [])}
        for sub in child.get("children", []):
            sub_name = sub.get("name")
            vals = {a["name"]: a.get("value") for a in sub.get("attributes", [])}
            if sub_name == "type":
                root_t = vals.get("t")
                if root_t is not None:
                    p["resource_type"] = root_t
            elif sub_name == "value":
                root_v = vals.get("v")
                if root_v is not None:
                    p["value"] = root_v
        params.append(p)
    textures = []
    for p in params:
        v = p.get("value")
        candidates = v if isinstance(v, list) else [v]
        for x in candidates:
            if isinstance(x, str) and x.lower().endswith(".dds"):
                textures.append(x.replace("\\", "/"))

    # BMT stores shader compile-time specialisation references as hashed
    # child elements carrying a plain name attribute, e.g. USE_FRESNEL,
    # METALLIC, DIRT_SCRATCH. Preserve them explicitly.
    specializations = []
    for child in tree.get("children", []):
        if not str(child.get("name", "")).startswith("hash_"):
            continue
        for attr in child.get("attributes", []):
            if attr.get("name") != "name" or not isinstance(attr.get("value"), str):
                continue
            value = attr["value"]
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
                specializations.append(value)
    specializations = list(dict.fromkeys(specializations))
    return {**root_values, "shaderparams": params, "textures": textures,
            "specializations": specializations}


def parse_bmt_material(data: bytes) -> dict[str, Any]:
    parsed = parse_bmt(data)
    summary = _material_summary_from_tree(parsed["root"]) if parsed.get("root") else {}
    parsed["material"] = summary
    return parsed


def parse_hlsl_metadata(data: bytes) -> dict[str, Any]:
    text = data.decode("utf-8", "replace")
    # Remove comments for structural regexes; shader source is full of prose
    # examples that otherwise look like declarations.
    clean = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    clean = re.sub(r"//[^\n]*", " ", clean)
    includes = list(dict.fromkeys(_HLSL_INCLUDE_RE.findall(clean)))
    techniques = list(dict.fromkeys(_HLSL_TECHNIQUE_RE.findall(clean)))
    samplers = list(dict.fromkeys(_HLSL_SAMPLER_RE.findall(clean)))
    textures = list(dict.fromkeys(_HLSL_TEX_RE.findall(clean)))
    variables = []
    for kind, name in _HLSL_VAR_RE.findall(clean):
        variables.append({"type": kind, "name": name})
    return {
        "format": "HLSL",
        "bytes": len(data),
        "includes": includes,
        "techniques": techniques,
        "samplers": samplers,
        "textures": textures,
        "global_variables": variables[:2048],
        "requires_transpilation": True,
    }
