"""Source-backed SGB OBJECT resource-factory classification.

The retail OBJECT render path does not dispatch directly on MEB/IMB content.
Its resource descriptor starts at type 0, enters renderer factory vfunc +0x214,
and FUN_00831940 promotes only .imb/.imx references to type 7 before the
factory switch.  The two observed factory classes are named MeshType (0) and
MeshInst (7) by the retail cache path.
"""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

FORMAT = "SHIFT.SGBObjectResourceFactory/1"
MESHINST_EXTENSIONS = {"imb", "imx"}

_FACTORY_CASES = {
    0: {
        "factory_name": "MeshType",
        "allocation_bytes": 0x80,
        "constructor": "FUN_0085aac0",
    },
    7: {
        "factory_name": "MeshInst",
        "allocation_bytes": 0xB0,
        "constructor": "FUN_0085ae20",
    },
}


_MESHINST_LOADERS = {
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
    },
    "imx": {
        "mode": "xml",
        "function": "FUN_008587e0",
        "retail_name": (
            "MWL::Renderer::WinRenderer::"
            "CMeshPrimitiveType::LoadXMLMeshFromResource"
        ),
    },
}


def _normalized_reference(reference: str) -> str:
    return reference.replace("\\", "/").strip()


def _extension(reference: str) -> str:
    normalized = _normalized_reference(reference)
    suffix = PurePosixPath(normalized).suffix.lower()
    return suffix[1:] if suffix.startswith(".") else suffix


def classify_sgb_object_resource(reference: str | None) -> dict[str, Any]:
    blockers: list[str] = []
    if reference is None or not str(reference).strip():
        blockers.append("sgb-resource-factory:resource-reference-missing")
        normalized = None
        extension = None
        factory_type = None
        factory = None
    else:
        normalized = _normalized_reference(str(reference))
        extension = _extension(normalized)
        factory_type = 7 if extension in MESHINST_EXTENSIONS else 0
        factory = _FACTORY_CASES[factory_type]

    ready = not blockers
    meshinst = factory_type == 7
    loader = _MESHINST_LOADERS.get(extension) if meshinst else None
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "reference": normalized,
        "extension": extension,
        "descriptor_initial_type": 0,
        "factory_type": factory_type,
        "factory_name": factory.get("factory_name") if factory else None,
        "allocation_bytes": (
            factory.get("allocation_bytes") if factory else None
        ),
        "constructor": factory.get("constructor") if factory else None,
        "extension_promotion": {
            "enabled": meshinst,
            "from_type": 0,
            "to_type": 7 if meshinst else 0,
            "extensions": sorted(MESHINST_EXTENSIONS),
            "extension_compare": "FUN_0040f060",
            "extension_strings": {
                "DAT_00b18c98": "imb",
                "DAT_00b18c94": "imx",
            },
        },
        "renderer_factory": {
            "renderer_global": "DAT_00c26058",
            "object_render_vfunc": "0x00699230",
            "renderer_factory_vfunc_offset": 0x214,
            "renderer_factory_entry": "FUN_00832a50",
            "factory_switch": "FUN_00831940",
            "create_if_missing": True,
        },
        "resource_loader": loader,
        "render_instance": {
            "lookup_vfunc_offset": 0x224,
            "release_vfunc_offset": 0x220,
            "transform_vfunc_offset": 0x2C,
            "meshinst_type7_extra_call": {
                "enabled": meshinst,
                "condition": "resource_descriptor+0x04 == 7",
                "vfunc_offset": 0x04,
                "edx_flag": 1,
                "stack_arguments": [0x100, 0],
            },
        },
        "source": {
            "descriptor_base_constructor": "FUN_008362a0",
            "descriptor_object_constructor": "FUN_00836300",
            "descriptor_type_offset": 0x04,
            "descriptor_initial_type_source": (
                "FUN_00836300 -> FUN_008362a0(param_1, 0)"
            ),
            "factory_source_file": (
                ".\\Source\\Platforms\\Win\\CPrimitiveType.cpp"
            ),
        },
        "boundary": {
            "classification": "source-backed",
            "mesh_payload_decode": "not-asserted",
            "meb_equivalence": "not-asserted",
            "meshinst_to_meb_equivalence": "not-asserted",
        },
    }
