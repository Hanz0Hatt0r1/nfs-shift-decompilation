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
    packet["submeshes"][0]["material"]["paint_shader_gate"] = None
    report=validate_bmw_golden_gate(golden,packet)
    assert report["ready"] is False
    assert "paint-shader:0:missing" in report["blocking_reasons"]
