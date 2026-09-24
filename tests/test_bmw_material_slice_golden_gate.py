import json
from pathlib import Path

from bmw_material_slice_golden_gate import validate_bmw_material_slice_golden


ROOT = Path(__file__).resolve().parents[1]


def _golden():
    return json.loads(
        (ROOT / "evidence" / "bmw_m3_e36_kit00_body_loda.golden.json").read_text(
            encoding="utf-8"
        )
    )


def _slice():
    golden = _golden()
    p = golden["mesh"]["primitives"][1]
    resource = golden["golden"]["resource"]
    sha = golden["golden"]["resource_sha256"]
    return {
        "format": "SHIFT.BMWMaterialSlice/1",
        "ready": True,
        "primitive_index": 1,
        "material_ref": p["material"],
        "golden_identity": {"resource": resource, "resource_sha256": sha},
        "mesh": {
            "resolved": {"path": resource, "resource_sha256": sha},
            "ref": resource,
            "vertex_count": golden["mesh"]["vertex_count"],
            "triangle_count": golden["mesh"]["triangle_count"],
        },
        "paint_contract": {"ready": True, "blocking_reasons": []},
        "paint_shader_gate": {"ready": True, "blocking_reasons": []},
        "render_command": {
            "format": "SHIFT.RenderCommand/1",
            "ready": True,
            "blocking_reasons": [],
            "submeshes": [
                {
                    "first_index": p["first_index"],
                    "index_count": p["index_count"],
                }
            ],
        },
    }


def test_bmw_material_slice_golden_accepts_exact_paint_primitive():
    report = validate_bmw_material_slice_golden(_golden(), _slice())
    assert report["ready"] is True
    assert report["primitive_index"] == 1
    assert report["blocking_reasons"] == []


def test_bmw_material_slice_golden_blocks_wrong_primitive_range():
    data = _slice()
    data["render_command"]["submeshes"][0]["index_count"] += 3
    report = validate_bmw_material_slice_golden(_golden(), data)
    assert report["ready"] is False
    assert "slice:index-count-mismatch" in report["blocking_reasons"]


def test_bmw_material_slice_golden_blocks_wrong_material():
    data = _slice()
    data["material_ref"] = "vehicles/BMW_M3_E36/BMW_M3_E36_BADGING.mtx"
    report = validate_bmw_material_slice_golden(_golden(), data)
    assert report["ready"] is False
    assert "slice:material-ref-mismatch" in report["blocking_reasons"]


def test_bmw_material_slice_golden_blocks_nonready_shader_gate():
    data = _slice()
    data["paint_shader_gate"] = {"ready": False, "blocking_reasons": ["shader-selection:not-unique"]}
    report = validate_bmw_material_slice_golden(_golden(), data)
    assert report["ready"] is False
    assert "slice:paint-shader-gate-not-ready" in report["blocking_reasons"]
