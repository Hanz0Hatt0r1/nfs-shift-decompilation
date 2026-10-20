"""Build a fail-closed Vulkan replay bundle from one captured D3D9 draw."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path, PureWindowsPath
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src" / "graphics" / "shader"))
sys.path.insert(0, str(ROOT / "src" / "render"))
sys.path.insert(0, str(ROOT / "src" / "formats"))
sys.path.insert(0, str(ROOT / "src" / "animation"))

from shader_asm import parse_program
from shader_backend import translate_pair, validate_linked_shader_pair_vulkan
from shader_interface import D3D9_DECL_USAGE, build_vertex_input_locations
from shader_ir import parse_shader_blobs
from texture_reference import decode_dds
from vulkan_texture_packet import build_vulkan_texture_packet

FORMAT = "SHIFT.D3D9CaptureVulkanBundle/1"
GEOMETRY_HEADER = struct.Struct("<4sIIIIII4f")
GEOMETRY_ATTRIBUTE = struct.Struct("<IIIII")
CAPTURE_GEOMETRY = struct.Struct("<IIiI")
CONSTANT_HEADER = struct.Struct("<4sIIIIII")
MAX_CONSTANTS = 256

_SEMANTIC_PROPERTY = {
    (0, 0): "200",
    (10, 0): "460",
    (10, 1): "461",
    (3, 0): "220",
    (6, 0): "240",
    (7, 0): "250",
    (1, 0): "310",
    (2, 0): "580",
}
_SEMANTIC_PROPERTY.update({(5, index): str(130 + index) for index in range(5)})
_D3D_FORMAT = {1: 1, 2: 2, 3: 3, 4: 4}
_SAMPLER_ADDRESS = {
    1: "REPEAT",
    2: "MIRRORED_REPEAT",
    3: "CLAMP_TO_EDGE",
}
_SAMPLER_FILTER = {1: "NEAREST", 2: "LINEAR"}
_BLEND_FACTOR = {
    1: "VK_BLEND_FACTOR_ZERO",
    2: "VK_BLEND_FACTOR_ONE",
    3: "VK_BLEND_FACTOR_SRC_COLOR",
    4: "VK_BLEND_FACTOR_ONE_MINUS_SRC_COLOR",
    5: "VK_BLEND_FACTOR_SRC_ALPHA",
    6: "VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA",
    7: "VK_BLEND_FACTOR_DST_ALPHA",
    8: "VK_BLEND_FACTOR_ONE_MINUS_DST_ALPHA",
    9: "VK_BLEND_FACTOR_DST_COLOR",
    10: "VK_BLEND_FACTOR_ONE_MINUS_DST_COLOR",
    11: "VK_BLEND_FACTOR_SRC_ALPHA_SATURATE",
}
_COMPARE = {
    1: "VK_COMPARE_OP_NEVER",
    2: "VK_COMPARE_OP_LESS",
    3: "VK_COMPARE_OP_EQUAL",
    4: "VK_COMPARE_OP_LESS_OR_EQUAL",
    5: "VK_COMPARE_OP_GREATER",
    6: "VK_COMPARE_OP_NOT_EQUAL",
    7: "VK_COMPARE_OP_GREATER_OR_EQUAL",
    8: "VK_COMPARE_OP_ALWAYS",
}
_BLEND_OP = {
    1: "VK_BLEND_OP_ADD",
    2: "VK_BLEND_OP_SUBTRACT",
    3: "VK_BLEND_OP_REVERSE_SUBTRACT",
    4: "VK_BLEND_OP_MIN",
    5: "VK_BLEND_OP_MAX",
}
_RENDER_TARGET_FORMAT = {114: "VK_FORMAT_R32_SFLOAT"}
_DEPTH_FORMAT = {75: "VK_FORMAT_D24_UNORM_S8_UINT"}


def _captured_surface_formats(
    color_format: int,
    depth_format: int,
    depth_enabled: bool,
) -> tuple[str, str]:
    if color_format not in _RENDER_TARGET_FORMAT:
        raise ValueError(f"unsupported captured D3D9 render-target format: {color_format}")
    if depth_format and depth_format not in _DEPTH_FORMAT:
        raise ValueError(f"unsupported captured D3D9 depth format: {depth_format}")
    if depth_enabled and depth_format not in _DEPTH_FORMAT:
        raise ValueError(f"unsupported or missing captured D3D9 depth format: {depth_format}")
    return _RENDER_TARGET_FORMAT[color_format], _DEPTH_FORMAT.get(depth_format, "")


def _read_events(capture_path: Path, event_index: int) -> tuple[dict[str, Any], dict[str, Any]]:
    draw = None
    for line in capture_path.open(encoding="utf-8"):
        row = json.loads(line)
        if int(row.get("event_index", -1)) == event_index:
            if row.get("event") != "draw_indexed_primitive":
                raise ValueError(f"event {event_index} is not DrawIndexedPrimitive")
            draw = row
            break
    if draw is None:
        raise ValueError(f"capture event {event_index} was not found")

    state: dict[str, Any] = {
        "render_states": {},
        "sampler_states": {},
        "streams": {},
        "vertex_constants": [[0.0] * 4 for _ in range(MAX_CONSTANTS)],
        "pixel_constants": [[0.0] * 4 for _ in range(MAX_CONSTANTS)],
        "constant_registers": {"vertex": set(), "pixel": set()},
    }
    objects: dict[str, dict[str, Any]] = {
        "vertex_shader": {},
        "pixel_shader": {},
        "declaration": {},
        "vertex_buffer": {},
        "index_buffer": {},
        "texture": {},
        "payload": {},
    }
    device = draw.get("device_ptr")
    process_id = draw.get("process_id")
    for line in capture_path.open(encoding="utf-8"):
        row = json.loads(line)
        current_event = int(row.get("event_index", -1))
        if current_event > event_index:
            break
        event = row.get("event")
        pointer_fields = {
            "create_vertex_shader": ("vertex_shader", "shader_ptr"),
            "create_pixel_shader": ("pixel_shader", "shader_ptr"),
            "create_vertex_declaration": ("declaration", "declaration_ptr"),
            "create_vertex_buffer": ("vertex_buffer", "vertex_buffer_ptr"),
            "create_index_buffer": ("index_buffer", "index_buffer_ptr"),
            "create_texture": ("texture", "texture_ptr"),
        }
        if event in pointer_fields and row.get("process_id") == process_id:
            category, key = pointer_fields[event]
            objects[category][row.get(key)] = row
        if event == "buffer_payload" and row.get("process_id") == process_id:
            objects["payload"][row.get("buffer_ptr")] = row

        if row.get("device_ptr") != device:
            continue
        if event == "set_render_state":
            state["render_states"][int(row["state"])] = int(row["value"])
        elif event == "set_sampler_state":
            sampler = int(row["sampler"])
            state["sampler_states"].setdefault(sampler, {})[
                int(row["state"])
            ] = int(row["value"])
        elif event == "set_stream_source":
            state["streams"][int(row["stream"])] = row
        elif event == "set_indices":
            state["indices"] = row
        elif event == "set_vertex_declaration":
            state["declaration"] = row
        elif event == "set_vertex_shader":
            state["vertex_shader"] = row
        elif event == "set_pixel_shader":
            state["pixel_shader"] = row
        elif event == "set_texture":
            state.setdefault("textures", {})[int(row["stage"])] = row
        elif event == "set_viewport":
            state["viewport"] = row
        elif event == "set_render_target" and int(row.get("render_target_index", 0)) == 0:
            state["render_target"] = row
        elif event == "set_depth_stencil_surface":
            state["depth_stencil_surface"] = row
        elif event == "clear":
            state["clear"] = row
            state["clear_render_target"] = state.get("render_target", {}).get("resource_signature")
        elif event in {"set_vertex_shader_constant_f", "set_pixel_shader_constant_f"}:
            stage = "vertex" if event.startswith("set_vertex") else "pixel"
            values = row.get("values") or []
            start = int(row["start_register"])
            count = int(row["vector4f_count"])
            if len(values) != count * 4 or start < 0 or start + count > MAX_CONSTANTS:
                raise ValueError(f"invalid {stage} float-constant update at event {current_event}")
            bank = state[f"{stage}_constants"]
            for index in range(count):
                register = start + index
                bank[register] = [float(x) for x in values[index * 4:index * 4 + 4]]
                state["constant_registers"][stage].add(register)
    return draw, {**state, "objects": objects}


def _resource_file(root: Path, path_value: str, directory: str) -> Path:
    name = PureWindowsPath(path_value).name
    path = root / directory / name
    if not path.is_file():
        raise ValueError(f"capture payload is missing: {path}")
    return path


def _shader_program(row: dict[str, Any], stage: str) -> Any:
    payload = bytes.fromhex(str(row.get("bytes_hex") or ""))
    if not payload:
        raise ValueError(f"captured {stage} shader has no bytecode")
    blobs = [blob for blob in parse_shader_blobs(payload) if blob.stage == stage]
    if len(blobs) != 1:
        raise ValueError(f"captured {stage} shader does not contain one stage program")
    blob = blobs[0]
    program = parse_program(payload, blob.offset, blob.end, blob.stage, blob.major, blob.minor)
    if program.unsupported_opcodes:
        raise ValueError(f"captured {stage} shader has unsupported opcodes")
    return program


def _declaration(data: bytes) -> list[dict[str, int | str]]:
    elements = []
    for offset in range(0, len(data) - 7, 8):
        stream, element_offset, kind, method, usage, usage_index = struct.unpack_from("<HHBBBB", data, offset)
        if stream == 0xFF:
            break
        if method != 0:
            raise ValueError("captured vertex declaration uses an unsupported method")
        property_id = _SEMANTIC_PROPERTY.get((usage, usage_index))
        elements.append({
            "stream": stream,
            "offset": element_offset,
            "type": kind,
            "method": method,
            "usage": usage,
            "usage_index": usage_index,
            "property_id": property_id or f"unknown-{usage}-{usage_index}-{len(elements)}",
        })
    else:
        raise ValueError("captured vertex declaration has no D3DDECL_END")
    if not elements:
        raise ValueError("captured vertex declaration is empty")
    return elements


def _shader_inputs(program: Any, elements: list[dict[str, int | str]], stride: int) -> tuple[list[str], list[dict[str, Any]]]:
    properties = [str(element["property_id"]) for element in elements]
    linkage = build_vertex_input_locations(program, properties)
    if not linkage["valid"]:
        raise ValueError("captured D3D9 vertex declaration does not cover shader inputs")
    element_by_semantic = {
        (int(element["usage"]), int(element["usage_index"])): element
        for element in elements
    }
    if len(element_by_semantic) != len(elements):
        raise ValueError("captured vertex declaration repeats a semantic")
    attributes = []
    for binding in linkage["bindings"]:
        usage_name = str(binding["semantic"]["usage"]).upper()
        usage = next((key for key, value in D3D9_DECL_USAGE.items() if value == usage_name), None)
        if usage is None:
            raise ValueError(f"unsupported vertex shader semantic {usage_name}")
        element = element_by_semantic.get((usage, int(binding["semantic"]["index"])))
        if element is None:
            raise ValueError(f"vertex declaration is missing {usage_name}{binding['semantic']['index']}")
        format_code = _D3D_FORMAT.get(int(element["type"]))
        if format_code is None:
            raise ValueError(f"unsupported captured D3DDECLTYPE {element['type']}")
        property_id = str(element["property_id"])
        expected_types = {
            "200": 2, "460": 4, "461": 4,
            "220": 2, "240": 2, "250": 2,
            "310": 3, "580": 5,
            **{str(130 + index): 1 for index in range(5)},
        }
        if expected_types.get(property_id) != int(element["type"]):
            raise ValueError(
                f"captured semantic {property_id} has an unsupported D3DDECLTYPE"
            )
        element_size = {1: 8, 2: 12, 3: 16, 4: 4}[format_code]
        if int(element["offset"]) + element_size > stride:
            raise ValueError("captured vertex element exceeds stream stride")
        attributes.append({
            "location": int(binding["target_location"]),
            "format": format_code,
            "offset": int(element["offset"]),
            "stride": stride,
            "property_id": 0,
            "d3d_type": int(element["type"]),
        })
    if not attributes or not any(row["location"] == 0 and row["format"] == 2 for row in attributes):
        raise ValueError("captured vertex declaration has no FLOAT3 POSITION0 at location 0")
    return properties, attributes


def encode_capture_geometry(
    vertex_bytes: bytes,
    index_bytes: bytes,
    *,
    stride: int,
    attributes: list[dict[str, Any]],
    index_format_bits: int,
    first_index: int,
    draw_index_count: int,
    base_vertex: int,
    vertex_buffer_offset: int = 0,
) -> bytes:
    """Encode captured VB/IB bytes as SVGP v4 without widening INDEX16."""
    if stride <= 0 or vertex_buffer_offset < 0 or vertex_buffer_offset > len(vertex_bytes):
        raise ValueError("invalid captured vertex stream range")
    if (len(vertex_bytes) - vertex_buffer_offset) % stride:
        raise ValueError("captured vertex stream is not stride aligned")
    element_bytes = {16: 2, 32: 4}.get(index_format_bits)
    if element_bytes is None or len(index_bytes) % element_bytes:
        raise ValueError("invalid captured index buffer width")
    index_count = len(index_bytes) // element_bytes
    if draw_index_count <= 0 or draw_index_count % 3 or first_index < 0 or first_index + draw_index_count > index_count:
        raise ValueError("captured triangle-list draw range exceeds its index buffer")
    if not attributes or len(attributes) > 16:
        raise ValueError("captured draw requires between one and sixteen vertex attributes")
    vertex_count = (len(vertex_bytes) - vertex_buffer_offset) // stride
    values = [
        struct.unpack_from("<H" if index_format_bits == 16 else "<I", index_bytes, index * element_bytes)[0]
        for index in range(first_index, first_index + draw_index_count)
    ]
    if any(index + base_vertex < 0 or index + base_vertex >= vertex_count for index in values):
        raise ValueError("captured draw index escapes the effective vertex range")

    attribute_data = b"".join(
        GEOMETRY_ATTRIBUTE.pack(
            int(row["location"]), int(row["format"]), int(row["offset"]),
            stride, int(row.get("property_id", 0)),
        )
        for row in attributes
    )
    header = GEOMETRY_HEADER.pack(
        b"SVGP", 4, vertex_count, index_count, stride, len(attributes),
        first_index, 0.0, 0.0, 0.0, 1.0,
    )
    metadata = CAPTURE_GEOMETRY.pack(
        index_format_bits, draw_index_count, base_vertex, vertex_buffer_offset,
    )
    return header + attribute_data + metadata + vertex_bytes + index_bytes


def _capture_constants(state: dict[str, Any], output: Path) -> dict[str, Any]:
    header = CONSTANT_HEADER.pack(
        b"SVCP", 1, MAX_CONSTANTS, 16,
        len(state["constant_registers"]["vertex"]),
        len(state["constant_registers"]["pixel"]), 0,
    )
    body = bytearray()
    for stage in ("vertex", "pixel"):
        for values in state[f"{stage}_constants"]:
            body.extend(struct.pack("<4f", *values))
    output.write_bytes(header + body)
    return {
        "path": output.name,
        "vertex_populated": len(state["constant_registers"]["vertex"]),
        "pixel_populated": len(state["constant_registers"]["pixel"]),
        "sha256": hashlib.sha256(header + body).hexdigest(),
    }


def _pipeline_state(states: dict[int, int]) -> dict[str, Any]:
    required = (7, 14, 23, 27, 19, 20, 22, 168, 171, 206)
    missing = [state for state in required if state not in states]
    if missing:
        raise ValueError("captured draw lacks required render states: " + ", ".join(map(str, missing)))
    if states[168] != 0xF:
        raise ValueError("partial D3D9 color-write masks are not supported in this replay")
    if states[206] != 0:
        raise ValueError("separate alpha blend state is not supported in this replay")
    if states[27] not in {0, 1} or states[7] not in {0, 1} or states[14] not in {0, 1}:
        raise ValueError("captured boolean render state is invalid")
    try:
        return {
            "format": "SHIFT.MaterialPipelineState/1",
            "ready": True,
            "depth_test_enable": bool(states[7]),
            "depth_write_enable": bool(states[14]),
            "depth_compare_op": _COMPARE[states[23]],
            "blend_enable": bool(states[27]),
            "src_color_blend_factor": _BLEND_FACTOR[states[19]],
            "dst_color_blend_factor": _BLEND_FACTOR[states[20]],
            "color_blend_op": _BLEND_OP[states[171]],
            "src_alpha_blend_factor": _BLEND_FACTOR[states[19]],
            "dst_alpha_blend_factor": _BLEND_FACTOR[states[20]],
            "alpha_blend_op": _BLEND_OP[states[171]],
            "vulkan_cull_mode": {1: "VK_CULL_MODE_NONE", 2: "VK_CULL_MODE_BACK_BIT", 3: "VK_CULL_MODE_FRONT_BIT"}[states[22]],
            "captured_d3d9_render_states": {str(k): v for k, v in sorted(states.items())},
            "front_face_mapping": "CCW with negative viewport height preserving D3D9 screen orientation",
        }
    except KeyError as exc:
        raise ValueError(f"captured D3D9 render state has unsupported value: {exc.args[0]}") from exc


def _sampler_state(states: dict[int, int]) -> dict[str, str]:
    required = (1, 2, 5, 6)
    missing = [state for state in required if state not in states]
    if missing:
        raise ValueError("captured sampler state is incomplete")
    try:
        u = _SAMPLER_ADDRESS[states[1]]
        v = _SAMPLER_ADDRESS[states[2]]
        min_filter = _SAMPLER_FILTER[states[6]]
        mag_filter = _SAMPLER_FILTER[states[5]]
    except KeyError as exc:
        raise ValueError(f"captured sampler value is unsupported: {exc.args[0]}") from exc
    if u != v:
        raise ValueError("Vulkan replay requires matching captured U/V address modes")
    return {"address_u": u, "address_v": v, "min_filter": min_filter, "mag_filter": mag_filter}


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_vulkan_capture_bundle(capture: str | Path, event_index: int, output_dir: str | Path) -> dict[str, Any]:
    capture_path = Path(capture).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    draw, state = _read_events(capture_path, event_index)
    if int(draw.get("primitive_type", -1)) != 4:
        raise ValueError("only captured D3DPT_TRIANGLELIST is supported")

    stream = state.get("streams", {}).get(0)
    indices_state = state.get("indices")
    declaration_state = state.get("declaration")
    vertex_state = state.get("vertex_shader")
    pixel_state = state.get("pixel_shader")
    texture_state = state.get("textures", {}).get(0)
    viewport = state.get("viewport")
    target = state.get("render_target")
    depth_target = state.get("depth_stencil_surface")
    clear = state.get("clear")
    if not all((stream, indices_state, declaration_state, vertex_state, pixel_state, texture_state, viewport, target, clear)):
        raise ValueError("captured draw is missing a required bound resource or state")
    if state.get("clear_render_target") != target.get("resource_signature"):
        raise ValueError("the captured clear does not belong to the draw render target")
    target_format = int(target.get("surface_format", -1))
    depth_format = int(depth_target.get("surface_format", 0)) if depth_target else 0
    vulkan_color_format, vulkan_depth_format = _captured_surface_formats(
        target_format,
        depth_format,
        bool(int(state["render_states"].get(7, 0))),
    )
    if depth_target and (
        int(depth_target.get("surface_width", -1)) != int(target["surface_width"])
        or int(depth_target.get("surface_height", -1)) != int(target["surface_height"])
    ):
        raise ValueError("captured color and depth targets have different dimensions")

    objects = state["objects"]
    vb_ptr = stream.get("vertex_buffer_ptr")
    ib_ptr = indices_state.get("index_buffer_ptr")
    vertex_create = objects["vertex_buffer"].get(vb_ptr)
    index_create = objects["index_buffer"].get(ib_ptr)
    vertex_payload = objects["payload"].get(vb_ptr)
    index_payload = objects["payload"].get(ib_ptr)
    if not all((vertex_create, index_create, vertex_payload, index_payload)):
        raise ValueError("captured draw lacks a create record or buffer payload snapshot")
    if int(vertex_payload["event_index"]) <= int(vertex_create["event_index"]) or int(vertex_payload["event_index"]) > event_index:
        raise ValueError("vertex payload is outside its COM resource generation")
    if int(index_payload["event_index"]) <= int(index_create["event_index"]) or int(index_payload["event_index"]) > event_index:
        raise ValueError("index payload is outside its COM resource generation")
    if vertex_create.get("pool") != 1 or vertex_create.get("usage") != 0:
        raise ValueError("capture replay currently requires a static managed vertex buffer")
    if index_create.get("format") != 101:
        raise ValueError("capture replay requires D3DFMT_INDEX16")
    if int(stream.get("stride", 0)) <= 0 or int(vertex_create.get("length", -1)) != int(vertex_payload.get("buffer_length", -2)):
        raise ValueError("captured vertex stream metadata does not match its full snapshot")
    if int(index_create.get("length", -1)) != int(index_payload.get("buffer_length", -2)):
        raise ValueError("captured index metadata does not match its full snapshot")
    if int(vertex_payload.get("offset", -1)) != 0 or int(vertex_payload.get("captured_byte_size", -1)) != int(vertex_payload.get("buffer_length", -2)):
        raise ValueError("captured vertex payload is not a complete offset-zero snapshot")
    if int(index_payload.get("offset", -1)) != 0 or int(index_payload.get("captured_byte_size", -1)) != int(index_payload.get("buffer_length", -2)):
        raise ValueError("captured index payload is not a complete offset-zero snapshot")

    vertex_path = _resource_file(capture_path.parent, str(vertex_payload["payload_path"]), "buffers")
    index_path = _resource_file(capture_path.parent, str(index_payload["payload_path"]), "buffers")
    vertex_bytes = bytearray(vertex_path.read_bytes())
    index_bytes = index_path.read_bytes()
    stride = int(stream["stride"])
    stream_offset = int(stream.get("offset_in_bytes", 0))
    declaration = _declaration(bytes.fromhex(str(objects["declaration"].get(declaration_state["declaration_ptr"], {}).get("bytes_hex") or "")))
    if any(int(element["stream"]) != 0 for element in declaration):
        raise ValueError("captured draw uses a vertex declaration outside stream0")
    vertex_shader_row = objects["vertex_shader"].get(vertex_state.get("shader_ptr"))
    pixel_shader_row = objects["pixel_shader"].get(pixel_state.get("shader_ptr"))
    if not vertex_shader_row or not pixel_shader_row:
        raise ValueError("active captured shader object was not found")
    if vertex_state.get("resource_signature") != vertex_shader_row.get("resource_signature") or pixel_state.get("resource_signature") != pixel_shader_row.get("resource_signature"):
        raise ValueError("active shader identity does not match its captured bytecode")
    vertex_program = _shader_program(vertex_shader_row, "vertex")
    pixel_program = _shader_program(pixel_shader_row, "pixel")
    properties, attributes = _shader_inputs(vertex_program, declaration, stride)
    linked = translate_pair(vertex_program, pixel_program, vertex_properties=properties)
    validation = validate_linked_shader_pair_vulkan(linked)
    if validation.get("status") != "valid":
        raise ValueError("captured VS/PS pair failed Vulkan compile/link validation")

    for attribute in attributes:
        if attribute["d3d_type"] == 4:
            for vertex in range((len(vertex_bytes) - stream_offset) // stride):
                offset = stream_offset + vertex * stride + attribute["offset"]
                vertex_bytes[offset], vertex_bytes[offset + 2] = vertex_bytes[offset + 2], vertex_bytes[offset]
        attribute.pop("d3d_type")
    primitive_count = int(draw.get("primitive_count", 0))
    draw_index_count = primitive_count * 3
    geometry = encode_capture_geometry(
        bytes(vertex_bytes), index_bytes, stride=stride, attributes=attributes,
        index_format_bits=16, first_index=int(draw.get("start_index", -1)),
        draw_index_count=draw_index_count,
        base_vertex=int(draw.get("base_vertex_index", 0)),
        vertex_buffer_offset=stream_offset,
    )
    (output / "geometry.svpk").write_bytes(geometry)

    _capture_constants(state, output / "constants.svcp")
    sampler = _sampler_state(state["sampler_states"].get(0, {}))
    snapshot_paths = texture_state.get("snapshot_paths") or []
    if texture_state.get("snapshot_status") != "captured" or not snapshot_paths:
        raise ValueError("active texture has no captured DDS snapshot")
    texture_path = _resource_file(capture_path.parent, str(snapshot_paths[0]), "textures")
    texture = decode_dds(texture_path.read_bytes())
    texture_command = {
        "format": "SHIFT.RenderCommand/1",
        "submeshes": [{"textures": [{
            "d3d9_sampler_register": 0,
            "sampler_state": sampler,
        }]}],
    }
    texture_report = build_vulkan_texture_packet(
        texture_command, {0: texture}, output / "textures.svtp")
    if pixel_program.samplers != [0]:
        raise ValueError("capture replay currently supports one active pixel sampler at s0")

    render_states = state["render_states"]
    pipeline_state = _pipeline_state(render_states)
    _write_json(output / "pipeline_state.json", pipeline_state)
    viewport_state = {
        "format": "SHIFT.D3D9CaptureRenderTarget/1",
        "ready": True,
        "target_width": int(target["surface_width"]),
        "target_height": int(target["surface_height"]),
        "viewport_x": int(viewport["x"]),
        "viewport_y": int(viewport["y"]),
        "viewport_width": int(viewport["width"]),
        "viewport_height": int(viewport["height"]),
        "min_depth": float(viewport["min_z"]),
        "max_depth": float(viewport["max_z"]),
        "d3d9_y_down": True,
        "surface_format": target_format,
        "vulkan_color_format": vulkan_color_format,
        "depth_surface_signature": depth_target.get("resource_signature") if depth_target else None,
        "depth_surface_width": int(depth_target["surface_width"]) if depth_target else 0,
        "depth_surface_height": int(depth_target["surface_height"]) if depth_target else 0,
        "depth_surface_format": depth_format,
        "vulkan_depth_format": vulkan_depth_format,
        "clear_color_argb": int(clear.get("color", 0)),
        "clear_depth": float(clear.get("depth", 1.0)),
        "clear_stencil": int(clear.get("stencil", 0)),
        "clear_flags": int(clear.get("clear_flags", 0)),
        "capture_event_index": int(draw["event_index"]),
        "render_target_signature": target.get("resource_signature"),
    }
    if not (viewport_state["clear_flags"] & 1 and viewport_state["clear_flags"] & 2):
        raise ValueError("capture replay requires a color and depth clear before the draw")
    _write_json(output / "render_target.json", viewport_state)

    sources = (
        ("capture.vertex.glsl", linked["vulkan_vertex_glsl"], "vert", "capture.vertex.glsl.spv"),
        ("capture.pixel.glsl", linked["vulkan_pixel_glsl"], "frag", "capture.pixel.glsl.spv"),
    )
    compiler = shutil.which("glslangValidator")
    if not compiler:
        raise ValueError("glslangValidator is required to build a native Vulkan replay bundle")
    spirv_dir = output / "spirv"
    spirv_dir.mkdir(exist_ok=True)
    for source_name, source, stage, spirv_name in sources:
        source_path = output / source_name
        source_path.write_text(source, encoding="utf-8")
        compiled = subprocess.run(
            [compiler, "-V", "-S", stage, str(source_path), "-o", str(spirv_dir / spirv_name)],
            capture_output=True, text=True, check=False,
        )
        if compiled.returncode:
            raise ValueError(f"captured {stage} shader SPIR-V compilation failed: {compiled.stderr.strip()}")

    capture_hash = hashlib.sha256()
    with capture_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            capture_hash.update(chunk)
    evidence = {
        "format": FORMAT,
        "capture": capture_path.name,
        "capture_sha256": capture_hash.hexdigest(),
        "event_index": int(draw["event_index"]),
        "frame": int(draw.get("frame", 0)),
        "device_ptr": draw.get("device_ptr"),
        "draw": {
            "primitive_type": int(draw["primitive_type"]),
            "base_vertex_index": int(draw["base_vertex_index"]),
            "min_vertex_index": int(draw["min_vertex_index"]),
            "num_vertices": int(draw["num_vertices"]),
            "start_index": int(draw["start_index"]),
            "primitive_count": primitive_count,
            "vk_index_count": draw_index_count,
            "vk_index_type": "VK_INDEX_TYPE_UINT16",
        },
        "resources": {
            "vertex_buffer_ptr": vb_ptr,
            "vertex_buffer_create_event": int(vertex_create["event_index"]),
            "vertex_payload_event": int(vertex_payload["event_index"]),
            "vertex_payload_sha256": hashlib.sha256(vertex_path.read_bytes()).hexdigest(),
            "index_buffer_ptr": ib_ptr,
            "index_buffer_create_event": int(index_create["event_index"]),
            "index_payload_event": int(index_payload["event_index"]),
            "index_payload_sha256": hashlib.sha256(index_path.read_bytes()).hexdigest(),
            "vertex_declaration_signature": declaration_state.get("resource_signature"),
            "vertex_shader_signature": vertex_shader_row.get("resource_signature"),
            "pixel_shader_signature": pixel_shader_row.get("resource_signature"),
            "texture_path": f"textures/{texture_path.name}",
            "texture_sha256": hashlib.sha256(texture_path.read_bytes()).hexdigest(),
        },
        "shader_validation": validation,
        "render_target": viewport_state,
        "snapshot_limitations": [
            "buffer payload is a capture-local COM-generation snapshot; the capture does not record VB/IB lock and unlock updates",
            "the original render-target pixels are not captured; output is a single-draw replay on the captured clear color and depth",
            "this bundle does not claim image parity with the retail frame",
        ],
        "native_submission_ready": True,
        "retail_parity": False,
    }
    _write_json(output / "draw_evidence.json", evidence)
    _write_json(output / "native_submission_gate.json", {
        "format": "SHIFT.NativeSubmissionGate/1",
        "ready": True,
        "blocking_reasons": [],
        "submission_kind": "captured-d3d9-draw-replay",
        "retail_parity": False,
        "capture_sha256": evidence["capture_sha256"],
        "capture_event_index": int(draw["event_index"]),
        "buffer_payload_sha256": [
            evidence["resources"]["vertex_payload_sha256"],
            evidence["resources"]["index_payload_sha256"],
        ],
        "shader_pair_validated": True,
    })
    return {
        "format": FORMAT,
        "output": str(output),
        "capture_event_index": int(draw["event_index"]),
        "vertex_count": len(vertex_bytes) // stride,
        "draw_index_count": draw_index_count,
        "index_format": "INDEX16",
        "attributes": attributes,
        "shader_validation": validation,
        "texture_packet": texture_report,
        "retail_parity": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a native Vulkan replay bundle for one captured D3D9 draw")
    parser.add_argument("capture_jsonl")
    parser.add_argument("event_index", type=int)
    parser.add_argument("output_dir")
    args = parser.parse_args(argv)
    result = build_vulkan_capture_bundle(args.capture_jsonl, args.event_index, args.output_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
