"""Exact static storage layout exposed by the two specialized SHIFT providers.

The address spans come directly from the retail provider accessor functions and
their initialization tables. The layout records storage roles by observed
address/range and deliberately avoids assigning unsupported C++ class names.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FORMAT = "SHIFT.SpecializedProviderStorageRuntime/1"


@dataclass(frozen=True)
class ProviderStorageLayout:
    provider_id: int
    selector_global: str
    scalar_count: int
    row_pointer_base: int
    row_pointer_bytes: int
    factor_workspace_base: int
    factor_workspace_doubles: int
    factor_workspace_bytes: int
    output_vector_base: int
    output_vector_doubles: int
    output_vector_bytes: int
    accessor_04: int
    accessor_08: int
    accessor_0c: int
    accessor_24: int
    accessor_28: int
    accessor_2c: int
    accessor_2c_global: str


PROVIDER0_STORAGE = ProviderStorageLayout(
    provider_id=0,
    selector_global="DAT_00c23da8",
    scalar_count=40,
    row_pointer_base=0x00C21698,
    row_pointer_bytes=40 * 4,
    factor_workspace_base=0x00C21738,
    factor_workspace_doubles=0x4A6,
    factor_workspace_bytes=0x4A6 * 8,
    output_vector_base=0x00C23C68,
    output_vector_doubles=40,
    output_vector_bytes=40 * 8,
    accessor_04=0x007D2EB0,
    accessor_08=0x007D2EC0,
    accessor_0c=0x007D2ED0,
    accessor_24=0x007D2EE0,
    accessor_28=0x007D2EF0,
    accessor_2c=0x007D2F00,
    accessor_2c_global="DAT_00b8d8ec",
)

PROVIDER1_STORAGE = ProviderStorageLayout(
    provider_id=1,
    selector_global="DAT_00c23dac",
    scalar_count=34,
    row_pointer_base=0x00C1FDB0,
    row_pointer_bytes=34 * 4,
    factor_workspace_base=0x00C1FE38,
    factor_workspace_doubles=0x2EA,
    factor_workspace_bytes=0x2EA * 8,
    output_vector_base=0x00C21588,
    output_vector_doubles=34,
    output_vector_bytes=34 * 8,
    accessor_04=0x007D2F10,
    accessor_08=0x007D2F20,
    accessor_0c=0x007D2F30,
    accessor_24=0x007D2F40,
    accessor_28=0x007D2F50,
    accessor_2c=0x007D2F60,
    accessor_2c_global="DAT_00b8d8f0",
)


def get_storage_layout(provider_id: int) -> ProviderStorageLayout:
    if provider_id == 0:
        return PROVIDER0_STORAGE
    if provider_id == 1:
        return PROVIDER1_STORAGE
    raise ValueError(f"unsupported provider id: {provider_id}")


def validate_storage_layout(layout: ProviderStorageLayout) -> dict[str, Any]:
    errors: list[str] = []
    if layout.row_pointer_base + layout.row_pointer_bytes != layout.factor_workspace_base:
        errors.append("row-pointer-table-does-not-end-at-factor-workspace")
    if layout.factor_workspace_base + layout.factor_workspace_bytes != layout.output_vector_base:
        errors.append("factor-workspace-does-not-end-at-output-vector")
    if layout.output_vector_doubles != layout.scalar_count:
        errors.append("output-vector-count-does-not-equal-scalar-count")
    if layout.output_vector_bytes != layout.output_vector_doubles * 8:
        errors.append("output-vector-byte-count-mismatch")
    if layout.factor_workspace_bytes != layout.factor_workspace_doubles * 8:
        errors.append("factor-workspace-byte-count-mismatch")
    if layout.row_pointer_bytes != layout.scalar_count * 4:
        errors.append("row-pointer-byte-count-mismatch")
    return {
        "format": "SHIFT.SpecializedProviderStorageValidation/1",
        "version": 1,
        "provider_id": layout.provider_id,
        "ready": not errors,
        "errors": errors,
    }


def build_storage_contract() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for layout in (PROVIDER0_STORAGE, PROVIDER1_STORAGE):
        validation = validate_storage_layout(layout)
        entries.append({
            "provider_id": layout.provider_id,
            "selector_global": layout.selector_global,
            "scalar_count": layout.scalar_count,
            "regions": {
                "row_pointer_table": {
                    "base": hex(layout.row_pointer_base),
                    "bytes": layout.row_pointer_bytes,
                    "entries": layout.scalar_count,
                    "entry_type": "32-bit address",
                },
                "factor_workspace": {
                    "base": hex(layout.factor_workspace_base),
                    "double_count": layout.factor_workspace_doubles,
                    "bytes": layout.factor_workspace_bytes,
                    "constant_from_+0x24": hex(layout.factor_workspace_doubles),
                },
                "output_vector": {
                    "base": hex(layout.output_vector_base),
                    "double_count": layout.output_vector_doubles,
                    "bytes": layout.output_vector_bytes,
                },
            },
            "accessors": {
                "+0x04": {"function": hex(layout.accessor_04), "returns": hex(layout.output_vector_base)},
                "+0x08": {"function": hex(layout.accessor_08), "returns": hex(layout.factor_workspace_base)},
                "+0x0c": {"function": hex(layout.accessor_0c), "returns": hex(layout.row_pointer_base)},
                "+0x24": {"function": hex(layout.accessor_24), "returns": layout.factor_workspace_doubles},
                "+0x28": {"function": hex(layout.accessor_28), "returns": layout.scalar_count},
                "+0x2c": {"function": hex(layout.accessor_2c), "returns_global": layout.accessor_2c_global, "returns_value": layout.factor_workspace_doubles, "equals_plus_0x24": True},
            },
            "boundary_checks": {
                "row_table_end": hex(layout.factor_workspace_base),
                "factor_workspace_end": hex(layout.output_vector_base),
                "output_vector_end": hex(layout.output_vector_base + layout.output_vector_bytes),
            },
            "validation": validation,
        })
    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c / PE .rdata provider accessors",
        "providers": entries,
        "status": "source-backed-static-layout",
        "limitations": [
            "The +0x2c accessor return is preserved as a global reference; its semantic type is unresolved.",
            "The factor workspace is identified by its static address span and size; internal slot semantics remain owned by the provider solve function.",
        ],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(build_storage_contract(), indent=2, sort_keys=True))
