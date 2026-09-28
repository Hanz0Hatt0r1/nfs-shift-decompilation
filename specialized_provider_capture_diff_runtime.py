"""Compare pre/post specialized-provider captures at raw storage level.

Phase 464 reports exactly which packed workspace and output-vector doubles changed
across a provider solve. It intentionally stays below logical-matrix semantics:
addresses are derived from the static provider layout and row-pointer table.
"""
from __future__ import annotations

from typing import Any, Mapping

from specialized_provider_capture_runtime import normalize_provider_capture
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderCaptureDiffRuntime/1"


def _diff_sequence(
    before: list[float],
    after: list[float],
    *,
    base_address: int,
    label: str,
    abs_tol: float,
    rel_tol: float,
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for index, (old, new) in enumerate(zip(before, after)):
        delta = abs(new - old)
        scale = max(abs(old), abs(new))
        threshold = float(abs_tol) + float(rel_tol) * scale
        if delta <= threshold:
            continue
        changes.append(
            {
                "index": index,
                "address": hex(base_address + index * 8),
                "before": old,
                "after": new,
                "abs_delta": delta,
                "rel_delta": delta / scale if scale else 0.0,
                "region": label,
            }
        )
    return changes


def compare_provider_captures(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    pre = normalize_provider_capture(before)
    post = normalize_provider_capture(after)

    errors: list[str] = []
    for field in ("provider_id", "scalar_count", "workspace_doubles"):
        if pre[field] != post[field]:
            errors.append(
                f"{field}-mismatch:{pre[field]}:{post[field]}"
            )

    if pre["row_pointers"] and post["row_pointers"]:
        if pre["row_pointers"] != post["row_pointers"]:
            errors.append("row-pointer-table-mutated")

    layout = get_storage_layout(int(pre["provider_id"]))
    workspace_changes = _diff_sequence(
        pre["workspace"],
        post["workspace"],
        base_address=layout.factor_workspace_base,
        label="factor_workspace",
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )
    output_changes = _diff_sequence(
        pre["output_vector"],
        post["output_vector"],
        base_address=layout.output_vector_base,
        label="output_vector",
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )

    changed_addresses = sorted(
        {
            int(entry["address"], 16)
            for entry in workspace_changes + output_changes
        }
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "matched-shape" if not errors else "blocked",
        "ready": not errors,
        "provider_id": pre["provider_id"],
        "scalar_count": pre["scalar_count"],
        "workspace_changes": workspace_changes,
        "output_changes": output_changes,
        "workspace_change_count": len(workspace_changes),
        "output_change_count": len(output_changes),
        "changed_address_count": len(changed_addresses),
        "changed_addresses": [hex(address) for address in changed_addresses],
        "pre_frame_index": pre.get("frame_index"),
        "post_frame_index": post.get("frame_index"),
        "errors": errors,
    }


def summarize_provider_capture_diff(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "workspace_change_count": int(
            report.get("workspace_change_count", 0)
        ),
        "output_change_count": int(
            report.get("output_change_count", 0)
        ),
        "changed_address_count": int(
            report.get("changed_address_count", 0)
        ),
        "status": report.get("status"),
        "ready": bool(report.get("ready")),
    }


def validate_provider_capture_diff(report: Mapping[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))

    for entry in list(report.get("output_changes") or []):
        index = int(entry.get("index", -1))
        if index < 0 or index >= scalar_count:
            errors.append(f"output-change-index-out-of-domain:{index}")

    for entry in list(report.get("workspace_changes") or []):
        address = int(str(entry["address"]), 16)
        if not (
            int(str(
                hex(
                    0
                )
            )) <= address
        ):
            pass

    if int(report.get("changed_address_count", 0)) != len(
        report.get("changed_addresses") or []
    ):
        errors.append("changed-address-count-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderCaptureDiffValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
    }


def build_capture_diff_contract(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    report = compare_provider_captures(
        before,
        after,
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )
    report["summary"] = summarize_provider_capture_diff(report)
    report["validation"] = validate_provider_capture_diff(report)
    return report


__all__ = [
    "FORMAT",
    "compare_provider_captures",
    "summarize_provider_capture_diff",
    "validate_provider_capture_diff",
    "build_capture_diff_contract",
]
