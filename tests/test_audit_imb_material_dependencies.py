from tools.audit_imb_material_dependencies import (
    FORMAT,
    summarize_dependency_rows,
)


def test_dependency_summary_distinguishes_local_closure_from_global_shader():
    report = summarize_dependency_rows([
        {
            "bmt": "tracks/a.bmt",
            "material_parsed": True,
            "shader": "render/shaders/basic.fx",
            "textures": ["tracks/a_d.dds", "tracks/a_n.dds"],
            "local_ready": True,
            "ready": False,
            "blocking_reasons": [
                "shader-source-missing:render/shaders/basic.fx"
            ],
        },
        {
            "bmt": "tracks/b.bmt",
            "material_parsed": True,
            "shader": "render/shaders/basic.fx",
            "textures": ["tracks/b_d.dds"],
            "local_ready": True,
            "ready": False,
            "blocking_reasons": [
                "shader-source-missing:render/shaders/basic.fx"
            ],
        },
    ])

    assert report["format"] == FORMAT
    assert report["status"] == "external-blocked"
    assert report["ready"] is False
    assert report["local_ready"] is True
    assert report["material_occurrence_count"] == 2
    assert report["material_parse_count"] == 2
    assert report["local_ready_count"] == 2
    assert report["ready_count"] == 0
    assert report["shader_reference_count"] == 2
    assert report["unique_shader_reference_count"] == 1
    assert report["texture_reference_count"] == 3
    assert report["unique_texture_reference_count"] == 3
    assert report["blocking_reason_counts"] == {
        "shader-source-missing:render/shaders/basic.fx": 2
    }


def test_dependency_summary_reports_local_texture_blocker():
    report = summarize_dependency_rows([
        {
            "material_parsed": True,
            "shader": "render/shaders/basic.fx",
            "textures": ["tracks/missing.dds"],
            "local_ready": False,
            "ready": False,
            "blocking_reasons": [
                "same-archive-texture-missing:tracks/missing.dds",
                "shader-source-missing:render/shaders/basic.fx",
            ],
        }
    ])

    assert report["status"] == "partial"
    assert report["local_ready"] is False
    assert report["ready"] is False
    assert report["blocking_reason_counts"] == {
        "same-archive-texture-missing:tracks/missing.dds": 1,
        "shader-source-missing:render/shaders/basic.fx": 1,
    }


def test_empty_dependency_set_is_explicit():
    report = summarize_dependency_rows([])
    assert report["status"] == "empty"
    assert report["ready"] is False
    assert report["local_ready"] is False
