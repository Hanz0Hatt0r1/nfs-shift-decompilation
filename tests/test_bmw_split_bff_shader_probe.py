import bmw_split_bff_shader_probe as probe


def test_split_bff_probe_preserves_shader_and_archive_provenance(monkeypatch, tmp_path):
    primary = tmp_path / "BMW_M3_E36.bff"
    render = tmp_path / "RENDER.bff"
    primary.write_bytes(b"primary")
    render.write_bytes(b"render")

    seen = {}

    def fake_builder(path, *, supplemental_bffs=()):
        seen["path"] = path
        seen["supplemental_bffs"] = list(supplemental_bffs)
        return {
            "format": "SHIFT.RealBMWMaterialBindingEvidence/1",
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
            "material_binding": {
                "shader": "bodywork.fx",
                "selection_status": "unique",
                "selected_fxo": {
                    "file": "RENDER.bff::render/shaders/cache/render_shaders_bodywork_test.fxo",
                    "program_offset": 64,
                    "pixel_sha256": "a" * 64,
                    "vertex_sha256": "b" * 64,
                    "pair_sha256": "c" * 64,
                    "permutation_identity": {
                        "format": "SHIFT.ShaderPermutationIdentity/1",
                        "identity_sha256": "d" * 64,
                    },
                },
                "linked_shader_pair": {
                    "format": "SHIFT.LinkedShaderPair/1",
                },
                "linked_shader_error": None,
            },
            "provenance": {
                "primary_bff": {"path": str(primary), "sha256": "1" * 64, "size": 7},
                "supplemental_bffs": [
                    {"path": str(render), "sha256": "2" * 64, "size": 6}
                ],
                "material_entry": {
                    "archive": "BMW_M3_E36.bff",
                    "path": "vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt",
                    "index": 858,
                },
                "mesh_entry": {
                    "archive": "BMW_M3_E36.bff",
                    "path": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
                    "index": 700,
                },
                "shader_source": {
                    "kind": "bff-entry",
                    "archive": "RENDER.bff",
                    "path": "render/shaders/bodywork.fx",
                },
                "fxo_candidate_count": 61,
                "dds_path_count": 3,
            },
        }

    monkeypatch.setattr(probe, "build_real_bmw_material_binding", fake_builder)

    result = probe.build_probe(primary, [render])

    assert result["format"] == "SHIFT.BMWSplitBFFShaderProbe/1"
    assert result["ready"] is True
    assert seen["path"] == primary
    assert seen["supplemental_bffs"] == [render]
    assert result["shader"]["selection_status"] == "unique"
    assert result["shader"]["selected_fxo"]["program_offset"] == 64
    assert result["shader"]["linked_shader_pair_present"] is True
    assert result["provenance"]["shader_source"]["archive"] == "RENDER.bff"
    assert result["provenance"]["fxo_candidate_count"] == 61
    assert result["provenance"]["dds_path_count"] == 3
