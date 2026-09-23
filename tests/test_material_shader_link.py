from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from material_shader_link import build_material_shader_links, norm_name


def test_norm_name_handles_case_punctuation_and_array_suffix():
    assert norm_name("Diffuse_Color[0]") == "diffusecolor"


def test_bmt_param_binds_to_ctab_float_and_sampler_registers():
    records = [{
        "archive": "cars.bff",
        "path": "car/body.bmt",
        "analysis": {"material": {
            "shader": "car/body.fx",
            "shaderparams": [
                {"name": "DiffuseColor", "value": [1, 1, 1, 1]},
                {"name": "DiffuseTexture", "value": "textures/body.dds"},
                {"name": "Missing", "value": 1},
            ],
        }},
    }]
    shaders = [{
        "archive": "cars.bff",
        "path": "cache/body.fxo",
        "source": "car/body.fx",
        "ctab": [
            {"name": "diffuse_color", "register_set": 2, "register_index": 7, "register_count": 1},
            {"name": "DiffuseTexture", "register_set": 3, "register_index": 2, "register_count": 1},
        ],
    }]
    result = build_material_shader_links(records, shaders)
    link = result["links"][0]
    assert result["stats"]["shader_matched"] == 1
    assert result["stats"]["constant_bindings"] == 1
    assert result["stats"]["sampler_bindings"] == 1
    assert link["bindings"]["constants"][0]["register_index"] == 7
    assert link["bindings"]["samplers"][0]["register_index"] == 2
    assert any(x["param"] == "Missing" for x in link["bindings"]["unresolved"])


def test_ambiguous_shader_is_not_silently_selected():
    records = [{
        "archive": "cars.bff",
        "path": "car/body.bmt",
        "analysis": {"material": {"shader": "body.fx", "shaderparams": []}},
    }]
    shaders = [
        {"archive": "a.bff", "path": "body.fxo", "source": "body.fx", "ctab": []},
        {"archive": "b.bff", "path": "body.fxo", "source": "body.fx", "ctab": []},
    ]
    result = build_material_shader_links(records, shaders)
    assert result["links"][0]["confidence"] == "ambiguous-shader"
