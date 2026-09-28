"""Capture schema for the specialized SHIFT provider solver path.

Phase 462 records provider-owned solver state without forcing it into the older
builtin 40x40 logical matrix schema. The provider path owns a packed workspace,
a static row-pointer table and an output vector; logical matrix reconstruction
remains a later layer.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from specialized_provider_runtime import get_provider
from specialized_provider_storage_runtime import get_storage_layout
from specialized_provider_row_storage_runtime import get_row_pointers

FORMAT = "SHIFT.SpecializedProviderCaptureRuntime/1"


def normalize_provider_capture(
    capture: Mapping[str, Any],
) -> dict[str, Any]:
    provider_id = int(capture.get("provider_id", -1))
    provider = get_provider(provider_id)
    layout = get_storage_layout(provider_id)

    stage = str(capture.get("stage", "unknown"))
    workspace = [
        float(value)
        for value in (capture.get("workspace") or [])
    ]
    output_vector = [
        float(value)
        for value in (capture.get("output_vector") or [])
    ]
    row_pointers = [
        int(value)
        for value in (capture.get("row_pointers") or [])
    ]

    if len(workspace) != layout.factor_workspace_doubles:
        raise ValueError(
            "workspace length must equal provider factor workspace size"
        )
    if len(output_vector) != layout.output_vector_doubles:
        raise ValueError(
            "output_vector length must equal provider scalar count"
        )
    if row_pointers and len(row_pointers) != layout.scalar_count:
        raise ValueError("row_pointers length must equal scalar count")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "normalized",
        "ready": True,
        "provider_id": provider_id,
        "provider_vtable": hex(provider.vtable_address),
        "solve_function": hex(provider.solve_function),
        "stage": stage,
        "scalar_count": layout.scalar_count,
        "workspace_base": hex(layout.factor_workspace_base),
        "workspace_doubles": layout.factor_workspace_doubles,
        "output_vector_base": hex(layout.output_vector_base),
        "workspace": workspace,
        "output_vector": output_vector,
        "row_pointers": row_pointers,
        "frame_index": capture.get("frame_index"),
        "physics_system": capture.get("physics_system"),
        "source": capture.get("source"),
        "metadata": dict(capture.get("metadata") or {}),
    }


def build_provider_capture_payload(
    *,
    provider_id: int,
    stage: str,
    workspace: Sequence[float],
    output_vector: Sequence[float],
    row_pointers: Sequence[int] | None = None,
    frame_index: int | None = None,
    physics_system: int | None = None,
    source: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    layout = get_storage_layout(provider_id)
    if len(workspace) != layout.factor_workspace_doubles:
        raise ValueError("workspace length does not match provider layout")
    if len(output_vector) != layout.output_vector_doubles:
        raise ValueError("output vector length does not match provider layout")

    pointers = (
        [int(value) for value in row_pointers]
        if row_pointers is not None
        else [int(value) for value in get_row_pointers(provider_id)]
    )

    return normalize_provider_capture(
        {
            "provider_id": provider_id,
            "stage": stage,
            "workspace": list(workspace),
            "output_vector": list(output_vector),
            "row_pointers": pointers,
            "frame_index": frame_index,
            "physics_system": physics_system,
            "source": source,
            "metadata": dict(metadata or {}),
        }
    )


def compare_provider_geometry(
    capture: Mapping[str, Any],
    *,
    provider_id: int,
) -> dict[str, Any]:
    normalized = normalize_provider_capture(capture)
    expected = get_storage_layout(provider_id)
    errors: list[str] = []

    if normalized["provider_id"] != int(provider_id):
        errors.append("provider-id-mismatch")
    if normalized["workspace_doubles"] != expected.factor_workspace_doubles:
        errors.append("workspace-size-mismatch")
    if normalized["scalar_count"] != expected.scalar_count:
        errors.append("scalar-count-mismatch")

    expected_pointers = get_row_pointers(provider_id)
    observed_pointers = normalized["row_pointers"]

    pointer_mismatches = []
    if observed_pointers:
        for index, (expected_pointer, observed_pointer) in enumerate(
            zip(expected_pointers, observed_pointers)
        ):
            if expected_pointer != observed_pointer:
                pointer_mismatches.append(
                    {
                        "row": index,
                        "expected": hex(expected_pointer),
                        "observed": hex(observed_pointer),
                    }
                )

    if pointer_mismatches:
        errors.append("row-pointer-table-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderCaptureGeometryComparison/1",
        "version": 1,
        "provider_id": provider_id,
        "ready": not errors,
        "errors": errors,
        "scalar_count": normalized["scalar_count"],
        "workspace_doubles": normalized["workspace_doubles"],
        "row_pointer_mismatch_count": len(pointer_mismatches),
        "row_pointer_mismatches": pointer_mismatches,
        "solve_function": normalized["solve_function"],
        "stage": normalized["stage"],
    }


def describe_provider_capture_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "providers": [
            {
                "provider_id": provider_id,
                "scalar_count": get_storage_layout(provider_id).scalar_count,
                "workspace_doubles": get_storage_layout(provider_id).factor_workspace_doubles,
                "workspace_base": hex(get_storage_layout(provider_id).factor_workspace_base),
                "output_vector_base": hex(get_storage_layout(provider_id).output_vector_base),
                "solve_function": hex(get_provider(provider_id).solve_function),
                "row_pointer_count": len(get_row_pointers(provider_id)),
            }
            for provider_id in (0, 1)
        ],
        "stages": [
            "pre-solve-provider",
            "post-solve-provider",
        ],
        "scope": {
            "workspace": "raw provider packed workspace doubles",
            "row_pointers": "raw provider static row-pointer addresses",
            "output_vector": "raw provider output-vector doubles",
            "logical_matrix": "not inferred",
        },
        "limitations": [
            "The provider capture does not map packed workspace bytes to the older logical matrix schema.",
            "Provider solve return capture requires a runtime debugger hook; this module only defines the data contract.",
            "No provider class name, physical unit, or matrix semantic is inferred.",
        ],
        "status": "source-backed-provider-capture-schema",
    }


__all__ = [
    "FORMAT",
    "normalize_provider_capture",
    "build_provider_capture_payload",
    "compare_provider_geometry",
    "describe_provider_capture_contract",
]
