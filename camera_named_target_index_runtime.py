"""Named target-index bootstrap from FUN_00816f50.

The source contains two fixed target-name tables: nine entries written at the
first output block and twelve entries at the second. Each table scans a
collection of RTTI-0xc25fb8 candidates and compares candidate +0x18 string
against the table name. No match copies the previous output value.
"""

from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.CameraNamedTargetIndexRuntime/1"
TRACKING_RTTI = "DAT_00c25fb8"
FIRST_COUNT = 9
SECOND_COUNT = 12


def resolve_named_indices(
    *,
    desired_names: Sequence[str],
    candidate_names: Sequence[str | None],
    candidate_has_tracking_rtti: Sequence[bool],
    initial_value: int = 0,
) -> dict[str, Any]:
    """Reproduce one of FUN_00816f50's fixed-name resolution loops."""
    if len(candidate_names) != len(candidate_has_tracking_rtti):
        raise ValueError("candidate arrays must have equal length")

    outputs: list[int] = []
    current = int(initial_value)
    trace: list[dict[str, Any]] = []

    for target_index, desired in enumerate(desired_names):
        found = False
        for candidate_index, (name, has_rtti) in enumerate(
            zip(candidate_names, candidate_has_tracking_rtti)
        ):
            if not has_rtti:
                continue
            if str(name or "") == str(desired):
                current = candidate_index
                found = True
                trace.append({
                    "target_index": target_index,
                    "desired_name": str(desired),
                    "candidate_index": candidate_index,
                    "matched": True,
                })
                break
        if not found:
            trace.append({
                "target_index": target_index,
                "desired_name": str(desired),
                "candidate_index": current,
                "matched": False,
                "fallback": "previous output value",
            })
        outputs.append(current)

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "resolve-named-indices",
        "desired_names": list(map(str, desired_names)),
        "outputs": outputs,
        "trace": trace,
        "evidence": {
            "function": "FUN_00816f50",
            "rtti_type": TRACKING_RTTI,
            "candidate_name_offset": "+0x18",
            "no_match_behavior": "copy previous output",
        },
    }


def bootstrap_named_target_indices(
    *,
    first_names: Sequence[str],
    second_names: Sequence[str],
    candidate_names_first: Sequence[str | None],
    candidate_rtti_first: Sequence[bool],
    candidate_names_second: Sequence[str | None],
    candidate_rtti_second: Sequence[bool],
) -> dict[str, Any]:
    """Reproduce the two fixed tables used by FUN_00816f50."""
    if len(first_names) != FIRST_COUNT:
        raise ValueError(f"first_names requires {FIRST_COUNT} entries")
    if len(second_names) != SECOND_COUNT:
        raise ValueError(f"second_names requires {SECOND_COUNT} entries")

    first = resolve_named_indices(
        desired_names=first_names,
        candidate_names=candidate_names_first,
        candidate_has_tracking_rtti=candidate_rtti_first,
    )
    second = resolve_named_indices(
        desired_names=second_names,
        candidate_names=candidate_names_second,
        candidate_has_tracking_rtti=candidate_rtti_second,
    )
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "bootstrap",
        "first_block": first,
        "second_block": second,
        "evidence": {
            "function": "FUN_00816f50",
            "first_output_count": FIRST_COUNT,
            "second_output_count": SECOND_COUNT,
        },
    }
