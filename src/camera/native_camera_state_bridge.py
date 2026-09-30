"""Bridge recovered CameraManager snapshot transitions into native_runtime.

The bridge consumes only the evidence-backed numeric subset of
SHIFT.CameraStateSnapshotRuntime/1. The opaque camera source is never
serialized into the native state ABI, and camera math/source vtable behavior is
not inferred.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.NativeCameraStateBridge/1"
SOURCE_FORMAT = "SHIFT.CameraStateSnapshotRuntime/1"


def _i32(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer") from exc
    if result < -(1 << 31) or result > (1 << 31) - 1:
        raise ValueError(f"{field} exceeds int32")
    return result


def _u8(value: Any, field: str) -> int:
    result = _i32(value, field)
    if result < 0 or result > 0xFF:
        raise ValueError(f"{field} exceeds uint8")
    return result


def _index(value: Any, field: str) -> int:
    result = _i32(value, field)
    if result not in (0, 1):
        raise ValueError(f"{field} must be 0 or 1")
    return result


def _blocked(
    blockers: Sequence[str],
    *,
    opaque_camera_source_present: bool = False,
) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "blocked",
        "ready": False,
        "blocking_reasons": list(dict.fromkeys(str(v) for v in blockers)),
        "opaque_camera_source_present": opaque_camera_source_present,
        "boundary": {
            "camera_source_transport": "not-performed",
            "camera_math_inferred": False,
            "projection_defaults_overridden": False,
            "retail_memory_layout_equivalence": False,
        },
    }


def build_native_camera_state_bridge(
    snapshot_report: Mapping[str, Any],
    transitions: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    if snapshot_report.get("format") != SOURCE_FORMAT:
        raise ValueError(
            "snapshot input must be SHIFT.CameraStateSnapshotRuntime/1"
        )

    snapshot = snapshot_report.get("snapshot")
    source_context = snapshot_report.get("source_context")
    if not isinstance(snapshot, Mapping):
        return _blocked(["native-camera:snapshot-payload-missing"])
    if not isinstance(source_context, Mapping):
        return _blocked(["native-camera:source-context-missing"])

    source_value = snapshot.get("word0_camera_source")
    opaque_present = source_value is not None
    blockers: list[str] = []

    try:
        active_index = _index(
            source_context.get("active_buffer_index"),
            "active_buffer_index",
        )
        manager_mode = _i32(
            snapshot.get("word1_mode"),
            "word1_mode",
        )
        buffer_sub_index = _i32(
            snapshot.get("word2_buffer_sub_index"),
            "word2_buffer_sub_index",
        )
        camera_id = _i32(
            snapshot.get("word3_camera_id"),
            "word3_camera_id",
        )
        active_group = _i32(
            snapshot.get("word4_active_group"),
            "word4_active_group",
        )
        if snapshot.get("word5_group_restore_value") is None:
            raise ValueError(
                "word5_group_restore_value is unresolved"
            )
        group_restore_value = _i32(
            snapshot.get("word5_group_restore_value"),
            "word5_group_restore_value",
        )
        active_sub_flag = _u8(
            source_context.get("active_buffer_sub_flag"),
            "active_buffer_sub_flag",
        )
    except ValueError as exc:
        return _blocked(
            [f"native-camera:{exc}"],
            opaque_camera_source_present=opaque_present,
        )

    update_in_progress = False
    transition_rows: list[dict[str, Any]] = []
    for ordinal, transition in enumerate(transitions):
        if transition.get("format") != SOURCE_FORMAT:
            blockers.append(
                f"native-camera:transition-{ordinal}:invalid-format"
            )
            continue

        status = str(transition.get("status") or "")
        if status == "swapped":
            try:
                old_index = _index(
                    transition.get("old_index"),
                    f"transition-{ordinal}.old_index",
                )
                new_index = _index(
                    transition.get("new_index"),
                    f"transition-{ordinal}.new_index",
                )
            except ValueError as exc:
                blockers.append(f"native-camera:{exc}")
                continue
            if (
                transition.get("changed") is not True
                or old_index != active_index
                or new_index != 1 - old_index
                or transition.get("update_in_progress") is not True
            ):
                blockers.append(
                    f"native-camera:transition-{ordinal}:"
                    "swap-sequence-mismatch"
                )
                continue
            active_index = new_index
            update_in_progress = True
            transition_rows.append({
                "ordinal": ordinal,
                "status": status,
                "old_index": old_index,
                "new_index": new_index,
                "update_in_progress": True,
                "source_function": "FUN_0080cd40",
            })
        elif status == "busy":
            try:
                old_index = _index(
                    transition.get("old_index"),
                    f"transition-{ordinal}.old_index",
                )
                new_index = _index(
                    transition.get("new_index"),
                    f"transition-{ordinal}.new_index",
                )
            except ValueError as exc:
                blockers.append(f"native-camera:{exc}")
                continue
            if (
                transition.get("changed") is not False
                or old_index != active_index
                or new_index != active_index
                or transition.get("update_in_progress") is not True
            ):
                blockers.append(
                    f"native-camera:transition-{ordinal}:"
                    "busy-sequence-mismatch"
                )
                continue
            update_in_progress = True
            transition_rows.append({
                "ordinal": ordinal,
                "status": status,
                "old_index": old_index,
                "new_index": new_index,
                "update_in_progress": True,
                "source_function": "FUN_0080cd40",
            })
        elif status == "ready":
            try:
                complete_index = _index(
                    transition.get("active_index"),
                    f"transition-{ordinal}.active_index",
                )
            except ValueError as exc:
                blockers.append(f"native-camera:{exc}")
                continue
            if (
                complete_index != active_index
                or transition.get("update_in_progress") is not False
            ):
                blockers.append(
                    f"native-camera:transition-{ordinal}:"
                    "completion-sequence-mismatch"
                )
                continue
            update_in_progress = False
            transition_rows.append({
                "ordinal": ordinal,
                "status": status,
                "active_index": complete_index,
                "update_in_progress": False,
                "source_functions": [
                    "FUN_0080ec80",
                    "FUN_0080e650",
                ],
            })
        else:
            blockers.append(
                f"native-camera:transition-{ordinal}:"
                f"unsupported-status:{status or 'missing'}"
            )

    if blockers:
        result = _blocked(
            blockers,
            opaque_camera_source_present=opaque_present,
        )
        result["transition_count"] = len(transitions)
        result["accepted_transition_count"] = len(transition_rows)
        return result

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "native_active_index": active_index,
        "native_update_in_progress": update_in_progress,
        "native_manager_mode": manager_mode,
        "native_buffer_sub_index": buffer_sub_index,
        "native_camera_id": camera_id,
        "native_active_group": active_group,
        "native_group_restore_value": group_restore_value,
        "native_active_buffer_sub_flag": active_sub_flag,
        "opaque_camera_source_present": opaque_present,
        "transition_count": len(transition_rows),
        "transitions": transition_rows,
        "source": {
            "snapshot_format": SOURCE_FORMAT,
            "snapshot_function": "FUN_0080e040",
            "buffer_swap_function": "FUN_0080cd40",
            "completion_functions": [
                "FUN_0080ec80",
                "FUN_0080e650",
            ],
        },
        "boundary": {
            "camera_source_transport": "not-performed",
            "camera_source_is_opaque": True,
            "camera_math_inferred": False,
            "projection_defaults_overridden": False,
            "native_double_buffer_state_initialized": True,
            "inactive_buffer_state_inferred": False,
            "retail_memory_layout_equivalence": False,
        },
    }


def validate_files(
    snapshot_path: str | Path,
    transition_paths: Sequence[str | Path] = (),
) -> dict[str, Any]:
    snapshot = json.loads(
        Path(snapshot_path).read_text(encoding="utf-8")
    )
    if not isinstance(snapshot, Mapping):
        raise ValueError("snapshot JSON must be an object")

    transitions: list[Mapping[str, Any]] = []
    for path in transition_paths:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            raise ValueError(
                f"transition JSON must be an object: {path}"
            )
        transitions.append(value)

    return build_native_camera_state_bridge(
        snapshot,
        transitions,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot")
    parser.add_argument("output")
    parser.add_argument(
        "--transition",
        action="append",
        default=[],
        help=(
            "ordered SHIFT.CameraStateSnapshotRuntime/1 swap/complete "
            "report; may be repeated"
        ),
    )
    args = parser.parse_args(argv)

    report = validate_files(
        args.snapshot,
        args.transition,
    )
    Path(args.output).write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "active_index": report.get("native_active_index"),
        "update_in_progress": report.get(
            "native_update_in_progress"
        ),
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
