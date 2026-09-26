import sys
import types

shift_stub = types.ModuleType("shift_importer")
shift_stub.BFF = object
sys.modules.setdefault("shift_importer", shift_stub)
resource_stub = types.ModuleType("resource_formats")
resource_stub.parse_bmt_material = lambda data: {}
sys.modules.setdefault("resource_formats", resource_stub)

import bmw_m3_material_dependency_parity as mod


def _refs():
    return [
        {"primitive_index": 0, "material_ref": "vehicles/BMW_M3_E36/BADGING.mtx",
         "bmt_ref": "vehicles/bmw_m3_e36/badging.bmt", "triangle_count": 50},
        {"primitive_index": 1, "material_ref": "vehicles/BMW_M3_E36/PAINT.mtx",
         "bmt_ref": "vehicles/bmw_m3_e36/paint.bmt", "triangle_count": 2098},
        {"primitive_index": 2, "material_ref": "vehicles/BMW_M3_E36/PAINT.mtx",
         "bmt_ref": "vehicles/bmw_m3_e36/paint.bmt", "triangle_count": 2462},
    ]


def _payloads():
    return {
        "vehicles/bmw_m3_e36/badging.bmt": {
            "material": {
                "name": "BADGING",
                "shader": "render/shaders/vehicles_basic.fx",
                "textures": ["vehicles/textures/badging.dds"],
            },
            "payload_sha256": "a" * 64,
        },
        "vehicles/bmw_m3_e36/paint.bmt": {
            "material": {
                "name": "PAINT",
                "shader": "render/shaders/bodywork.fx",
                "textures": [
                    "vehicles/textures/common_paint.dds",
                    "vehicles/textures/common_paint_specular.dds",
                ],
            },
            "payload_sha256": "b" * 64,
        },
    }


def _resources():
    return {
        x: {"archive": "x.bff", "entry_index": 1, "type": 2}
        for x in [
            "render/shaders/vehicles_basic.fx",
            "vehicles/textures/badging.dds",
            "render/shaders/bodywork.fx",
            "vehicles/textures/common_paint.dds",
            "vehicles/textures/common_paint_specular.dds",
        ]
    }


def test_dependency_closure_resolves_shader_and_texture_references():
    report = mod.build_dependency_report(
        _refs(), _payloads(), _resources(),
        resource=mod.TARGET_RESOURCE,
        resource_sha256=mod.TARGET_SHA256,
    )
    assert report["ready"] is True
    assert report["unique_bmt_count"] == 2
    assert report["unique_shader_count"] == 2
    assert report["unique_texture_count"] == 3
    assert report["material_reference_use_count"]["vehicles/bmw_m3_e36/paint.bmt"] == 2


def test_missing_shader_or_texture_blocks():
    resources = _resources()
    resources.pop("render/shaders/bodywork.fx")
    report = mod.build_dependency_report(_refs(), _payloads(), resources)
    assert report["ready"] is False
    assert (
        "dependency:resource-missing:vehicles/bmw_m3_e36/paint.bmt:"
        "render/shaders/bodywork.fx"
    ) in report["blocking_reasons"]


def test_bmt_name_mismatch_blocks():
    payloads = _payloads()
    payloads["vehicles/bmw_m3_e36/paint.bmt"]["material"]["name"] = "WRONG"
    report = mod.build_dependency_report(_refs(), payloads, _resources())
    assert report["ready"] is False
    assert any(
        x.startswith("dependency:bmt-name-mismatch:vehicles/bmw_m3_e36/paint.bmt")
        for x in report["blocking_reasons"]
    )


def test_wrong_resource_hash_blocks():
    report = mod.build_dependency_report(
        _refs(), _payloads(), _resources(), resource_sha256="00" * 32
    )
    assert report["ready"] is False
    assert "dependency:unexpected-target-sha256" in report["blocking_reasons"]
