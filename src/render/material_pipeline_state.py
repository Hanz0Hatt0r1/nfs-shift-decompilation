"""Translate source-backed BMT depth/blend state into Vulkan pipeline state."""
from __future__ import annotations

from typing import Any, Mapping

from material_cull_state import translate_bmt_cull

FORMAT = "SHIFT.MaterialPipelineState/1"

_TEST_FUNCTIONS = [
    ("ETF_FAIL", 0, 1, "D3DCMP_NEVER", "VK_COMPARE_OP_NEVER"),
    ("ETF_LESS_THAN", 1, 2, "D3DCMP_LESS", "VK_COMPARE_OP_LESS"),
    ("ETF_EQUAL", 2, 3, "D3DCMP_EQUAL", "VK_COMPARE_OP_EQUAL"),
    (
        "ETF_LESS_THAN_OR_EQUAL",
        3,
        4,
        "D3DCMP_LESSEQUAL",
        "VK_COMPARE_OP_LESS_OR_EQUAL",
    ),
    ("ETF_GREATER_THAN", 4, 5, "D3DCMP_GREATER", "VK_COMPARE_OP_GREATER"),
    ("ETF_NOT_EQUAL", 5, 6, "D3DCMP_NOTEQUAL", "VK_COMPARE_OP_NOT_EQUAL"),
    (
        "ETF_GREATER_THAN_OR_EQUAL",
        6,
        7,
        "D3DCMP_GREATEREQUAL",
        "VK_COMPARE_OP_GREATER_OR_EQUAL",
    ),
    ("ETF_PASS", 7, 8, "D3DCMP_ALWAYS", "VK_COMPARE_OP_ALWAYS"),
]

_BLEND_FACTORS = [
    ("EBF_ZERO", 0, 1, "D3DBLEND_ZERO", "VK_BLEND_FACTOR_ZERO"),
    ("EBF_ONE", 1, 2, "D3DBLEND_ONE", "VK_BLEND_FACTOR_ONE"),
    ("EBF_SOURCE", 2, 3, "D3DBLEND_SRCCOLOR", "VK_BLEND_FACTOR_SRC_COLOR"),
    (
        "EBF_INV_SOURCE",
        3,
        4,
        "D3DBLEND_INVSRCCOLOR",
        "VK_BLEND_FACTOR_ONE_MINUS_SRC_COLOR",
    ),
    (
        "EBF_SOURCE_ALPHA",
        4,
        5,
        "D3DBLEND_SRCALPHA",
        "VK_BLEND_FACTOR_SRC_ALPHA",
    ),
    (
        "EBF_INV_SOURCE_ALPHA",
        5,
        6,
        "D3DBLEND_INVSRCALPHA",
        "VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA",
    ),
    (
        "EBF_DEST_ALPHA",
        6,
        7,
        "D3DBLEND_DESTALPHA",
        "VK_BLEND_FACTOR_DST_ALPHA",
    ),
    (
        "EBF_INV_DEST_ALPHA",
        7,
        8,
        "D3DBLEND_INVDESTALPHA",
        "VK_BLEND_FACTOR_ONE_MINUS_DST_ALPHA",
    ),
    ("EBF_DEST", 8, 9, "D3DBLEND_DESTCOLOR", "VK_BLEND_FACTOR_DST_COLOR"),
    (
        "EBF_INV_DEST",
        9,
        10,
        "D3DBLEND_INVDESTCOLOR",
        "VK_BLEND_FACTOR_ONE_MINUS_DST_COLOR",
    ),
    (
        "EBF_SOURCE_ALPHA_SATURATED",
        10,
        11,
        "D3DBLEND_SRCALPHASAT",
        "VK_BLEND_FACTOR_SRC_ALPHA_SATURATE",
    ),
]

_BLEND_OPS = [
    ("EBO_ADD", 0, 1, "D3DBLENDOP_ADD", "VK_BLEND_OP_ADD"),
    (
        "EBO_DEST_MINUS_SOURCE",
        1,
        3,
        "D3DBLENDOP_REVSUBTRACT",
        "VK_BLEND_OP_REVERSE_SUBTRACT",
    ),
    ("EBO_MIN", 2, 4, "D3DBLENDOP_MIN", "VK_BLEND_OP_MIN"),
    ("EBO_MAX", 3, 5, "D3DBLENDOP_MAX", "VK_BLEND_OP_MAX"),
    (
        "EBO_SOURCE_MINUS_DEST",
        4,
        2,
        "D3DBLENDOP_SUBTRACT",
        "VK_BLEND_OP_SUBTRACT",
    ),
]


