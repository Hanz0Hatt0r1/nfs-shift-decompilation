from pathlib import Path
import json
from bmw_golden_gate import validate_bmw_golden_gate


def _golden():
    return {
        "format": "SHIFT.BMWGoldenAssetManifest/1",
        "golden": {
            "resource": "vehicles/bmw_m3_e36/body.meb",
            "resource_sha256": "abc",
        },
        "mesh": {
            "vertex_count": 100,
            "triangle_count": 10,
            "color460_descriptor": {"words": [4, 6, 0]},
            "primitives": [
                {"first_index": 0, "index_count": 30, "material": "vehicles/bmw/paint.mtx"}
            ],
        },
    }


def _packet(status="unique"):
    return {
        "mesh": {
            "ref": "vehicles/bmw_m3_e36/body.meb",
            "resolved": {"path": "vehicles/bmw_m3_e36/body.meb", "resource_sha256": "abc"},
            "vertex_count": 100,
            "triangle_count": 10,
        },
        "submeshes": [{
            "first_index": 0,
            "index_count": 30,
            "material": {
                "ref": "vehicles/bmw/paint.mtx",
                "shader_selection": {
                    "status": status,
                    "vertex_pair_selection_status": "unique",
                    "linked_shader_pair": {"format": "SHIFT.LinkedShaderPair/1"},
                    "permutation_identity": {
                        "format": "SHIFT.ShaderPermutationIdentity/1",
                        "identity_sha256": "a" * 64,
                    },
                },
                "paint_shader_gate": {
                    "format": "SHIFT.BMWM3PaintShaderGate/1",
                    "status": "ready",
                    "ready": True,
                    "blocking_reasons": [],
                },
            },
        }],
    }


def test_bmw_golden_gate_accepts_matching_render_packet():
    report = validate_bmw_golden_gate(_golden(), _packet())
    assert report["ready"] is True
    assert report["status"] == "match"
    assert report["blocking_reasons"] == []


def test_bmw_golden_gate_blocks_nonunique_shader_selection():
    report = validate_bmw_golden_gate(_golden(), _packet("ambiguous"))
    assert report["ready"] is False
    assert "shader-selection:0:ambiguous" in report["blocking_reasons"]


def test_bmw_golden_gate_blocks_resource_identity_mismatch():
    packet = _packet()
    packet["mesh"]["resolved"]["resource_sha256"] = "wrong"
    report = validate_bmw_golden_gate(_golden(), packet)
    assert report["ready"] is False
    assert "mesh:resource-sha256-mismatch" in report["blocking_reasons"]


def test_bmw_golden_gate_blocks_missing_resource_identity():
    packet = _packet()
    del packet["mesh"]["resolved"]["resource_sha256"]
    report = validate_bmw_golden_gate(_golden(), packet)
    assert report["ready"] is False
    assert "mesh:resource-sha256-missing" in report["blocking_reasons"]


def test_bmw_golden_gate_blocks_missing_shader_permutation_identity():
    packet = _packet()
    del packet["submeshes"][0]["material"]["shader_selection"]["permutation_identity"]
    report = validate_bmw_golden_gate(_golden(), packet)
    assert report["ready"] is False
    assert "shader-permutation-identity:0:missing" in report["blocking_reasons"]


def test_bmw_golden_gate_blocks_unready_paint_contract():
    golden=_golden()
    packet=_packet()
    packet["submeshes"][0]["material"]["paint_contract"]={
        "ready":False,
        "blocking_reasons":["sampler:diffuseMap:register-mismatch"],
    }
    report=validate_bmw_golden_gate(golden,packet)
    assert report["ready"] is False
    assert "paint-contract:0:sampler:diffuseMap:register-mismatch" in report["blocking_reasons"]


def test_bmw_golden_gate_accepts_ready_paint_contract():
    golden=_golden()
    packet=_packet()
    packet["submeshes"][0]["material"]["paint_contract"]={"ready":True,"blocking_reasons":[]}
    report=validate_bmw_golden_gate(golden,packet)
    assert report["ready"] is True


def test_bmw_golden_gate_blocks_missing_bmw_paint_shader_gate():
    golden=_golden()
    packet=_packet()
    golden["mesh"]["primitives"][0]["material"]="vehicles/bmw_m3_e36/bmw_m3_e36_paint.mtx"
    packet["submeshes"][0]["material"]["ref"]="vehicles/bmw_m3_e36/bmw_m3_e36_paint.mtx"
    packet["submeshes"][0]["material"]["paint_shader_gate"] = None
    report=validate_bmw_golden_gate(golden,packet)
    assert report["ready"] is False
    assert "paint-shader:0:missing" in report["blocking_reasons"]


def test_bmw_golden_gate_requires_shader_gate_only_for_exact_m3_paint():
    golden=_golden()
    packet=_packet()
    packet["submeshes"][0]["material"]["ref"]="vehicles/bmw/bmw_m3_badging.mtx"
    packet["submeshes"][0]["material"].pop("paint_shader_gate", None)
    golden["mesh"]["primitives"][0]["material"]="vehicles/bmw/bmw_m3_badging.mtx"
    report=validate_bmw_golden_gate(golden,packet)
    assert report["ready"] is True


def test_bmw_golden_gate_requires_shader_gate_for_exact_m3_paint_path():
    golden=_golden()
    golden["mesh"]["primitives"][0]["material"]="vehicles/bmw_m3_e36/bmw_m3_e36_paint.mtx"
    packet=_packet()
    packet["submeshes"][0]["material"]["ref"]="vehicles/bmw_m3_e36/bmw_m3_e36_paint.mtx"
    packet["submeshes"][0]["material"].pop("paint_shader_gate", None)
    report=validate_bmw_golden_gate(golden,packet)
    assert report["ready"] is False
    assert "paint-shader:0:missing" in report["blocking_reasons"]


def test_bmw_golden_gate_reports_exact_asset_contract_from_repo_manifest():
    golden=json.loads(
        (Path(__file__).resolve().parents[1] / 'evidence' / 'bmw_m3_e36_kit00_body_loda.golden.json').read_text(
            encoding='utf-8'
        )
    )
    packet=_packet()
    packet["mesh"]["resolved"]={
        "path": golden["golden"]["resource"],
        "resource_sha256": golden["golden"]["resource_sha256"],
    }
    packet["mesh"]["ref"]=golden["golden"]["resource"]
    packet["mesh"]["vertex_count"]=golden["mesh"]["vertex_count"]
    packet["mesh"]["triangle_count"]=golden["mesh"]["triangle_count"]
    base_material=packet["submeshes"][0]["material"]
    packet["submeshes"]=[]
    paint_path="vehicles/bmw_m3_e36/bmw_m3_e36_paint.mtx"
    for primitive in golden["mesh"]["primitives"]:
        material=dict(base_material)
        material["ref"]=primitive["material"]
        if str(primitive["material"]).replace("\\","/").strip("/").lower()!=paint_path:
            material.pop("paint_shader_gate",None)
        else:
            material["paint_shader_gate"]={
                "format":"SHIFT.BMWM3PaintShaderGate/1",
                "status":"ready",
                "ready":True,
                "blocking_reasons":[],
            }
        packet["submeshes"].append({
            "first_index":primitive["first_index"],
            "index_count":primitive["index_count"],
            "material":material,
        })
    report=validate_bmw_golden_gate(golden,packet)
    assert report["ready"] is True
    assert report["asset_contract"]["ready"] is True
