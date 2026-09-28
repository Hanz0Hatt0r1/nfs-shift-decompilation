"""Static source fingerprint extractor for specialized SHIFT provider solvers.

The retail provider solvers are fully unrolled, so a small source-level parser is
more useful than maintaining hand-copied expressions. This module extracts the
unique reciprocal pivot sequence and the local loop ranges between pivots.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


RECIPROCAL_RE = re.compile(r"1\.0\s*/\s*(_DAT_[0-9A-Fa-f]+)")
LOOP_RE = re.compile(
    r"for\s*\(\s*local_10\s*=\s*(0x[0-9A-Fa-f]+|\d+)\s*;\s*"
    r"local_10\s*<\s*(0x[0-9A-Fa-f]+|\d+)\s*;"
)
FUNCTION_RE_TEMPLATE = r"(?:void|uint|int|undefined\d+\s*\*?)\s+{name}\s*\([^)]*\)\s*\{{"

FORMAT = "SHIFT.SpecializedProviderSourceFingerprint/1"


@dataclass(frozen=True)
class ReciprocalPivot:
    index: int
    source_line: int
    denominator: str
    loop_ranges: tuple[tuple[int, int], ...]


def _parse_int(value: str) -> int:
    return int(value, 0)


def extract_reciprocal_pivots(
    source_lines: Iterable[str],
    *,
    first_source_line: int = 1,
) -> tuple[ReciprocalPivot, ...]:
    lines = list(source_lines)
    found: list[tuple[int, str]] = []
    seen: set[str] = set()

    for offset, line in enumerate(lines):
        match = RECIPROCAL_RE.search(line)
        if not match:
            continue
        denominator = match.group(1)
        if denominator in seen:
            continue
        seen.add(denominator)
        found.append((first_source_line + offset, denominator))

    pivots: list[ReciprocalPivot] = []
    for index, (source_line, denominator) in enumerate(found):
        next_line = (
            found[index + 1][0]
            if index + 1 < len(found)
            else first_source_line + len(lines)
        )
        start_offset = source_line - first_source_line
        end_offset = next_line - first_source_line
        ranges: list[tuple[int, int]] = []
        seen_ranges: set[tuple[int, int]] = set()

        for line in lines[start_offset:end_offset]:
            match = LOOP_RE.search(line)
            if not match:
                continue
            pair = (_parse_int(match.group(1)), _parse_int(match.group(2)))
            if pair not in seen_ranges:
                seen_ranges.add(pair)
                ranges.append(pair)

        pivots.append(
            ReciprocalPivot(
                index=index,
                source_line=source_line,
                denominator=denominator,
                loop_ranges=tuple(ranges),
            )
        )

    return tuple(pivots)


def extract_function_body(
    source: str,
    function_name: str,
    *,
    next_function_marker: str | None = None,
) -> tuple[str, int]:
    """Return one named function body and its 1-based source start line."""
    pattern = re.compile(
        FUNCTION_RE_TEMPLATE.format(name=re.escape(function_name)),
        re.MULTILINE,
    )
    match = pattern.search(source)
    if match is None:
        raise ValueError(f"function {function_name} not found")

    start = match.start()
    start_line = source.count("\n", 0, start) + 1

    if next_function_marker is None:
        return source[start:], start_line

    end = source.find(next_function_marker, match.end())
    if end < 0:
        raise ValueError(
            f"end marker {next_function_marker!r} not found after {function_name}"
        )
    return source[start:end], start_line


def build_provider_source_fingerprint(
    source: str,
    *,
    provider_id: int,
    function_name: str,
    next_function_marker: str | None = None,
    expected_scalar_count: int | None = None,
) -> dict:
    body, start_line = extract_function_body(
        source,
        function_name,
        next_function_marker=next_function_marker,
    )
    pivots = extract_reciprocal_pivots(
        body.splitlines(),
        first_source_line=start_line,
    )

    errors: list[str] = []
    if expected_scalar_count is not None and len(pivots) != expected_scalar_count:
        errors.append(
            f"reciprocal-count:expected={expected_scalar_count}:actual={len(pivots)}"
        )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": int(provider_id),
        "function": function_name,
        "source_start_line": start_line,
        "source_line_count": len(body.splitlines()),
        "unique_reciprocal_count": len(pivots),
        "pivots": [
            {
                "index": pivot.index,
                "source_line": pivot.source_line,
                "denominator": pivot.denominator,
                "loop_ranges": [
                    {"start": start, "end": end}
                    for start, end in pivot.loop_ranges
                ],
            }
            for pivot in pivots
        ],
        "ready": not errors,
        "errors": errors,
    }


def build_fixture_fingerprint() -> dict:
    fixture = """
void FUN_example(void)
{
  double dVar1;
  dVar1 = 1.0 / _DAT_00001000;
  for (local_10 = 1; local_10 < 4; local_10 = local_10 + 1) {
  }
  dVar1 = 1.0 / _DAT_00001008;
  for (local_10 = 2; local_10 < 5; local_10 = local_10 + 1) {
  }
  dVar1 = 1.0 / _DAT_00001010;
}
void FUN_next(void)
{
}
""".lstrip()
    return build_provider_source_fingerprint(
        fixture,
        provider_id=99,
        function_name="FUN_example",
        next_function_marker="void FUN_next(void)",
        expected_scalar_count=3,
    )


__all__ = [
    "FORMAT",
    "ReciprocalPivot",
    "extract_reciprocal_pivots",
    "extract_function_body",
    "build_provider_source_fingerprint",
    "build_fixture_fingerprint",
]
