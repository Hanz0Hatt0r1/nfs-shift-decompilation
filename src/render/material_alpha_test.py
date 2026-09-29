"""Exact retail D3D9 alpha-test contract without unproven Vulkan emulation."""
from __future__ import annotations

import math
from typing import Any, Mapping

FORMAT = "SHIFT.MaterialAlphaTestContract/1"

_COMPARE_ROWS = {
    "ETF_FAIL": (0, 1, "D3DCMP_NEVER"),
    "ETF_LESS_THAN": (1, 2, "D3DCMP_LESS"),
    "ETF_EQUAL": (2, 3, "D3DCMP_EQUAL"),
    "ETF_LESS_THAN_OR_EQUAL": (3, 4, "D3DCMP_LESSEQUAL"),
    "ETF_GREATER_THAN": (4, 5, "D3DCMP_GREATER"),
    "ETF_NOT_EQUAL": (5, 6, "D3DCMP_NOTEQUAL"),
    "ETF_GREATER_THAN_OR_EQUAL": (6, 7, "D3DCMP_GREATEREQUAL"),
    "ETF_PASS": (7, 8, "D3DCMP_ALWAYS"),
}
_INDEX_TO_NAME = {row[0]: name for name, row in _COMPARE_ROWS.items()}


def _compare(value: Any, blockers: list[str]) -> dict[str, Any]:
    if value is None:
        name = "ETF_PASS"
    else:
        raw = value
        index = None
        if isinstance(value, Mapping):
            raw = value.get("raw")
            index = value.get("engine_enum_index")
            if value.get("status") == "unknown":
                blockers.append(f"alpha-test:function-unknown:{raw}")
                name = "ETF_PASS"
                raw_index, d3d9_value, d3d9_name = _COMPARE_ROWS[name]
                return {
                    "raw": raw,
                    "engine_name": name,
                    "engine_enum_index": raw_index,
                    "d3d9_value": d3d9_value,
                    "d3d9_name": d3d9_name,
                    "status": "blocked",
                }
        if isinstance(raw, str) and raw.strip().upper() in _COMPARE_ROWS:
            name = raw.strip().upper()
        elif isinstance(raw, str) and raw.strip().isdigit():
            name = _INDEX_TO_NAME.get(int(raw.strip()))
        elif isinstance(raw, int) and not isinstance(raw, bool):
            name = _INDEX_TO_NAME.get(raw)
        elif isinstance(index, int):
            name = _INDEX_TO_NAME.get(index)
        else:
            name = None
        if name is None:
            blockers.append(f"alpha-test:function-unsupported:{raw}")
            name = "ETF_PASS"

    index, d3d9_value, d3d9_name = _COMPARE_ROWS[name]
    return {
        "raw": value.get("raw") if isinstance(value, Mapping) else value,
        "engine_name": name,
        "engine_enum_index": index,
        "d3d9_value": d3d9_value,
        "d3d9_name": d3d9_name,
        "status": "ready" if not blockers else "blocked",
    }


def _enabled(value: Any, blockers: list[str]) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    blockers.append(f"alpha-test:enabled-invalid:{value}")
    return False


def _reference(
    state: Mapping[str, Any],
    *,
    enabled: bool,
    blockers: list[str],
) -> dict[str, Any]:
    raw = state.get("value_raw")
    normalized = state.get("value_normalized")

    if not enabled and raw is None and normalized is None:
        return {
            "bmt_raw": None,
            "normalized": None,
            "d3d9_u8": None,
            "status": "not-used",
        }

    if raw is None and isinstance(normalized, (int, float)) and not isinstance(normalized, bool):
        raw = float(normalized) * 255.0
    if normalized is None and isinstance(raw, (int, float)) and not isinstance(raw, bool):
        normalized = float(raw) / 255.0

    if (
        not isinstance(raw, (int, float))
        or isinstance(raw, bool)
        or not math.isfinite(float(raw))
    ):
        blockers.append(f"alpha-test:reference-invalid:{raw}")
        return {
            "bmt_raw": raw,
            "normalized": normalized,
            "d3d9_u8": None,
            "status": "blocked",
        }

    raw_float = float(raw)
    if raw_float < 0.0 or raw_float > 255.0:
        blockers.append(f"alpha-test:reference-out-of-range:{raw_float}")
    # Retail path: BMT value / 255.0, then ROUND(normalized * 255.0)
    # before D3DRS_ALPHAREF. round-half semantics do not matter for the
    # supplied corpus because observed BMT values are integral; retain a
    # blocker for fractional values rather than guessing.
    nearest = round(raw_float)
    if abs(raw_float - nearest) > 1e-7:
        blockers.append(f"alpha-test:fractional-reference-unproven:{raw_float}")
    ref_u8 = max(0, min(255, int(nearest)))
    normalized_exact = ref_u8 / 255.0

    if isinstance(normalized, (int, float)) and math.isfinite(float(normalized)):
        if abs(float(normalized) - normalized_exact) > 1e-6:
            blockers.append("alpha-test:normalized-reference-mismatch")

    return {
        "bmt_raw": raw_float,
        "normalized": normalized_exact,
        "d3d9_u8": ref_u8,
        "status": "ready" if not blockers else "blocked",
        "retail_conversion": "ROUND((BMT_value/255.0)*255.0)",
    }


def build_alpha_test_contract(
    state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build the exact D3D9 alpha-test state and an explicit native boundary."""
    blockers: list[str] = []
    source = dict(state or {})

    if source.get("unmapped_fields"):
        blockers.append("alpha-test:unmapped-fields")

    enabled = _enabled(source.get("enabled"), blockers)
    compare = _compare(source.get("function"), blockers)
    reference = _reference(source, enabled=enabled, blockers=blockers)

    evidence_ready = not blockers
    native_blockers = list(blockers)
    if enabled:
        native_blockers.append(
            "alpha-test:fragment-alpha-quantization-unproven"
        )
    native_ready = not native_blockers

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if evidence_ready else "blocked",
        "ready": evidence_ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "enabled": enabled,
        "compare": compare,
        "reference": reference,
        "d3d9_render_states": {
            "D3DRS_ALPHATESTENABLE": {
                "id": 15,
                "value": 1 if enabled else 0,
            },
            "D3DRS_ALPHAFUNC": {
                "id": 25,
                "value": compare["d3d9_value"],
                "name": compare["d3d9_name"],
            },
            "D3DRS_ALPHAREF": {
                "id": 24,
                "value": reference["d3d9_u8"],
            },
        },
        "native_execution": {
            "ready": native_ready,
            "status": "ready" if native_ready else "blocked",
            "blocking_reasons": list(dict.fromkeys(native_blockers)),
            "candidate_output": "fragColor0.a",
            "candidate_threshold": reference["normalized"],
            "required_equivalence": (
                "D3D9 incoming-fragment alpha quantization/comparison before "
                "framebuffer processing"
            ),
        },
        "retail_evidence": {
            "loader_conversion": "FUN_0083f960",
            "device_application": "FUN_00863500",
            "set_render_state_vtable_offset": "0xe4",
            "states": {
                "enable": 15,
                "reference": 24,
                "function": 25,
            },
        },
    }


__all__ = ["FORMAT", "build_alpha_test_contract"]
