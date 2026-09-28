"""Extract the recovered declaration-count/sentinel boundary.

FUN_0082ea90 scans 8-byte declaration records by reading the first WORD
(Stream) of each record and stops counting when that value is >= 0xff.
FUN_00830f80 then uses the recovered count to allocate count * 8 + 8 bytes.

This is deliberately separated from exact D3DDECL_END recognition: the
source proves a one-WORD stopping criterion, not that all six sentinel fields
have the documented D3DDECL_END values.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.D3D9DeclarationCountEvidence/1"
COUNT_FUNCTION = "FUN_0082ea90"
CREATE_FUNCTION = "FUN_00830f80"
RECORD_STRIDE = 8


def _function_body(source: str, function: str) -> tuple[int | None, int | None, str]:
    lines = source.splitlines()
    start = None
    for index, line in enumerate(lines, 1):
        if re.search(rf"\b{re.escape(function)}\(", line):
            start = index
            break
    if start is None:
        return None, None, ""
    depth = 0
    seen = False
    body: list[str] = []
    for index in range(start, len(lines) + 1):
        line = lines[index - 1]
        body.append(line)
        depth += line.count("{")
        depth -= line.count("}")
        if "{" in line:
            seen = True
        if seen and depth == 0:
            return start, index, "\n".join(body)
    return start, None, "\n".join(body)


def analyze_d3d9_declaration_count(source: str) -> dict[str, Any]:
    if not isinstance(source, str):
        raise TypeError("source must be str")

    count_start, count_end, count_body = _function_body(source, COUNT_FUNCTION)
    create_start, create_end, create_body = _function_body(source, CREATE_FUNCTION)

    first_stream = "uVar1 = *param_1;" in count_body or "uVar1 = *param_1" in count_body
    increment = "iVar2 = iVar2 + 1;" in count_body
    stride_read = "param_1[iVar2 * 4]" in count_body
    stop_condition = "while (uVar1 < 0xff)" in count_body

    create_count_use = "uVar1 * 8 + 8" in create_body
    create_copy = "_memcpy(puVar6,param_1,uVar1);" in create_body

    observations = {
        "count_function": {
            "status": "observed"
            if count_start is not None else "not-found",
            "line_start": count_start,
            "line_end": count_end,
        },
        "stream_word_is_count_key": {
            "status": "observed" if first_stream else "not-found",
            "detail": "the first WORD of the first declaration record is read before counting",
        },
        "count_increment": {
            "status": "observed" if increment else "not-found",
        },
        "record_stride": {
            "status": "observed" if stride_read else "not-found",
            "element_stride_bytes": RECORD_STRIDE,
            "source_index_scale": 4,
            "source_index_unit": "WORD",
        },
        "stop_condition": {
            "status": "observed" if stop_condition else "not-found",
            "criterion": "Stream >= 0xff",
        },
        "create_function": {
            "status": "observed"
            if create_start is not None else "not-found",
            "line_start": create_start,
            "line_end": create_end,
        },
        "create_buffer_size": {
            "status": "observed" if create_count_use else "not-found",
            "expression": "count * 8 + 8",
        },
        "create_input_copy": {
            "status": "observed" if create_copy else "not-found",
        },
    }

    count_ok = all(
        observations[key]["status"] == "observed"
        for key in (
            "count_function",
            "stream_word_is_count_key",
            "count_increment",
            "record_stride",
            "stop_condition",
        )
    )
    create_ok = all(
        observations[key]["status"] == "observed"
        for key in (
            "create_function",
            "create_buffer_size",
            "create_input_copy",
        )
    )

    return {
        "format": FORMAT,
        "status": "observed" if count_ok and create_ok else "not-proven",
        "source": {
            "kind": "shift-exe-c",
            "bytes": len(source.encode("utf-8")),
            "line_count": len(source.splitlines()),
            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        },
        "count_boundary": {
            "function": COUNT_FUNCTION,
            "record_stride_bytes": RECORD_STRIDE,
            "stop_field": "Stream WORD",
            "stop_criterion": "Stream >= 0xff",
            "first_non-data_stream_value_is_not_required_to_match_full_D3DDECL_END": True,
        },
        "create_boundary": {
            "function": CREATE_FUNCTION,
            "buffer_expression": "count * 8 + 8",
            "extra_record_bytes": 8,
        },
        "observations": observations,
        "semantic_links": {
            "count_to_create_buffer": {
                "status": "observed" if count_ok and create_ok else "not-proven",
                "detail": "the source count drives the 8-byte record buffer allocation used by the declaration creation path",
            },
            "stream_stop_to_exact_end_sentinel": {
                "status": "not-proven",
                "detail": "the recovered source checks only Stream >= 0xff; exact D3DDECL_END fields are not established here",
            },
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "detail": "Declaration count/sentinel evidence does not establish MEB 460/461 -> Type linkage.",
        },
    }


def analyze_d3d9_declaration_count_file(path: str | Path) -> dict[str, Any]:
    source_path = Path(path)
    return analyze_d3d9_declaration_count(
        source_path.read_text(encoding="utf-8")
    )
