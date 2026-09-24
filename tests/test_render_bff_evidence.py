from types import SimpleNamespace

import render_bff_evidence as evidence


def test_extension_counts_and_normalization():
    entries = [
        SimpleNamespace(path="Render/Shaders/bodywork.FX"),
        SimpleNamespace(path="render/shaders/cache/a.FXO"),
        SimpleNamespace(path="no_extension"),
    ]
    assert evidence._norm(entries[0].path) == "render/shaders/bodywork.fx"
    assert evidence._extension_counts(entries) == {"<none>": 1, "fx": 1, "fxo": 1}


def test_build_probe_result_contract_preserves_boundary(monkeypatch, tmp_path):
    class Archive:
        def __init__(self, path):
            self.path = tmp_path / path
            self.path.write_bytes(b"x")
            self.entries = [
                SimpleNamespace(path=evidence.TARGET_BMT, index=8),
                SimpleNamespace(path=evidence.TARGET_MEB, index=13),
                SimpleNamespace(path="render/shaders/cache/render_shaders_bodywork_test.fxo", index=21),
                SimpleNamespace(path="render/shaders/bodywork.fx", index=22),
            ]

        def extract_entry(self, entry):
            return b"x"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(evidence, "BFF", Archive)
    monkeypatch.setattr(evidence, "_file_sha256", lambda path: "a" * 64)
    monkeypatch.setattr(
        evidence,
        "parse_bmt_material",
        lambda data: {"material": {
            "name": "BMW_M3_E36_PAINT",
            "shader": "render/shaders/bodywork.fx",
            "shaderparams": [],
        }},
    )
    mesh = SimpleNamespace(
        name="BMW_M3_E36_KIT00_BODY_LODA",
        vertex_count=3,
        triangle_count=1,
        vertex_properties=["200", "460"],
    )
    monkeypatch.setattr(evidence, "read_meb", lambda data: mesh)
    monkeypatch.setattr(
        evidence,
        "mesh_summary",
        lambda value: {"format": "SHIFT.MEB", "vertex_count": 3, "triangle_count": 1},
    )
    monkeypatch.setattr(
        evidence,
        "link_material",
        lambda *args, **kwargs: {
            "selection_status": "ambiguous",
            "selected_fxo": None,
            "permutation_identity": None,
            "shader_pair": {"selection_status": "ambiguous"},
            "linked_shader_pair": None,
            "linked_shader_error": None,
            "unresolved_textures": [],
        },
    )

    primary = tmp_path / "BMW_M3_E36.bff"
    render = tmp_path / "RENDER.bff"
    primary.write_bytes(b"primary")
    render.write_bytes(b"render")
    report = evidence.build_evidence(primary, render)

    assert report["format"] == "SHIFT.BMWRenderBFFEvidence/1"
    assert report["targets"]["bmt"]["material_name"] == "BMW_M3_E36_PAINT"
    assert report["targets"]["meb"]["vertex_count"] == 3
    assert report["shader_probe"]["status"] == "ambiguous"
    assert report["boundary"]["runtime_draw_identity"] == "not-supplied"
