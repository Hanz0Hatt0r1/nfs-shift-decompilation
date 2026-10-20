"""Translate the captured D3D9 indexed-draw arguments used by SHIFT."""
from __future__ import annotations

from typing import Any, Mapping


FORMAT = "SHIFT.VulkanD3D9DrawParameters/1"
D3DPT_TRIANGLELIST = 4
D3DFMT_INDEX16 = 101
UINT32_MAX = 0xFFFFFFFF
INT32_MIN = -(1 << 31)
INT32_MAX = (1 << 31) - 1


def _integer(row: Mapping[str, Any], key: str, *, minimum: int, maximum: int) -> int | None:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        return None
    return value


def translate_d3d9_indexed_draw(
    draw_event: Mapping[str, Any],
    index_binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Map captured D3D9 TRIANGLELIST/INDEX16 parameters to Vulkan draw fields.

    This translates parameters only. It does not admit a draw for submission:
    buffer payloads, shader modules, render state, and a render target are separate
    required inputs.
    """
    blockers: list[str] = []
    if draw_event.get("event") != "draw_indexed_primitive":
        blockers.append("d3d9-vulkan-draw:event-invalid")

    primitive_type = _integer(draw_event, "primitive_type", minimum=0, maximum=UINT32_MAX)
    if primitive_type is None:
        blockers.append("d3d9-vulkan-draw:primitive-type-invalid")
    elif primitive_type != D3DPT_TRIANGLELIST:
        blockers.append(f"d3d9-vulkan-draw:unsupported-primitive-type:{primitive_type}")

    primitive_count = _integer(draw_event, "primitive_count", minimum=0, maximum=UINT32_MAX)
    start_index = _integer(draw_event, "start_index", minimum=0, maximum=UINT32_MAX)
    base_vertex_index = _integer(draw_event, "base_vertex_index", minimum=INT32_MIN, maximum=INT32_MAX)
    min_vertex_index = _integer(draw_event, "min_vertex_index", minimum=0, maximum=UINT32_MAX)
    num_vertices = _integer(draw_event, "num_vertices", minimum=0, maximum=UINT32_MAX)
    for key, value in (
        ("primitive-count", primitive_count),
        ("start-index", start_index),
        ("base-vertex-index", base_vertex_index),
        ("min-vertex-index", min_vertex_index),
        ("num-vertices", num_vertices),
    ):
        if value is None:
            blockers.append(f"d3d9-vulkan-draw:{key}-invalid")

    index_count = primitive_count * 3 if primitive_count is not None else None
    if index_count is not None and index_count > UINT32_MAX:
        blockers.append("d3d9-vulkan-draw:index-count-overflow")
    if primitive_count and num_vertices == 0:
        blockers.append("d3d9-vulkan-draw:empty-vertex-window")
    if (
        base_vertex_index is not None
        and min_vertex_index is not None
        and num_vertices is not None
        and num_vertices > 0
    ):
        first_vertex = base_vertex_index + min_vertex_index
        last_vertex = first_vertex + num_vertices - 1
        if first_vertex < INT32_MIN or last_vertex > INT32_MAX:
            blockers.append("d3d9-vulkan-draw:vertex-offset-range-overflow")

    descriptor = index_binding.get("descriptor")
    if not isinstance(descriptor, Mapping):
        descriptor = {}
        blockers.append("d3d9-vulkan-draw:index-descriptor-missing")
    index_format = _integer(descriptor, "format", minimum=0, maximum=UINT32_MAX)
    if index_format is None:
        blockers.append("d3d9-vulkan-draw:index-format-invalid")
    elif index_format != D3DFMT_INDEX16:
        blockers.append(f"d3d9-vulkan-draw:unsupported-index-format:{index_format}")
    index_buffer_length = _integer(descriptor, "length", minimum=1, maximum=UINT32_MAX)
    if index_buffer_length is None:
        blockers.append("d3d9-vulkan-draw:index-buffer-length-invalid")
    elif index_buffer_length % 2:
        blockers.append("d3d9-vulkan-draw:index-buffer-length-unaligned")

    if (
        start_index is not None
        and index_count is not None
        and index_buffer_length is not None
        and (start_index + index_count) * 2 > index_buffer_length
    ):
        blockers.append("d3d9-vulkan-draw:index-range-out-of-bounds")

    translated = not blockers
    return {
        "format": FORMAT,
        "status": "translated" if translated else "blocked",
        "parameter_translation_ready": translated,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "source": {
            "event_index": draw_event.get("event_index"),
            "frame": draw_event.get("frame"),
            "device_ptr": draw_event.get("device_ptr"),
        },
        "source_draw": {
            "primitive_type": primitive_type,
            "base_vertex_index": base_vertex_index,
            "min_vertex_index": min_vertex_index,
            "num_vertices": num_vertices,
            "start_index": start_index,
            "primitive_count": primitive_count,
        },
        "index_binding": {
            "index_buffer_ptr": index_binding.get("index_buffer_ptr"),
            "format": index_format,
            "length_bytes": index_buffer_length,
            "bytes_per_index": 2 if index_format == D3DFMT_INDEX16 else None,
        },
        "vulkan_draw": (
            {
                "topology": "VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST",
                "index_type": "VK_INDEX_TYPE_UINT16",
                "index_count": index_count,
                "instance_count": 1,
                "first_index": start_index,
                "vertex_offset": base_vertex_index,
                "first_instance": 0,
            }
            if translated
            else None
        ),
        "submission_ready": False,
        "submission_blocking_reasons": [
            "d3d9-vulkan-draw:buffer-payload-and-render-pipeline-not-supplied"
        ],
    }
