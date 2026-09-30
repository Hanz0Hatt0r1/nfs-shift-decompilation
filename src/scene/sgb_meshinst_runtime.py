"""Source-backed runtime contract for retail SGB MeshInst resources.

Phase 554 proves that .imb/.imx OBJECT resources are promoted to renderer
factory type 7 (MeshInst). Phase 555 follows the concrete type-7 constructor
and loader path. Phases 556-560 progressively recover the binary IMB payload
through a neutral geometry adapter while keeping IMX and higher-level scene
material binding separate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sgb_resource_factory import classify_sgb_object_resource

FORMAT = "SHIFT.SGBMeshInstRuntime/1"

_LOADER_BY_EXTENSION = {
    "imb": {
        "mode": "binary",
        "function": "FUN_00859800",
        "retail_name": (
            "MWL::Renderer::WinRenderer::"
            "CMeshPrimitiveType::LoadBinaryMeshFromResource"
        ),
        "partial_decoder_format": "SHIFT.IMBBinaryMeshSchema/1",
        "partial_decoder": "imb_format.parse_imb_binary_mesh",
        "prefix_auto_detection": "source-backed",
        "neutral_geometry_format": "SHIFT.IMBNeutralGeometry/1",
        "neutral_geometry_adapter": "imb_neutral_geometry.build_imb_neutral_geometry",
    },
    "imx": {
        "mode": "xml",
        "function": "FUN_008587e0",
        "retail_name": (
            "MWL::Renderer::WinRenderer::"
            "CMeshPrimitiveType::LoadXMLMeshFromResource"
        ),
        "xml_root": "MESH",
        "source_evidence": "evidence/imx_xml_mesh_loader_source.json",
        "neutral_geometry_format": "SHIFT.IMXNeutralGeometry/1",
        "neutral_geometry_adapter": (
            "imx_neutral_geometry.build_imx_neutral_geometry"
        ),
    },
}


def build_meshinst_runtime_contract(
    reference: str,
    *,
    descriptor_instance_count: int | None = None,
) -> dict[str, Any]:
    factory = classify_sgb_object_resource(reference)
    if factory.get("factory_type") != 7:
        raise ValueError(
            "MeshInst runtime contract requires a .imb or .imx resource"
        )

    extension = str(factory.get("extension"))
    loader = _LOADER_BY_EXTENSION[extension]

    blockers: list[str] = []
    count: int | None = None
    if descriptor_instance_count is not None:
        try:
            count = int(descriptor_instance_count)
        except (TypeError, ValueError) as exc:
            raise ValueError("descriptor instance count must be an integer") from exc
        if count < 0:
            raise ValueError("descriptor instance count must be non-negative")

    payload_bytes = count * 0x40 if count is not None else None
    allocation_request_bytes = (
        payload_bytes + 0x10 if payload_bytes is not None and count > 0 else None
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": blockers,
        "reference": factory.get("reference"),
        "extension": extension,
        "factory": {
            "type": 7,
            "name": "MeshInst",
            "allocation_bytes": 0xB0,
            "constructor": "FUN_0085ae20",
            "base_class": "MeshType",
            "base_constructor": "FUN_0085aac0",
            "vtable": "PTR_FUN_00b1d480",
        },
        "resource_loader": {
            **loader,
            "source_file": ".\\Source\\Platforms\\Win\\CPrimitiveType.cpp",
            "shared_base_constructor_dispatch": "FUN_0085aac0",
        },
        "runtime_layout": {
            "object_size": 0xB0,
            "base_mesh_type_range": [0x00, 0x7F],
            "instance_count": {
                "runtime_offset": 0x80,
                "source_descriptor_offset": 0x30,
                "usage": "count used for 0x40-stride aligned storage allocation",
                "value": count,
            },
            "instance_storage": {
                "runtime_pointer_offset": 0x84,
                "element_stride": 0x40,
                "alignment": 0x10,
                "payload_bytes": payload_bytes,
                "allocation_request_bytes": allocation_request_bytes,
                "allocator": "FUN_008868c0",
            },
            "zero_initialized_dwords": [
                0x88,
                0x8C,
                0x90,
                0x94,
                0x98,
                0x9C,
                0xA0,
                0xA4,
                0xA8,
                0xAC,
            ],
        },
        "renderer_registration": {
            "register": {
                "function": "FUN_00834a60",
                "renderer_global": "DAT_00c26058",
                "category": 10,
                "condition": "runtime +0x80 != 0",
            },
            "unregister": {
                "function": "FUN_008352f0",
                "renderer_global": "DAT_00c26058",
                "category": 10,
                "destructor": "FUN_0085af00",
            },
        },
        "teardown": {
            "destructor": "FUN_0085af00",
            "aligned_storage_pointer_offset": 0x84,
            "release_offsets": [0x20, 0x8C],
            "release_function": "FUN_0082ea80",
            "base_cleanup": "FUN_0085ac90",
        },
        "mesh_type_base_loader": {
            "constructor": "FUN_0085aac0",
            "in_memory_builder": "FUN_00854e70",
            "xml_loader": "FUN_008587e0",
            "binary_loader": "FUN_00859800",
            "xml_fields_proven": {
                "vertices": "Vertices",
                "streams": "Streams",
                "buffers": "Buffers",
                "environment_map_type": "EnvMapType",
                "bounding_sphere": "BOUNDSPHERE",
                "axis_aligned_box": "AABBOX",
                "bones": "BONES",
            },
        },
        "boundary": {
            "runtime_layout": "source-backed",
            "loader_selection": "source-backed",
            "instance_storage_element_semantics": (
                "0x40-byte elements; exact higher-level matrix/instance "
                "semantics not promoted beyond observed storage use"
            ),
            "serialized_payload_decode": (
                "source-backed v0.4 binary prefix/header/streams/primitives"
                if extension == "imb"
                else (
                    "source-backed XML MESH/STREAM/ITEM/"
                    "INDEXBUFFER/TRIANGLE grammar"
                )
            ),
            "neutral_geometry_adapter": (
                "SHIFT.IMBNeutralGeometry/1"
                if extension == "imb"
                else "SHIFT.IMXNeutralGeometry/1"
            ),
            "unsupported_payload_policy": (
                "preserve evidence and fail closed"
            ),
            "meb_equivalence": False,
            "imb_imx_container_equivalence": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit the source-backed SHIFT MeshInst runtime contract"
    )
    parser.add_argument("resource")
    parser.add_argument("output")
    parser.add_argument("--instance-count", type=int)
    args = parser.parse_args(argv)

    report = build_meshinst_runtime_contract(
        args.resource,
        descriptor_instance_count=args.instance_count,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "resource": report["reference"],
        "loader_mode": report["resource_loader"]["mode"],
        "instance_count": report["runtime_layout"]["instance_count"]["value"],
        "status": report["status"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
