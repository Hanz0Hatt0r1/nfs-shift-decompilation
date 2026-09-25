"""Evidence-backed Trackside Camera selection semantics from SHIFT.exe.

FUN_008119b0 scans the Trackside Cams collection, evaluates each camera with
FUN_008154d0(camera, query), and keeps the index producing the smallest returned
scalar. If the score becomes negative, the runtime returns that index immediately.
An empty collection returns -1 and the initial best score is +FLT_MAX.

This module models only the selection reduction. It intentionally does not call or
interpret FUN_008154d0 itself, because its internal area/vehicle dependencies remain
partially unresolved.
"""

from __future__ import annotations

from math import isfinite
from typing import Any, Callable, Iterable, Sequence

FORMAT = "SHIFT.TracksideCameraSelectionRuntime/1"
FLT_MAX = 3.4028234663852886e38


def select_min_score(
    cameras: Sequence[Any],
    query: Any,
    score_fn: Callable[[Any, Any], float],
) -> dict[str, Any]:
    """Reproduce FUN_008119b0 minimum-score selection and negative early-exit."""
    best_index = -1
    best_score = FLT_MAX
    evaluated = 0
    early_exit = False

    for index, camera in enumerate(cameras):
        score = float(score_fn(camera, query))
        if not isfinite(score):
            raise ValueError(f"camera score at index {index} is not finite")
        evaluated += 1
        if score < best_score:
            best_index = index
            best_score = score
        if score < 0.0:
            early_exit = True
            break

    return {
        "format": FORMAT,
        "version": 1,
        "selected_index": best_index,
        "selected_score": None if best_index < 0 else best_score,
        "evaluated_count": evaluated,
        "early_exit_on_negative_score": early_exit,
        "query_preserved": query,
        "evidence": {
            "selector": "FUN_008119b0",
            "score_function": "FUN_008154d0",
            "initial_best_score": "FLT_MAX",
            "empty_result": -1,
        },
        "limitations": [
            "FUN_008154d0 is not semantically reimplemented",
            "score is kept as a raw scalar; it is not renamed to distance/proximity",
        ],
    }


def select_min_score_values(scores: Iterable[float], *, query: Any = None) -> dict[str, Any]:
    """Convenience adapter for deterministic tests and offline traces."""
    values = list(scores)
    return select_min_score(values, query, lambda score, _query: float(score))