def _rows(table: list[tuple[str, int, int, str, str]]) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "engine_name": name,
            "engine_enum_index": index,
            "d3d9_value": d3d9_value,
            "d3d9_name": d3d9_name,
            "vulkan_value": vulkan_value,
        }
        for name, index, d3d9_value, d3d9_name, vulkan_value in table
    }


_TEST_ROWS = _rows(_TEST_FUNCTIONS)
_BLEND_FACTOR_ROWS = _rows(_BLEND_FACTORS)
_BLEND_OP_ROWS = _rows(_BLEND_OPS)


def _bool_value(
    value: Any,
    *,
    default: bool,
    field: str,
    blockers: list[str],
) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    blockers.append(f"material-pipeline:{field}-invalid:{value}")
    return default


def _enum_row(
    value: Any,
    rows: Mapping[str, Mapping[str, Any]],
    *,
    default: str,
    field: str,
    blockers: list[str],
) -> dict[str, Any]:
    if value is None:
        return dict(rows[default])

    raw = value
    index = None
    if isinstance(value, Mapping):
        raw = value.get("raw")
        index = value.get("engine_enum_index")
        if value.get("status") == "unknown":
            blockers.append(
                f"material-pipeline:{field}-unknown:{raw}"
            )
            return dict(rows[default])

    name: str | None = None
    if isinstance(raw, str):
        candidate = raw.strip().upper()
        if candidate in rows:
            name = candidate
        elif candidate.isdigit():
            index = int(candidate)
    elif isinstance(raw, int) and not isinstance(raw, bool):
        index = raw

    if name is None and isinstance(index, int):
        for candidate, row in rows.items():
            if row["engine_enum_index"] == index:
                name = candidate
                break

    if name is None:
        blockers.append(
            f"material-pipeline:{field}-unsupported:{raw}"
        )
        return dict(rows[default])
    return dict(rows[name])


def _unmapped(
    state: Mapping[str, Any] | None,
    label: str,
    blockers: list[str],
) -> None:
    if state and state.get("unmapped_fields"):
        blockers.append(f"material-pipeline:{label}-unmapped-fields")


