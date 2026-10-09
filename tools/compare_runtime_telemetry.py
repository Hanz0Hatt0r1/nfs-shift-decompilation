#!/usr/bin/env python3
"""Compare frame-aligned retail and native runtime telemetry.

The comparator is intentionally fail-closed: malformed traces, non-contiguous
steps, non-finite values, or mismatched input controls cannot produce a ready
physics-equivalence result.

The default 1% normalized-RMSE limit is an acceptance policy, not a claim about
retail implementation accuracy. Callers can override it explicitly.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.RuntimeTelemetryComparison/1"
TRACE_FORMAT = "SHIFT.RuntimeTelemetryFrame/1"
DEFAULT_MAX_NORMALIZED_RMSE = 0.01
DEFAULT_CONTROL_TOLERANCE = 1e-6

_VECTOR_WIDTHS = {
    "position": 3,
    "orientation_degrees": 3,
    "wheel_loads": 4,
    "tire_temperatures": 4,
}
_SCALAR_FIELDS = ("speed",)
_ANALOG_CONTROLS = ("throttle", "brake", "steer")
_INTEGER_CONTROLS = ("gear",)


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _vector(value: Any, width: int, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != width:
        raise ValueError(f"{label} must contain exactly {width} values")
    return [_finite_number(item, f"{label}[{index}]") for index, item in enumerate(value)]


def _validate_frame(raw: Any, source: str, expected_step: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{source}: frame {expected_step} must be an object")
    if raw.get("format") not in (None, TRACE_FORMAT):
        raise ValueError(
            f"{source}: frame {expected_step} has unsupported format {raw.get('format')!r}"
        )

    step = raw.get("step")
    if isinstance(step, bool) or not isinstance(step, int):
        raise ValueError(f"{source}: frame {expected_step} step must be an integer")
    if step != expected_step:
        raise ValueError(
            f"{source}: telemetry steps must be contiguous from zero; "
            f"expected {expected_step}, got {step}"
        )

    frame: dict[str, Any] = {"step": step}
    for field in _ANALOG_CONTROLS:
        value = _finite_number(raw.get(field), f"{source}: frame {step} {field}")
        if field in ("throttle", "brake") and not 0.0 <= value <= 1.0:
            raise ValueError(f"{source}: frame {step} {field} must be in [0, 1]")
        if field == "steer" and not -1.0 <= value <= 1.0:
            raise ValueError(f"{source}: frame {step} steer must be in [-1, 1]")
        frame[field] = value

    gear = raw.get("gear")
    if isinstance(gear, bool) or not isinstance(gear, int):
        raise ValueError(f"{source}: frame {step} gear must be an integer")
    frame["gear"] = gear

    for field in _SCALAR_FIELDS:
        frame[field] = _finite_number(raw.get(field), f"{source}: frame {step} {field}")
    for field, width in _VECTOR_WIDTHS.items():
        frame[field] = _vector(raw.get(field), width, f"{source}: frame {step} {field}")
    return frame


def load_trace(path: str | Path) -> list[dict[str, Any]]:
    source = str(path)
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{source}: invalid JSON at line {line_number}: {exc}") from exc
            rows.append(_validate_frame(raw, source, len(rows)))
    if not rows:
        raise ValueError(f"{source}: telemetry trace contains no frames")
    return rows


def _rms(values: Iterable[float]) -> float:
    sequence = list(values)
    if not sequence:
        return 0.0
    return math.sqrt(sum(value * value for value in sequence) / len(sequence))


def _wrapped_degrees_error(retail: float, native: float) -> float:
    delta = (native - retail + 180.0) % 360.0 - 180.0
    return abs(delta)


def _position_errors(retail: list[dict[str, Any]], native: list[dict[str, Any]]) -> tuple[list[float], float]:
    errors: list[float] = []
    origin = retail[0]["position"]
    scale_samples: list[float] = []
    for reference, candidate in zip(retail, native):
        errors.append(
            math.sqrt(
                sum(
                    (candidate["position"][axis] - reference["position"][axis]) ** 2
                    for axis in range(3)
                )
            )
        )
        scale_samples.append(
            math.sqrt(
                sum((reference["position"][axis] - origin[axis]) ** 2 for axis in range(3))
            )
        )
    # One metre prevents a stationary/near-origin trace from making normalization singular.
    return errors, max(_rms(scale_samples), 1.0)


def _vector_component_errors(
    retail: list[dict[str, Any]],
    native: list[dict[str, Any]],
    field: str,
    *,
    wrapped_degrees: bool = False,
) -> tuple[list[float], float]:
    errors: list[float] = []
    reference_values: list[float] = []
    for reference, candidate in zip(retail, native):
        for expected, actual in zip(reference[field], candidate[field]):
            if wrapped_degrees:
                errors.append(_wrapped_degrees_error(expected, actual))
            else:
                errors.append(abs(actual - expected))
            reference_values.append(expected)
    if wrapped_degrees:
        # A fixed angular scale avoids discontinuities near +/-180 degrees.
        scale = 180.0
    else:
        scale = max(_rms(reference_values), 1.0)
    return errors, scale


def _scalar_errors(
    retail: list[dict[str, Any]], native: list[dict[str, Any]], field: str
) -> tuple[list[float], float]:
    errors = [abs(candidate[field] - reference[field]) for reference, candidate in zip(retail, native)]
    scale = max(_rms(reference[field] for reference in retail), 1.0)
    return errors, scale


def _metric(errors: list[float], scale: float) -> dict[str, float]:
    rmse = _rms(errors)
    maximum = max(errors, default=0.0)
    return {
        "rmse": rmse,
        "max_abs_error": maximum,
        "normalization_scale": scale,
        "normalized_rmse": rmse / scale,
        "normalized_max_error": maximum / scale,
    }


def _controls_match(
    retail: list[dict[str, Any]],
    native: list[dict[str, Any]],
    tolerance: float,
) -> tuple[bool, list[dict[str, Any]]]:
    mismatches: list[dict[str, Any]] = []
    for reference, candidate in zip(retail, native):
        fields: list[str] = []
        for field in _ANALOG_CONTROLS:
            if abs(reference[field] - candidate[field]) > tolerance:
                fields.append(field)
        for field in _INTEGER_CONTROLS:
            if reference[field] != candidate[field]:
                fields.append(field)
        if fields:
            mismatches.append({"step": reference["step"], "fields": fields})
    return not mismatches, mismatches


def compare_traces(
    retail: list[dict[str, Any]],
    native: list[dict[str, Any]],
    *,
    max_normalized_rmse: float = DEFAULT_MAX_NORMALIZED_RMSE,
    control_tolerance: float = DEFAULT_CONTROL_TOLERANCE,
) -> dict[str, Any]:
    if not 0.0 <= max_normalized_rmse < 1.0:
        raise ValueError("max_normalized_rmse must be in [0, 1)")
    if control_tolerance < 0.0 or not math.isfinite(control_tolerance):
        raise ValueError("control_tolerance must be finite and non-negative")
    if not retail or not native:
        raise ValueError("retail and native telemetry must contain frames")
    if len(retail) != len(native):
        raise ValueError(
            f"telemetry frame count mismatch: retail={len(retail)} native={len(native)}"
        )

    # Revalidate in-memory inputs as well as file-loaded traces so the library API is fail-closed.
    retail = [_validate_frame(frame, "retail", index) for index, frame in enumerate(retail)]
    native = [_validate_frame(frame, "native", index) for index, frame in enumerate(native)]

    controls_match, control_mismatches = _controls_match(retail, native, control_tolerance)

    position_errors, position_scale = _position_errors(retail, native)
    speed_errors, speed_scale = _scalar_errors(retail, native, "speed")
    orientation_errors, orientation_scale = _vector_component_errors(
        retail, native, "orientation_degrees", wrapped_degrees=True
    )
    wheel_errors, wheel_scale = _vector_component_errors(retail, native, "wheel_loads")
    temperature_errors, temperature_scale = _vector_component_errors(
        retail, native, "tire_temperatures"
    )

    metrics = {
        "position": _metric(position_errors, position_scale),
        "speed": _metric(speed_errors, speed_scale),
        "orientation_degrees": _metric(orientation_errors, orientation_scale),
        "wheel_loads": _metric(wheel_errors, wheel_scale),
        "tire_temperatures": _metric(temperature_errors, temperature_scale),
    }
    failing_metrics = sorted(
        name
        for name, metric in metrics.items()
        if metric["normalized_rmse"] > max_normalized_rmse
    )
    blockers: list[str] = []
    if not controls_match:
        blockers.append("telemetry:input-controls-mismatch")
    blockers.extend(f"telemetry:{name}:normalized-rmse-exceeded" for name in failing_metrics)

    return {
        "format": FORMAT,
        "version": 1,
        "frame_count": len(retail),
        "controls_match": controls_match,
        "control_mismatches": control_mismatches,
        "metrics": metrics,
        "policy": {
            "max_normalized_rmse": max_normalized_rmse,
            "control_tolerance": control_tolerance,
            "threshold_kind": "acceptance-policy-not-retail-evidence",
        },
        "blocking_reasons": blockers,
        "ready": not blockers,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("retail", type=Path, help="retail telemetry JSONL")
    parser.add_argument("native", type=Path, help="native telemetry JSONL")
    parser.add_argument(
        "--max-normalized-rmse",
        type=float,
        default=DEFAULT_MAX_NORMALIZED_RMSE,
        help="acceptance policy threshold (default: 0.01 = 1%%)",
    )
    parser.add_argument(
        "--control-tolerance",
        type=float,
        default=DEFAULT_CONTROL_TOLERANCE,
    )
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    result = compare_traces(
        load_trace(args.retail),
        load_trace(args.native),
        max_normalized_rmse=args.max_normalized_rmse,
        control_tolerance=args.control_tolerance,
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
