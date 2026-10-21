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
from shader_interface import D3D9_DECL_USAGE, register_index
from shader_ir import parse_shader_blobs
from texture_reference import decode_dds
from vulkan_texture_packet import build_vulkan_texture_packet

FORMAT = "SHIFT.D3D9CaptureVulkanBundle/1"
GEOMETRY_HEADER = struct.Struct("<4sIIIIII4f")
GEOMETRY_ATTRIBUTE = struct.Struct("<IIIII")
CAPTURE_GEOMETRY = struct.Struct("<IIiI")
CONSTANT_HEADER = struct.Struct("<4sIIIIII")
MAX_CONSTANTS = 256
D3DLOCK_DISCARD = 0x2000
D3DSTREAMSOURCE_INDEXEDDATA = 0x40000000
D3DSTREAMSOURCE_INSTANCEDATA = 0x80000000
D3DSTREAMSOURCE_FREQUENCY_MASK = 0x3FFFFFFF

_D3D_FORMAT = {1: 1, 2: 2, 3: 3, 4: 4}
_SAMPLER_ADDRESS = {
    1: "REPEAT",
    2: "MIRRORED_REPEAT",
    3: "CLAMP_TO_EDGE",
    4: "CLAMP_TO_BORDER",
}
_SAMPLER_FILTER = {1: "NEAREST", 2: "LINEAR"}
_MIP_FILTER = {0: "NONE", 1: "POINT", 2: "LINEAR"}
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
_RENDER_TARGET_FORMAT = {
    21: "VK_FORMAT_B8G8R8A8_UNORM",
    113: "VK_FORMAT_R16G16B16A16_SFLOAT",
    114: "VK_FORMAT_R32_SFLOAT",
}
_DEPTH_FORMAT = {
    75: "VK_FORMAT_D24_UNORM_S8_UINT",
    80: "VK_FORMAT_D16_UNORM",
}


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


def _captured_depth_surface(row: dict[str, Any] | None) -> dict[str, Any] | None:
    return row if row and row.get("surface_ptr") else None


def _payload_precedes_draw(payload: dict[str, Any], draw: dict[str, Any]) -> bool:
    if int(payload.get("event_index", -1)) <= int(draw.get("event_index", -1)):
        return True
    capture_frame = payload.get("payload_capture_frame")
    return isinstance(capture_frame, int) and capture_frame < int(draw.get("frame", 0))


def _draw_bool_constants(
    draw: dict[str, Any], stage: str, program: Any
) -> dict[int, bool]:
    definitions = {
        int(instruction.operands[0].index or 0)
        for instruction in program.instructions
        if instruction.name == "DEFB"
        and instruction.operands
        and instruction.operands[0].kind == "dest"
        and instruction.operands[0].reg_type == 14
    }
    required = set(program.const_bools) - definitions
    if not required:
        return {}
    field = f"{stage}_bool_constants"
    values = draw.get(field)
    set_mask = draw.get(f"{stage}_bool_constant_set_mask")
    if isinstance(set_mask, int) and not isinstance(set_mask, bool):
        if set_mask < 0 or set_mask > 0xFFFF:
            raise ValueError(f"captured {stage} boolean-constant set mask is invalid")
        if not isinstance(values, list) or len(values) != 16:
            raise ValueError(f"captured draw has incomplete {stage} boolean constants")
        for register in required:
            if not (set_mask & (1 << register)):
                raise ValueError(
                    f"captured draw has no written {stage} boolean register b{register}"
                )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            or value > 0xFFFFFFFF
            for value in values
        ):
            raise ValueError(f"captured {stage} boolean constants are not DWORD values")
        return {register: values[register] != 0 for register in required}

    result_hr = draw.get(f"{field}_hr")
    if isinstance(result_hr, bool) or not isinstance(result_hr, int) or result_hr != 0:
        raise ValueError(f"captured draw has no successful {stage} boolean-constant query")
    if not isinstance(values, list) or len(values) != 16:
        raise ValueError(f"captured draw has incomplete {stage} boolean constants")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 0xFFFFFFFF for value in values):
        raise ValueError(f"captured draw has invalid {stage} boolean DWORD constants")
    if max(required) >= len(values):
        raise ValueError(f"captured draw does not include {stage} boolean register b{max(required)}")
    return {register: values[register] != 0 for register in required}