def translate_bmt_pipeline_state(
    render_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Translate only state with a proven retail D3D9 -> Vulkan mapping."""
    state = dict(render_state or {})
    blockers: list[str] = []

    cull = translate_bmt_cull(state.get("cull"))
    blockers.extend(cull.get("blocking_reasons") or [])

    depth = state.get("depth")
    if depth is not None and not isinstance(depth, Mapping):
        blockers.append("material-pipeline:depth-invalid")
        depth = None
    _unmapped(depth, "depth", blockers)

    # FUN_00839d70 retail defaults:
    # enabled=1, function=3 (LESS_EQUAL), writeenabled=1, bias=0, slopebias=0.
    depth_enabled = _bool_value(
        (depth or {}).get("enabled"),
        default=True,
        field="depth-enabled",
        blockers=blockers,
    )
    depth_write = _bool_value(
        (depth or {}).get("write_enabled"),
        default=True,
        field="depth-write-enabled",
        blockers=blockers,
    )
    depth_compare = _enum_row(
        (depth or {}).get("function"),
        _TEST_ROWS,
        default="ETF_LESS_THAN_OR_EQUAL",
        field="depth-function",
        blockers=blockers,
    )
    for key in ("bias", "slope_bias", "slopebias"):
        if depth and key in depth:
            value = depth.get(key)
            if value not in (None, 0, 0.0):
                blockers.append(
                    f"material-pipeline:depth-bias-unsupported:{key}:{value}"
                )

    alpha_test = state.get("alpha_test")
    if alpha_test is not None and not isinstance(alpha_test, Mapping):
        blockers.append("material-pipeline:alpha-test-invalid")
        alpha_test = None
    _unmapped(alpha_test, "alpha-test", blockers)
    alpha_test_enabled = _bool_value(
        (alpha_test or {}).get("enabled"),
        default=False,
        field="alpha-test-enabled",
        blockers=blockers,
    )
    alpha_test_compare = _enum_row(
        (alpha_test or {}).get("function"),
        _TEST_ROWS,
        default="ETF_PASS",
        field="alpha-test-function",
        blockers=blockers,
    )
    if alpha_test_enabled:
        blockers.append("material-pipeline:alpha-test-enabled-unsupported")

    alpha_blend = state.get("alpha_blend")
    if alpha_blend is not None and not isinstance(alpha_blend, Mapping):
        blockers.append("material-pipeline:alpha-blend-invalid")
        alpha_blend = None
    _unmapped(alpha_blend, "alpha-blend", blockers)
    blend_enabled = _bool_value(
        (alpha_blend or {}).get("enabled"),
        default=False,
        field="blend-enabled",
        blockers=blockers,
    )
    src_color = _enum_row(
        (alpha_blend or {}).get("source_blend"),
        _BLEND_FACTOR_ROWS,
        default="EBF_ONE",
        field="source-blend",
        blockers=blockers,
    )
    dst_color = _enum_row(
        (alpha_blend or {}).get("dest_blend"),
        _BLEND_FACTOR_ROWS,
        default="EBF_ZERO",
        field="dest-blend",
        blockers=blockers,
    )
    color_op = _enum_row(
        (alpha_blend or {}).get("blend_op"),
        _BLEND_OP_ROWS,
        default="EBO_ADD",
        field="blend-op",
        blockers=blockers,
    )

    separate_value = None
    if alpha_blend:
        if "separate_alpha" in alpha_blend:
            separate_value = alpha_blend.get("separate_alpha")
        elif "seperatealpha" in alpha_blend:
            separate_value = alpha_blend.get("seperatealpha")
    separate_alpha = _bool_value(
        separate_value,
        default=False,
        field="separate-alpha",
        blockers=blockers,
    )

    if separate_alpha:
        src_alpha = _enum_row(
            (alpha_blend or {}).get("alpha_source_blend"),
            _BLEND_FACTOR_ROWS,
            default="EBF_ONE",
            field="alpha-source-blend",
            blockers=blockers,
        )
        dst_alpha = _enum_row(
            (alpha_blend or {}).get("alpha_dest_blend"),
            _BLEND_FACTOR_ROWS,
            default="EBF_ZERO",
            field="alpha-dest-blend",
            blockers=blockers,
        )
        alpha_op = _enum_row(
            (alpha_blend or {}).get("alpha_blend_op"),
            _BLEND_OP_ROWS,
            default="EBO_ADD",
            field="alpha-blend-op",
            blockers=blockers,
        )
    else:
        # D3DRS_SEPARATEALPHABLENDENABLE == FALSE: color blend state applies
        # to alpha as well.
        src_alpha = dict(src_color)
        dst_alpha = dict(dst_color)
        alpha_op = dict(color_op)

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "evidence_status": "retail-static",
        "cull": cull,
        "depth": {
            "source_format": (depth or {}).get("format"),
            "enabled": depth_enabled,
            "write_enabled": depth_write,
            "compare": depth_compare,
            "unmapped_fields": list((depth or {}).get("unmapped_fields") or []),
        },
        "alpha_test": {
            "source_format": (alpha_test or {}).get("format"),
            "enabled": alpha_test_enabled,
            "compare": alpha_test_compare,
            "value_normalized": (alpha_test or {}).get("value_normalized"),
            "native_execution": (
                "blocked-shader-discard-required"
                if alpha_test_enabled else "disabled"
            ),
            "unmapped_fields": list(
                (alpha_test or {}).get("unmapped_fields") or []
            ),
        },
        "alpha_blend": {
            "source_format": (alpha_blend or {}).get("format"),
            "enabled": blend_enabled,
            "separate_alpha": separate_alpha,
            "source_blend": src_color,
            "dest_blend": dst_color,
            "blend_op": color_op,
            "alpha_source_blend": src_alpha,
            "alpha_dest_blend": dst_alpha,
            "alpha_blend_op": alpha_op,
            "unmapped_fields": list(
                (alpha_blend or {}).get("unmapped_fields") or []
            ),
        },
        "vulkan": {
            "front_face": "VK_FRONT_FACE_COUNTER_CLOCKWISE",
            "cull_mode": cull.get(
                "vulkan_cull_mode", "VK_CULL_MODE_NONE"
            ),
            "depth_test_enable": depth_enabled,
            "depth_write_enable": depth_write,
            "depth_compare_op": depth_compare["vulkan_value"],
            "blend_enable": blend_enabled,
            "src_color_blend_factor": src_color["vulkan_value"],
            "dst_color_blend_factor": dst_color["vulkan_value"],
            "color_blend_op": color_op["vulkan_value"],
            "src_alpha_blend_factor": src_alpha["vulkan_value"],
            "dst_alpha_blend_factor": dst_alpha["vulkan_value"],
            "alpha_blend_op": alpha_op["vulkan_value"],
        },
        "retail_evidence": {
            "default_constructor": "FUN_00839d70",
            "depth_to_d3d9": "FUN_0083f920",
            "alpha_test_to_d3d9": "FUN_0083f960",
            "alpha_blend_to_d3d9": "FUN_0083f9c0",
            "compare_lookup_va": "0x00b8ecf4",
            "blend_factor_lookup_va": "0x00b8ed38",
            "blend_op_lookup_va": "0x00b8eda8",
        },
    }


__all__ = ["FORMAT", "translate_bmt_pipeline_state"]
