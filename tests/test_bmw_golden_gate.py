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