def _captured_stream_frequency_contract(
    draw: dict[str, Any], capture_options: dict[str, Any]
) -> tuple[int, set[int], dict[int, int]]:
    if capture_options.get("stream_source_freq_capture") is not True:
        raise ValueError("capture does not prove SetStreamSourceFreq state")
    rows = draw.get("stream_source_frequencies")
    if not isinstance(rows, list):
        raise ValueError("captured draw has no stream-source frequency state")
    frequencies: dict[int, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("captured stream-source frequency entry is invalid")
        stream = int(row.get("stream", -1))
        setting = int(row.get("setting", -1))
        if stream < 0 or setting < 0 or setting > 0xFFFFFFFF or stream in frequencies:
            raise ValueError("captured stream-source frequency entry is invalid")
        frequencies[stream] = setting

    indexed = []
    instance_streams = set()
    for stream, setting in frequencies.items():
        flags = setting & (D3DSTREAMSOURCE_INDEXEDDATA | D3DSTREAMSOURCE_INSTANCEDATA)
        rate = setting & D3DSTREAMSOURCE_FREQUENCY_MASK
        if flags == D3DSTREAMSOURCE_INDEXEDDATA:
            if stream != 0 or rate == 0:
                raise ValueError("D3D9 indexed-data frequency is invalid")
            indexed.append(rate)
        elif flags == D3DSTREAMSOURCE_INSTANCEDATA:
            if stream == 0 or rate == 0:
                raise ValueError("D3D9 instance-data frequency is invalid")
            instance_streams.add(stream)
        elif flags or setting != 1:
            raise ValueError("captured D3D9 stream frequency is unsupported")

    if not indexed and not instance_streams:
        return 1, set(), frequencies
    if len(indexed) != 1 or not instance_streams:
        raise ValueError("captured D3D9 instancing state is incomplete")
    if indexed[0] != 1:
        raise ValueError(
            f"captured D3D9 draw uses {indexed[0]} instances; multi-instance packets are not supported"
        )
    return 1, instance_streams, frequencies


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
        "constant_register_bits": {
            "vertex": [0] * (MAX_CONSTANTS * 4),
            "pixel": [0] * (MAX_CONSTANTS * 4),
        },
        "constant_registers": {"vertex": set(), "pixel": set()},
        "packet_constant_snapshot": None,
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
    draw_frame = int(draw.get("frame", 0))

    def retain_payload(row: dict[str, Any]) -> None:
        pointer = row.get("buffer_ptr")
        objects["payload"].setdefault(pointer, []).append(row)

    for line in capture_path.open(encoding="utf-8"):
        row = json.loads(line)
        current_event = int(row.get("event_index", -1))
        if current_event > event_index:
            if (
                row.get("event") == "buffer_payload"
                and row.get("process_id") == process_id
                and isinstance(row.get("payload_capture_frame"), int)
                and row["payload_capture_frame"] <= draw_frame
            ):
                retain_payload(row)
            continue
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
            retain_payload(row)

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
        elif event == "device_hooks":
            state["capture_options"] = row
        elif event == "clear":
            state["clear"] = row
            state["clear_render_target"] = state.get("render_target", {}).get("resource_signature")
        elif event in {"set_vertex_shader_constant_f", "set_pixel_shader_constant_f"}:
            stage = "vertex" if event.startswith("set_vertex") else "pixel"
            values = row.get("values") or []
            values_bits = row.get("values_bits")
            start = int(row["start_register"])
            count = int(row["vector4f_count"])
            register_limit = MAX_CONSTANTS if stage == "vertex" else 224
            if start < 0 or count <= 0 or start + count > register_limit:
                raise ValueError(f"invalid {stage} float-constant update at event {current_event}")
            if isinstance(values_bits, list):
                if (
                    len(values_bits) != count * 4
                    or any(
                        isinstance(value, bool)
                        or not isinstance(value, int)
                        or value < 0
                        or value > 0xFFFFFFFF
                        for value in values_bits
                    )
                ):
                    raise ValueError(f"invalid {stage} float-constant DWORDs at event {current_event}")
                bits = values_bits
                values = [
                    struct.unpack("<f", struct.pack("<I", value))[0]
                    for value in values_bits
                ]
            else:
                if len(values) != count * 4 or not all(
                    isinstance(value, (int, float)) and not isinstance(value, bool)
                    for value in values
                ):
                    raise ValueError(f"invalid {stage} float-constant update at event {current_event}")
                bits = [
                    struct.unpack("<I", struct.pack("<f", float(value)))[0]
                    for value in values
                ]
            bank = state[f"{stage}_constants"]
            for index in range(count):
                register = start + index
                bank[register] = [float(x) for x in values[index * 4:index * 4 + 4]]
                state["constant_registers"][stage].add(register)
                state["constant_register_bits"][stage][register * 4:register * 4 + 4] = bits[
                    index * 4:index * 4 + 4
                ]
        elif event == "draw_indexed_primitive":
            snapshot = {}
            for stage, register_count in (("vertex", 256), ("pixel", 224)):
                value_key = f"{stage}_float_constants_bits"
                mask_key = f"{stage}_float_constant_set_mask"
                values_bits = row.get(value_key)
                set_mask = row.get(mask_key)
                if values_bits is None and set_mask is None:
                    continue
                if (
                    not isinstance(values_bits, list)
                    or len(values_bits) != register_count * 4
                    or any(
                        isinstance(value, bool)
                        or not isinstance(value, int)
                        or value < 0
                        or value > 0xFFFFFFFF
                        for value in values_bits
                    )
                    or (set_mask is not None and (
                        not isinstance(set_mask, list)
                        or len(set_mask) != 8
                        or any(
                            isinstance(value, bool)
                            or not isinstance(value, int)
                            or value < 0
                            or value > 0xFFFFFFFF
                            for value in set_mask
                        )
                    ))
                ):
                    raise ValueError(f"captured {stage} packet constant snapshot is invalid")
                snapshot[stage] = {"values_bits": values_bits, "set_mask": set_mask}
            state["packet_constant_snapshot"] = snapshot or None
    packet_snapshot = state["packet_constant_snapshot"]
    if packet_snapshot is not None:
        for stage, snapshot in packet_snapshot.items():
            written = set(state["constant_registers"][stage])
            bits = snapshot["values_bits"]
            mask = snapshot["set_mask"]
            if mask is None:
                # Preserve raw bits, but do not infer the provenance of Set*ConstantF.
                continue
            register_count = 256 if stage == "vertex" else 224
            packet_written = {
                register
                for register in range(register_count)
                if (mask[register // 32] >> (register % 32)) & 1
            }
            if any(
                (mask[register // 32] >> (register % 32)) & 1
                for register in range(register_count, len(mask) * 32)
            ):
                raise ValueError(f"captured {stage} float-constant set mask exceeds the register bank")
            if packet_written != written:
                raise ValueError(f"{stage} float-constant events do not match the packet set mask")
            for register in written:
                start = register * 4
                if state["constant_register_bits"][stage][start:start + 4] != bits[start:start + 4]:
                    raise ValueError(f"{stage} float-constant event bits differ from the packet snapshot")
    return draw, {**state, "objects": objects}


def _resource_file(root: Path, path_value: str, directory: str) -> Path:
    name = PureWindowsPath(path_value).name
    path = root / directory / name
    if not path.is_file():
        raise ValueError(f"capture payload is missing: {path}")
    return path


def _captured_buffer_bytes(
    capture_root: Path,
    payload_rows: list[dict[str, Any]],
    buffer_create: dict[str, Any],
    draw: dict[str, Any],
    capture_options: dict[str, Any],
    buffer_length: int,
    resource_name: str,
) -> tuple[bytes, list[dict[str, Any]]]:
    return _captured_buffer_range(
        capture_root, payload_rows, buffer_create, draw, capture_options,
        buffer_length, 0, buffer_length, resource_name,
    )


def _captured_buffer_range(
    capture_root: Path,
    payload_rows: list[dict[str, Any]],
    buffer_create: dict[str, Any],
    draw: dict[str, Any],
    capture_options: dict[str, Any],
    buffer_length: int,
    required_offset: int,
    required_size: int,
    resource_name: str,
) -> tuple[bytes, list[dict[str, Any]]]:
    if buffer_length <= 0:
        raise ValueError(f"captured {resource_name} has an invalid buffer length")
    if not payload_rows:
        raise ValueError(f"captured {resource_name} has no matching payloads")
    if required_offset < 0 or required_size <= 0 or required_offset + required_size > buffer_length:
        raise ValueError(f"captured {resource_name} draw range exceeds its buffer")
    if not capture_options.get("buffer_payload_capture_enabled") or not capture_options.get(
        "partial_buffer_payload_capture_enabled"
    ):
        raise ValueError(f"captured {resource_name} requires confirmed partial Lock-range capture")
    filter_length = int(capture_options.get("partial_buffer_payload_length_filter", -1))

    create_event = int(buffer_create["event_index"])
    create_frame = int(buffer_create.get("frame", -1))
    draw_frame = int(draw.get("frame", 0))
    required_end = required_offset + required_size
    candidates: list[tuple[int, int, int, bytes, dict[str, Any]]] = []
    for row in payload_rows:
        event_index = int(row.get("event_index", -1))
        capture_frame = int(row.get("payload_capture_frame", row.get("frame", -1)))
        if event_index <= create_event or capture_frame < create_frame:
            continue
        if capture_frame > draw_frame:
            continue
        if not _payload_precedes_draw(row, draw):
            # Trigger-deferred payloads keep their source frame but receive a
            # later event index. Never consume them for a same-frame draw.
            continue
        scope = row.get("capture_scope", "locked-range")
        offset = int(row.get("offset", -1))
        byte_size = int(row.get("captured_byte_size", -1))
        if offset < 0 or byte_size <= 0 or offset + byte_size > buffer_length:
            raise ValueError(f"captured {resource_name} payload range is invalid")
        discard = bool(int(row.get("flags", 0)) & D3DLOCK_DISCARD)
        overlaps = offset < required_end and offset + byte_size > required_offset
        if not overlaps and not discard:
            continue
        if row.get("snapshot_status") != "captured":
            raise ValueError(f"captured {resource_name} buffer payload failed")
        if int(row.get("buffer_length", -1)) != buffer_length:
            raise ValueError(f"captured {resource_name} payload has a different buffer length")
        if scope == "full-buffer" and (offset != 0 or byte_size != buffer_length):
            raise ValueError(f"captured {resource_name} full-buffer snapshot is incomplete")
        if scope != "full-buffer" and filter_length not in (0, buffer_length):
            raise ValueError(f"captured {resource_name} is excluded by the partial payload length filter")
        path = _resource_file(capture_root, str(row.get("payload_path") or ""), "buffers")
        payload = path.read_bytes() if overlaps else b""
        if overlaps and len(payload) != byte_size:
            raise ValueError(f"captured {resource_name} payload size does not match its event")
        candidates.append((capture_frame, event_index, offset, payload, row))

    data = bytearray(required_size)
    covered = bytearray(required_size)
    used_rows: list[dict[str, Any]] = []
    for _, _, offset, payload, row in sorted(candidates, key=lambda item: item[:2]):
        if int(row.get("flags", 0)) & D3DLOCK_DISCARD:
            data[:] = b"\0" * required_size
            covered[:] = b"\0" * required_size
        if not payload:
            continue
        overlap_start = max(offset, required_offset)
        overlap_end = min(offset + len(payload), required_end)
        if overlap_start >= overlap_end:
            continue
        source_start = overlap_start - offset
        destination_start = overlap_start - required_offset
        byte_count = overlap_end - overlap_start
        data[destination_start:destination_start + byte_count] = payload[source_start:source_start + byte_count]
        covered[destination_start:destination_start + byte_count] = b"\1" * byte_count
        used_rows.append(row)

    if 0 in covered:
        first_missing = covered.find(b"\0")
        raise ValueError(
            f"captured {resource_name} payload ranges do not cover the required draw range "
            f"(first missing byte {required_offset + first_missing})"
        )
    return bytes(data), used_rows


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


def _validate_float_constant_set(
    program: Any,
    state: dict[str, Any],
    stage: str,
) -> None:
    defined = {
        int(instruction.operands[0].index or 0)
        for instruction in program.instructions
        if instruction.name == "DEF"
        and instruction.operands
        and instruction.operands[0].kind == "dest"
        and instruction.operands[0].reg_type == 2
    }
    required = {int(register) for register in program.constants} - defined
    missing = required - set(state["constant_registers"][stage])
    if missing:
        registers = ", ".join(f"c{register}" for register in sorted(missing))
        raise ValueError(f"captured draw has no written {stage} float constants: {registers}")


def _declaration(data: bytes) -> list[dict[str, int | str]]:
    elements = []
    for offset in range(0, len(data) - 7, 8):
        stream, element_offset, kind, method, usage, usage_index = struct.unpack_from("<HHBBBB", data, offset)
        if stream == 0xFF:
            break
        if method != 0:
            raise ValueError("captured vertex declaration uses an unsupported method")
        elements.append({
            "stream": stream,
            "offset": element_offset,
            "type": kind,
            "method": method,
            "usage": usage,
            "usage_index": usage_index,
        })
    else:
        raise ValueError("captured vertex declaration has no D3DDECL_END")
    if not elements:
        raise ValueError("captured vertex declaration is empty")
    return elements


def _captured_shader_inputs(
    program: Any,
    elements: list[dict[str, int | str]],
    streams: dict[int, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    element_by_semantic = {
        (int(element["usage"]), int(element["usage_index"])): element
        for element in elements
    }
    if len(element_by_semantic) != len(elements):
        raise ValueError("captured vertex declaration repeats a semantic")
    attributes = []
    bindings = []
    for shader_input in program.inputs:
        usage_name = str(shader_input.get("usage", "")).upper()
        usage = next((key for key, value in D3D9_DECL_USAGE.items() if value == usage_name), None)
        if usage is None:
            raise ValueError(f"unsupported vertex shader semantic {usage_name}")
        usage_index = int(shader_input.get("index", 0))
        element = element_by_semantic.get((usage, usage_index))
        if element is None:
            raise ValueError(f"vertex declaration is missing {usage_name}{usage_index}")
        format_code = _D3D_FORMAT.get(int(element["type"]))
        if format_code is None:
            raise ValueError(f"unsupported captured D3DDECLTYPE {element['type']}")
        element_size = {1: 8, 2: 12, 3: 16, 4: 4}[format_code]
        stream = int(element["stream"])
        stream_state = streams.get(stream)
        if stream_state is None:
            raise ValueError(f"captured vertex declaration stream {stream} is not bound")
        source_stride = int(stream_state.get("stride", 0))
        source_offset = int(element["offset"])
        if source_stride <= 0 or source_offset + element_size > source_stride:
            raise ValueError("captured vertex element exceeds stream stride")
        location = register_index(shader_input.get("register"))
        if location is None or location < 0 or location > 31:
            raise ValueError("captured vertex shader input has an unsupported register")
        attributes.append({
            "location": location,
            "format": format_code,
            "offset": 0,
            "stride": 0,
            "property_id": 0,
            "d3d_type": int(element["type"]),
            "source_stream": stream,
            "source_offset": source_offset,
            "source_stride": source_stride,
            "source_stream_offset": int(stream_state.get("offset_in_bytes", 0)),
        })
        bindings.append({
            "register": str(shader_input.get("register")),
            "location": location,
            "semantic": {"usage": usage_name, "index": usage_index},
            "stream": stream,
            "source_offset": source_offset,
            "source_stride": source_stride,
            "source_stream_offset": int(stream_state.get("offset_in_bytes", 0)),
            "d3d_decl_type": int(element["type"]),
        })
    if len({row["location"] for row in attributes}) != len(attributes):
        raise ValueError("captured vertex shader inputs share a register location")
    if not any(
        row["location"] == 0 and row["format"] == 2
        and next(binding for binding in bindings if binding["location"] == 0)["semantic"]
        == {"usage": "POSITION", "index": 0}
        for row in attributes
    ):
        raise ValueError("captured vertex declaration has no FLOAT3 POSITION0 at location 0")
    return attributes, bindings


def _interleave_vertex_streams(
    attributes: list[dict[str, Any]],
    stream_data: dict[int, tuple[int, bytes]],
    min_vertex: int,
    max_vertex: int,
    instance_streams: set[int] | None = None,
) -> tuple[bytes, int, list[dict[str, Any]]]:
    if not attributes or min_vertex < 0 or max_vertex < min_vertex:
        raise ValueError("captured vertex stream range is invalid")
    element_sizes = {1: 8, 2: 12, 3: 16, 4: 4}
    output_attributes = []
    stride = 0
    for attribute in attributes:
        size = element_sizes[attribute["format"]]
        output_attributes.append({
            **attribute,
            "offset": stride,
            "source_size": size,
        })
        stride += size
    for attribute in output_attributes:
        attribute["stride"] = stride

    vertex_count = max_vertex - min_vertex + 1
    vertices = bytearray(vertex_count * stride)
    instance_streams = instance_streams or set()
    for vertex_index in range(min_vertex, max_vertex + 1):
        destination_base = (vertex_index - min_vertex) * stride
        for attribute in output_attributes:
            source_stream = int(attribute["source_stream"])
            source = stream_data.get(source_stream)
            if source is None:
                raise ValueError(f"captured vertex stream {source_stream} has no payload")
            source_base, payload = source
            element_index = 0 if source_stream in instance_streams else vertex_index
            relative = (
                int(attribute["source_stream_offset"])
                + element_index * int(attribute["source_stride"])
                + int(attribute["source_offset"])
                - source_base
            )
            size = int(attribute["source_size"])
            if relative < 0 or relative + size > len(payload):
                raise ValueError("captured vertex element exceeds its snapshotted stream range")
            destination = destination_base + int(attribute["offset"])
            vertices[destination:destination + size] = payload[relative:relative + size]
            if int(attribute["d3d_type"]) == 4:
                vertices[destination], vertices[destination + 2] = (
                    vertices[destination + 2], vertices[destination]
                )
    for attribute in output_attributes:
        attribute.pop("source_size")
        attribute.pop("source_stride")
        attribute.pop("source_stream")
        attribute.pop("source_offset")
        attribute.pop("source_stream_offset")
        attribute.pop("d3d_type")
    return bytes(vertices), stride, output_attributes


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
        for bits in state["constant_register_bits"][stage]:
            body.extend(struct.pack("<I", bits))
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
    if states[206] not in {0, 1}:
        raise ValueError("captured separate-alpha-blend state is invalid")
    if states[27] not in {0, 1} or states[7] not in {0, 1} or states[14] not in {0, 1}:
        raise ValueError("captured boolean render state is invalid")
    separate_alpha = bool(states[206])
    if separate_alpha and (207 not in states or 208 not in states):
        raise ValueError("captured separate alpha blend factors are incomplete")
    alpha_source = states[207] if separate_alpha else states[19]
    alpha_destination = states[208] if separate_alpha else states[20]
    alpha_operation = states.get(209, 1 if separate_alpha else states[171])
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
            "src_alpha_blend_factor": _BLEND_FACTOR[alpha_source],
            "dst_alpha_blend_factor": _BLEND_FACTOR[alpha_destination],
            "alpha_blend_op": _BLEND_OP[alpha_operation],
            "vulkan_cull_mode": {1: "VK_CULL_MODE_NONE", 2: "VK_CULL_MODE_BACK_BIT", 3: "VK_CULL_MODE_FRONT_BIT"}[states[22]],
            "captured_d3d9_render_states": {str(k): v for k, v in sorted(states.items())},
            "front_face_mapping": "CCW with negative viewport height preserving D3D9 screen orientation",
        }
    except KeyError as exc:
        raise ValueError(f"captured D3D9 render state has unsupported value: {exc.args[0]}") from exc


def _sampler_state(states: dict[int, int]) -> dict[str, Any]:
    required = (1, 2, 5, 6, 7)
    missing = [state for state in required if state not in states]
    if missing:
        raise ValueError("captured sampler state is incomplete")
    try:
        u = _SAMPLER_ADDRESS[states[1]]
        v = _SAMPLER_ADDRESS[states[2]]
        min_filter = _SAMPLER_FILTER[states[6]]
        mag_filter = _SAMPLER_FILTER[states[5]]
        mip_filter = _MIP_FILTER[states[7]]
    except KeyError as exc:
        raise ValueError(f"captured sampler value is unsupported: {exc.args[0]}") from exc
    if u != v:
        raise ValueError("Vulkan replay requires matching captured U/V address modes")
    srgb_value = states.get(11, 0)
    if srgb_value not in (0, 1):
        raise ValueError(f"captured sampler value is unsupported: {srgb_value}")
    result: dict[str, Any] = {
        "address_u": u,
        "address_v": v,
        "min_filter": min_filter,
        "mag_filter": mag_filter,
        "mip_filter": mip_filter,
        "srgb": bool(srgb_value),
    }
    if u == "CLAMP_TO_BORDER":
        border_color = states.get(4, 0)
        if border_color != 0:
            raise ValueError(f"captured D3D9 border color is unsupported: 0x{border_color:08X}")
        result["border_color"] = "TRANSPARENT_BLACK"
    return result


def _validate_texture_mip_filter(mipmaps: int, sampler: dict[str, Any]) -> None:
    if mipmaps <= 0:
        raise ValueError("captured texture has an invalid mip count")
    if mipmaps > 1 and sampler["mip_filter"] != "NONE":
        raise ValueError("captured mip filtering requires native mip-chain support")


def _capture_texture_packet(
    state: dict[str, Any],
    capture_root: Path,
    pixel_program: Any,
    output_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[int, dict[str, str]]]:
    registers = sorted(set(pixel_program.samplers))
    if not registers:
        return {
            "format": "SHIFT.VulkanTexturePacket/1",
            "status": "not-required",
            "texture_count": 0,
        }, [], {}

    textures: dict[int, dict[str, Any]] = {}
    texture_rows: list[dict[str, Any]] = []
    sampler_states: dict[int, dict[str, str]] = {}
    command_rows: list[dict[str, Any]] = []
    for register in registers:
        if register < 0 or register > 15:
            raise ValueError(f"captured pixel sampler is outside s0-s15: s{register}")
        sampler_type = pixel_program.sampler_types.get(register, "sampler2D")
        if sampler_type != "sampler2D":
            raise ValueError(f"capture replay does not support {sampler_type} at s{register}")

        texture_state = state.get("textures", {}).get(register)
        if not texture_state:
            raise ValueError(f"active pixel sampler s{register} has no captured texture binding")
        snapshot_paths = texture_state.get("snapshot_paths") or []
        if texture_state.get("snapshot_status") != "captured" or not snapshot_paths:
            raise ValueError(f"active texture at s{register} has no captured DDS snapshot")
        texture_path = _resource_file(capture_root, str(snapshot_paths[0]), "textures")
        texture_bytes = texture_path.read_bytes()
        texture = decode_dds(texture_bytes)
        sampler = _sampler_state(state["sampler_states"].get(register, {}))
        _validate_texture_mip_filter(int(texture["mipmaps"]), sampler)

        textures[register] = texture
        sampler_states[register] = sampler
        texture_rows.append({
            "register": register,
            "texture_path": f"textures/{texture_path.name}",
            "texture_sha256": hashlib.sha256(texture_bytes).hexdigest(),
            "texture_mipmaps": int(texture["mipmaps"]),
        })
        command_rows.append({
            "d3d9_sampler_register": register,
            "sampler_state": sampler,
        })

    texture_command = {
        "format": "SHIFT.RenderCommand/1",
        "submeshes": [{"textures": command_rows}],
    }
    report = build_vulkan_texture_packet(texture_command, textures, output_path)
    return report, texture_rows, sampler_states


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_vulkan_capture_bundle(capture: str | Path, event_index: int, output_dir: str | Path) -> dict[str, Any]:
    capture_path = Path(capture).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    draw, state = _read_events(capture_path, event_index)
    if any(
        bank["set_mask"] is None
        for bank in (state.get("packet_constant_snapshot") or {}).values()
    ):
        raise ValueError("P1 guest float constant validity masks are missing; raw DWORDs are preserved but replay is unproven")
    if int(draw.get("primitive_type", -1)) != 4:
        raise ValueError("only captured D3DPT_TRIANGLELIST is supported")

    streams = state.get("streams", {})
    indices_state = state.get("indices")
    declaration_state = state.get("declaration")
    vertex_state = state.get("vertex_shader")
    pixel_state = state.get("pixel_shader")
    viewport = state.get("viewport")
    target = state.get("render_target")
    depth_target = _captured_depth_surface(state.get("depth_stencil_surface"))
    clear = state.get("clear")
    if not all((streams, indices_state, declaration_state, vertex_state, pixel_state, viewport, target, clear)):
        raise ValueError("captured draw is missing a required bound resource or state")
    if clear.get("guest_packet_last_clear_unproven_target") is True:
        raise ValueError("P1 packet last_clear has no target identity or ordering proof; refusing synthetic clear")
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
    ib_ptr = indices_state.get("index_buffer_ptr")
    index_create = objects["index_buffer"].get(ib_ptr)
    if not index_create:
        raise ValueError("captured draw lacks an index buffer create record")
    if index_create.get("format") != 101:
        raise ValueError("capture replay requires D3DFMT_INDEX16")
    index_length = int(index_create.get("length", -1))
    index_bytes, index_payload_rows = _captured_buffer_bytes(
        capture_path.parent,
        objects["payload"].get(ib_ptr, []),
        index_create,
        draw,
        state.get("capture_options", {}),
        index_length,
        "index",
    )
    index_payload_sha256 = hashlib.sha256(index_bytes).hexdigest()
    declaration = _declaration(bytes.fromhex(str(objects["declaration"].get(declaration_state["declaration_ptr"], {}).get("bytes_hex") or "")))
    vertex_shader_row = objects["vertex_shader"].get(vertex_state.get("shader_ptr"))
    pixel_shader_row = objects["pixel_shader"].get(pixel_state.get("shader_ptr"))
    if not vertex_shader_row or not pixel_shader_row:
        raise ValueError("active captured shader object was not found")
    if vertex_state.get("resource_signature") != vertex_shader_row.get("resource_signature") or pixel_state.get("resource_signature") != pixel_shader_row.get("resource_signature"):
        raise ValueError("active shader identity does not match its captured bytecode")
    vertex_program = _shader_program(vertex_shader_row, "vertex")
    pixel_program = _shader_program(pixel_shader_row, "pixel")
    _validate_float_constant_set(vertex_program, state, "vertex")
    _validate_float_constant_set(pixel_program, state, "pixel")
    source_attributes, vertex_input_bindings = _captured_shader_inputs(
        vertex_program, declaration, streams
    )
    instance_count, instance_streams, stream_frequencies = (
        _captured_stream_frequency_contract(draw, state.get("capture_options", {}))
    )
    vertex_bool_constants = _draw_bool_constants(draw, "vertex", vertex_program)
    pixel_bool_constants = _draw_bool_constants(draw, "pixel", pixel_program)
    linked = translate_pair(
        vertex_program,
        pixel_program,
        vertex_bool_constants=vertex_bool_constants,
        pixel_bool_constants=pixel_bool_constants,
    )
    validation = validate_linked_shader_pair_vulkan(linked)
    if validation.get("status") != "valid":
        raise ValueError("captured VS/PS pair failed Vulkan compile/link validation")

    primitive_count = int(draw.get("primitive_count", 0))
    draw_index_count = primitive_count * 3
    first_index = int(draw.get("start_index", -1))
    if draw_index_count <= 0 or first_index < 0 or (first_index + draw_index_count) * 2 > len(index_bytes):
        raise ValueError("captured triangle-list draw range exceeds its index buffer")
    raw_indices = [
        struct.unpack_from("<H", index_bytes, index * 2)[0]
        for index in range(first_index, first_index + draw_index_count)
    ]
    original_base_vertex = int(draw.get("base_vertex_index", 0))
    effective_indices = [index + original_base_vertex for index in raw_indices]
    if not effective_indices or min(effective_indices) < 0:
        raise ValueError("captured draw has an invalid effective vertex index")
    min_vertex = min(effective_indices)
    max_vertex = max(effective_indices)
    if max_vertex - min_vertex > 0xffff:
        raise ValueError("captured draw vertex range exceeds its index format")

    stream_data: dict[int, tuple[int, bytes]] = {}
    stream_evidence = []
    stream_resources = {}
    for stream_index in sorted({int(row["source_stream"]) for row in source_attributes}):
        stream = streams[stream_index]
        vb_ptr = stream.get("vertex_buffer_ptr")
        vertex_create = objects["vertex_buffer"].get(vb_ptr)
        if not vertex_create:
            raise ValueError(f"captured vertex stream {stream_index} has no buffer create record")
        vertex_length = int(vertex_create.get("length", -1))
        stream_stride = int(stream.get("stride", 0))
        stream_offset = int(stream.get("offset_in_bytes", 0))
        if stream_stride <= 0:
            raise ValueError(f"captured vertex stream {stream_index} has an invalid stride")
        if stream_index in instance_streams:
            range_offset = stream_offset
            range_size = stream_stride
        else:
            range_offset = stream_offset + min_vertex * stream_stride
            range_size = (max_vertex - min_vertex + 1) * stream_stride
        payload, payload_rows = _captured_buffer_range(
            capture_path.parent,
            objects["payload"].get(vb_ptr, []),
            vertex_create,
            draw,
            state.get("capture_options", {}),
            vertex_length,
            range_offset,
            range_size,
            f"vertex stream {stream_index}",
        )
        stream_data[stream_index] = (range_offset, payload)
        stream_resources[stream_index] = {
            "vertex_buffer_ptr": vb_ptr,
            "vertex_create": vertex_create,
            "payload_rows": payload_rows,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "range_offset": range_offset,
            "range_size": range_size,
            "stride": stream_stride,
            "stream_offset_in_bytes": stream_offset,
        }
        stream_evidence.append({
            "stream": stream_index,
            "vertex_buffer_ptr": vb_ptr,
            "resource_signature": stream.get("resource_signature"),
            "vertex_buffer_create_event": int(vertex_create["event_index"]),
            "usage": int(vertex_create.get("usage", 0)),
            "pool": int(vertex_create.get("pool", -1)),
            "buffer_length": vertex_length,
            "stream_offset_in_bytes": stream_offset,
            "stride": stream_stride,
            "captured_range": {"offset": range_offset, "byte_size": range_size},
            "payload_events": [int(row["event_index"]) for row in payload_rows],
            "payload_ranges": [
                {"offset": int(row["offset"]), "byte_size": int(row["captured_byte_size"])}
                for row in payload_rows
            ],
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
        })

    primary_stream = stream_resources.get(0) or stream_resources[min(stream_resources)]
    vb_ptr = primary_stream["vertex_buffer_ptr"]
    vertex_create = primary_stream["vertex_create"]
    vertex_payload_rows = primary_stream["payload_rows"]
    vertex_bytes, stride, attributes = _interleave_vertex_streams(
        source_attributes, stream_data, min_vertex, max_vertex,
        instance_streams=instance_streams,
    )
    vertex_payload_sha256 = hashlib.sha256(vertex_bytes).hexdigest()
    rebased_indices = [index - min_vertex for index in effective_indices]
    packed_index_bytes = b"".join(struct.pack("<H", index) for index in rebased_indices)
    geometry = encode_capture_geometry(
        vertex_bytes, packed_index_bytes, stride=stride, attributes=attributes,
        index_format_bits=16, first_index=0,
        draw_index_count=draw_index_count,
        base_vertex=0,
        vertex_buffer_offset=0,
    )
    (output / "geometry.svpk").write_bytes(geometry)

    _capture_constants(state, output / "constants.svcp")
    texture_report, texture_rows, samplers = _capture_texture_packet(
        state, capture_path.parent, pixel_program, output / "textures.svtp")

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
            "instance_count": instance_count,
            "vk_index_count": draw_index_count,
            "vk_index_type": "VK_INDEX_TYPE_UINT16",
            "packed_vertex_count": max_vertex - min_vertex + 1,
            "packed_base_vertex": 0,
        },
        "resources": {
            "vertex_buffer_ptr": vb_ptr,
            "vertex_buffer_create_event": int(vertex_create["event_index"]),
            "vertex_payload_events": [int(row["event_index"]) for row in vertex_payload_rows],
            "vertex_payload_ranges": [
                {"offset": int(row["offset"]), "byte_size": int(row["captured_byte_size"])}
                for row in vertex_payload_rows
            ],
            "vertex_payload_sha256": vertex_payload_sha256,
            "vertex_streams": stream_evidence,
            "vertex_input_bindings": vertex_input_bindings,
            "stream_source_frequencies": [
                {"stream": stream, "setting": setting}
                for stream, setting in sorted(stream_frequencies.items())
            ],
            "flattened_single_instance_streams": sorted(instance_streams),
            "buffer_capture_options": {
                "buffer_payload_capture_enabled": bool(
                    state["capture_options"].get("buffer_payload_capture_enabled")
                ),
                "partial_buffer_payload_capture_enabled": bool(
                    state["capture_options"].get("partial_buffer_payload_capture_enabled")
                ),
                "partial_buffer_payload_length_filter": int(
                    state["capture_options"].get("partial_buffer_payload_length_filter", -1)
                ),
            },
            "index_buffer_ptr": ib_ptr,
            "index_buffer_create_event": int(index_create["event_index"]),
            "index_payload_events": [int(row["event_index"]) for row in index_payload_rows],
            "index_payload_ranges": [
                {"offset": int(row["offset"]), "byte_size": int(row["captured_byte_size"])}
                for row in index_payload_rows
            ],
            "index_payload_sha256": index_payload_sha256,
            "vertex_declaration_signature": declaration_state.get("resource_signature"),
            "vertex_shader_signature": vertex_shader_row.get("resource_signature"),
            "pixel_shader_signature": pixel_shader_row.get("resource_signature"),
            "textures": texture_rows,
        },
        "samplers": {str(register): sampler for register, sampler in samplers.items()},
        "shader_validation": validation,
        "bool_constants": {
            "vertex": {str(register): value for register, value in vertex_bool_constants.items()},
            "pixel": {str(register): value for register, value in pixel_bool_constants.items()},
        },
        "constant_capture": {
            "vertex_float_written_registers": sorted(state["constant_registers"]["vertex"]),
            "pixel_float_written_registers": sorted(state["constant_registers"]["pixel"]),
            "vertex_float_set_mask": draw.get("vertex_float_constant_set_mask"),
            "pixel_float_set_mask": draw.get("pixel_float_constant_set_mask"),
            "vertex_bool_values_dwords": draw.get("vertex_bool_constants"),
            "pixel_bool_values_dwords": draw.get("pixel_bool_constants"),
            "vertex_bool_set_mask": draw.get("vertex_bool_constant_set_mask"),
            "pixel_bool_set_mask": draw.get("pixel_bool_constant_set_mask"),
        },
        "render_target": viewport_state,
        "snapshot_limitations": [
            "the original render-target pixels are not captured; output is a single-draw replay on the captured clear color and depth",
            "multi-instance D3D9 draws are rejected; single-instance instance-rate streams are flattened into the captured vertex packet",
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
